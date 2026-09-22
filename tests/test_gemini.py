import json

import httpx
import pytest
from google import genai
from google.genai import errors, types


MODEL = "gemini-2.5-flash"
BASE = f"/gemini/v1beta/models/{MODEL}"
BODY = {"contents": [{"role": "user", "parts": [{"text": "你吃饭了吗？"}]}]}


@pytest.fixture
def gemini_app(app):
    store = app.state.lmmock.store
    settings = store.get_settings()
    store.set_settings({"model_configs": [*settings["model_configs"], {
        "name": MODEL, "protocol": "gemini", "api_key": "mock",
        "group_ids": [settings["active_group_id"]],
    }]})
    return app


@pytest.fixture
async def client(gemini_app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gemini_app), base_url="http://test",
        headers={"x-goog-api-key": "mock"},
    ) as client:
        yield client


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


async def test_generate_regex_usage_and_history(client):
    response = await client.post(BASE + ":generateContent", json=BODY)
    assert response.status_code == 200
    payload = response.json()
    candidate = payload["candidates"][0]
    assert candidate == {"index": 0, "content": {"role": "model", "parts": [{"text": "我吃饭了！"}]}, "finishReason": "STOP"}
    usage = payload["usageMetadata"]
    assert usage["totalTokenCount"] == usage["promptTokenCount"] + usage["candidatesTokenCount"]
    history = (await client.get("/__lmmock/api/requests")).json()[0]
    assert history["provider"] == "gemini" and history["rule"] == "foolAI"
    assert history["response"] == payload
    stats = (await client.get("/__lmmock/api/stats")).json()
    assert stats["by_model"][MODEL]["total_tokens"] == usage["totalTokenCount"]


@pytest.mark.parametrize("text", ["", "你好 " * 3000])
@pytest.mark.parametrize("sse", [True, False])
async def test_stream_content_and_finish(client, text, sse):
    await client.post("/__lmmock/api/rules", json={"name": "stream", "priority": 1, "reply": {"content": text}})
    response = await client.post(BASE + ":streamGenerateContent" + ("?alt=sse" if sse else ""), json=BODY)
    assert response.status_code == 200
    chunks = events(response) if sse else response.json()
    assert "[DONE]" not in response.text
    assert "".join(chunk["candidates"][0]["content"]["parts"][0]["text"] for chunk in chunks) == text
    assert len({chunk["responseId"] for chunk in chunks}) == 1
    assert all(chunk["modelVersion"] == MODEL for chunk in chunks)
    assert all("finishReason" not in chunk["candidates"][0] for chunk in chunks[:-1])
    assert chunks[-1]["candidates"][0]["finishReason"] == "STOP"
    assert chunks[-1]["usageMetadata"]["candidatesTokenCount"] == (len(text) + 3) // 4


async def test_json_tool_and_function_response_matching(client):
    await client.post("/__lmmock/api/rules", json={
        "name": "tool", "priority": 2, "reply_type": "tool",
        "reply": {"tool_name": "weather", "arguments": {"city": "Shanghai"}},
    })
    expected = {"functionCall": {"name": "weather", "args": {"city": "Shanghai"}}}
    for endpoint in (":generateContent", ":streamGenerateContent?alt=sse"):
        response = await client.post(BASE + endpoint, json=BODY)
        payload = events(response)[0] if "stream" in endpoint else response.json()
        assert payload["candidates"][0]["content"]["parts"] == [expected]
    await client.post("/__lmmock/api/rules", json={
        "name": "tool result", "priority": 1, "scopes": ["generateContent"],
        "match_type": "contains", "match_value": "sunny", "reply_type": "json",
        "reply": {"content": '{"ok":true}'},
    })
    result = await client.post(BASE + ":generateContent", json={"contents": [
        {"role": "model", "parts": [expected]},
        {"role": "user", "parts": [{"functionResponse": {"name": "weather", "response": {"result": "sunny"}}}]},
    ]})
    assert json.loads(result.json()["candidates"][0]["content"]["parts"][0]["text"]) == {"ok": True}


@pytest.mark.parametrize("endpoint", [":generateContent", ":streamGenerateContent?alt=sse", ":countTokens"])
async def test_auth_and_unknown_model(client, endpoint):
    denied = await client.post(BASE + endpoint, json=BODY, headers={"x-goog-api-key": "wrong"})
    assert denied.status_code == 401
    assert denied.json()["error"]["status"] == "UNAUTHENTICATED"
    missing = await client.post("/gemini/v1beta/models/gpt-5.6-sol" + endpoint, json=BODY)
    assert missing.status_code == 404
    assert missing.json()["error"]["status"] == "NOT_FOUND"
    query = await client.post(BASE + endpoint + ("&" if "?" in endpoint else "?") + "key=mock", json=BODY, headers={"x-goog-api-key": ""})
    assert query.status_code == 200


@pytest.mark.parametrize("body", [[], {"contents": None}, {"contents": [None]}, {"contents": [{"parts": [1]}]}, {"contents": [{"parts": [{"text": 42}]}]}])
async def test_invalid_body(client, body):
    response = await client.post(BASE + ":generateContent", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["status"] == "INVALID_ARGUMENT"


async def test_count_models_and_path_precedence(client):
    body = {**BODY, "model": "wrong", "stream": True, "systemInstruction": {"parts": [{"text": "Be brief"}]}}
    response = await client.post(BASE + ":generateContent", json=body)
    assert response.headers["content-type"] == "application/json"
    assert response.json()["modelVersion"] == MODEL
    counted = await client.post(BASE + ":countTokens", json=body)
    nested = await client.post(BASE + ":countTokens", json={"generateContentRequest": body})
    assert counted.json() == nested.json() == {"totalTokens": response.json()["usageMetadata"]["promptTokenCount"]}
    models = (await client.get("/gemini/v1beta/models")).json()["models"]
    assert [model["name"] for model in models] == [f"models/{MODEL}"]
    assert (await client.get("/gemini/v1beta/models/" + MODEL)).json() == models[0]
    assert (await client.get("/gemini/v1beta/models/missing")).status_code == 404
    invalid = await client.post(BASE + ":countTokens", json={"generateContentRequest": None})
    assert invalid.status_code == 400
    invalid_json = await client.post(BASE + ":generateContent", content=b"{")
    assert invalid_json.status_code == 400


async def test_group_scopes_errors_and_random(client):
    group = (await client.post("/__lmmock/api/groups", json={"name": "Gemini errors"})).json()
    await client.post("/__lmmock/api/rules", json={
        "name": "rate limit", "group_id": group["id"], "reply_type": "error",
        "reply": {"status_code": 429, "message": "Try later"},
    })
    response = await client.post(BASE + ":generateContent", json=BODY, headers={"x-lmmock-group": group["name"]})
    assert response.status_code == 400
    settings = (await client.get("/__lmmock/api/settings")).json()
    settings["model_configs"][-1]["group_ids"].append(group["id"])
    assert (await client.put("/__lmmock/api/settings", json=settings)).status_code == 200
    response = await client.post(BASE + ":streamGenerateContent?alt=sse", json=BODY, headers={"x-lmmock-group": group["name"]})
    assert response.status_code == 429
    assert response.json() == {"error": {"code": 429, "message": "Try later", "status": "RESOURCE_EXHAUSTED"}}
    await client.post("/__lmmock/api/rules", json={"name": "wrong scope", "priority": 0, "scopes": ["messages"], "reply": {"content": "wrong"}})
    await client.post("/__lmmock/api/rules", json={"name": "random", "priority": 1, "scopes": ["generateContent"], "reply_type": "random", "reply": {"size": 4096}})
    response = await client.post(BASE + ":generateContent", json=BODY)
    assert len(response.json()["candidates"][0]["content"]["parts"][0]["text"].encode()) == 4096
    preview = await client.post("/__lmmock/api/preview", json={"protocol": "gemini_generate_content", "body": {**BODY, "model": MODEL}})
    assert preview.json()["matched_rule"]["name"] == "random"


@pytest.fixture
def live_url(gemini_app, live_server):
    return live_server + "/gemini"


def test_official_google_genai_sdk(live_url, gemini_app):
    with genai.Client(vertexai=False, api_key="mock", http_options=types.HttpOptions(base_url=live_url, api_version="v1beta")) as sdk:
        response = sdk.models.generate_content(model=MODEL, contents="你吃饭了吗？")
        assert response.text == "我吃饭了！"
        assert "".join(chunk.text or "" for chunk in sdk.models.generate_content_stream(model=MODEL, contents="你吃饭了吗？")) == response.text
        assert sdk.models.count_tokens(model=MODEL, contents="你吃饭了吗？").total_tokens == response.usage_metadata.prompt_token_count
        assert [model.name for model in sdk.models.list()] == [f"models/{MODEL}"]
        assert sdk.models.get(model=MODEL).name == f"models/{MODEL}"
        chat = sdk.chats.create(model=MODEL)
        assert chat.send_message("Hello").text == "LMMock is running."
        assert chat.send_message("你会写代码吗？").text == "我会写代码！"
        gemini_app.state.lmmock.store.create_rule({"name": "SDK tool", "priority": 1, "reply_type": "tool", "reply": {"tool_name": "weather", "arguments": {"city": "Shanghai"}}})
        tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="weather", parameters={"type": "OBJECT", "properties": {"city": {"type": "STRING"}}})])
        config = types.GenerateContentConfig(tools=[tool], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        response = sdk.models.generate_content(model=MODEL, contents="weather", config=config)
        assert response.function_calls[0].name == "weather"
        assert response.function_calls[0].args == {"city": "Shanghai"}
        chunks = list(sdk.models.generate_content_stream(model=MODEL, contents="weather", config=config))
        assert chunks[0].function_calls[0].args == {"city": "Shanghai"}
        with pytest.raises(errors.ClientError) as error:
            sdk.models.generate_content(model="missing", contents="Hello")
        assert error.value.code == 404
