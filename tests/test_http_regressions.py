import json

import httpx
import pytest


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
        yield session


@pytest.mark.parametrize("method,path", [
    ("POST", "/__lmmock/api/rules"), ("PUT", "/__lmmock/api/rules/1"),
    ("POST", "/__lmmock/api/groups"), ("PUT", "/__lmmock/api/groups/1"),
    ("PUT", "/__lmmock/api/settings"), ("POST", "/__lmmock/api/preview"),
    ("POST", "/__lmmock/api/rules/reorder"), ("POST", "/anthropic/v1/messages/count_tokens"),
    ("POST", "/openai/v1/chat/completions"),
])
@pytest.mark.parametrize("body", [b"[]", b"null", b"{", b"\xff", b'{"value":NaN}'])
async def test_invalid_json_returns_400(client, method, path, body):
    response = await client.request(method, path, content=body)
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize("body", [
    {"messages": None}, {"messages": [1]}, {"messages": [{"content": 1}]},
    {"messages": [{"content": [1]}]}, {"messages": [{"tool_calls": 1}]},
    {"stream_options": []}, {"stream": "false"}, {"model": []},
])
async def test_invalid_message_shapes(client, body):
    for path in ("/openai/v1/chat/completions", "/anthropic/v1/messages", "/anthropic/v1/messages/count_tokens"):
        response = await client.post(path, json=body)
        assert response.status_code in {400, 404}


@pytest.mark.parametrize("body", [{"body": []}, {"group_id": "bad"}, {"protocol": []}])
async def test_invalid_preview_returns_400(client, body):
    assert (await client.post("/__lmmock/api/preview", json=body)).status_code == 400


async def test_nullable_tool_calls_are_accepted(client):
    response = await client.post("/openai/v1/chat/completions", json={"messages": [{"role": "assistant", "content": None, "tool_calls": None}]})
    assert response.status_code == 200


async def test_bad_regex_is_rejected_without_changing_rule(client):
    before = (await client.get("/__lmmock/api/rules")).json()
    for method, path in (("POST", "/__lmmock/api/rules"), ("PUT", f"/__lmmock/api/rules/{before[0]['id']}")):
        result = await client.request(method, path, json={"match_type": "regex", "match_value": "("})
        assert result.status_code == 400
        assert "Invalid regular expression" in result.json()["error"]
    assert (await client.get("/__lmmock/api/rules")).json() == before


@pytest.mark.parametrize("status", [200, 0, 600, "bad", 400.5, True])
async def test_error_rules_require_valid_http_status(client, status):
    response = await client.post("/__lmmock/api/rules", json={"reply_type": "error", "reply": {"status_code": status}})
    assert response.status_code == 400


@pytest.mark.parametrize("arguments", [[], 1, None, "{", '"text"'])
async def test_tool_arguments_require_object(client, arguments):
    response = await client.post("/__lmmock/api/rules", json={"reply_type": "tool", "reply": {"arguments": arguments}})
    assert response.status_code == 400


async def test_json_string_tool_arguments_are_normalized(client):
    response = await client.post("/__lmmock/api/rules", json={"reply_type": "tool", "reply": {"arguments": '{"city":"Shanghai"}'}})
    assert response.status_code == 201
    assert response.json()["reply"]["arguments"] == {"city": "Shanghai"}


async def test_openai_completion_usage_matches_protocol(client):
    for path, body in (("chat/completions", {"messages": [{"role": "user", "content": "hello"}]}), ("completions", {"prompt": "hello"})):
        response = await client.post("/openai/v1/" + path, json=body)
        usage = response.json()["usage"]
        assert set(usage) == {"prompt_tokens", "completion_tokens", "total_tokens"}
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    stream = await client.post("/openai/v1/chat/completions", json={"stream": True, "stream_options": {"include_usage": True}})
    events = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: {")]
    assert set(events[-1]["usage"]) == {"prompt_tokens", "completion_tokens", "total_tokens"}


@pytest.mark.parametrize("path,body,kind", [
    ("/openai/v1/chat/completions", {}, "chat"),
    ("/openai/v1/responses", {"input": "tool"}, "responses"),
    ("/anthropic/v1/messages", {}, "anthropic"),
])
async def test_stream_tool_ids_match_recent_request(client, path, body, kind):
    await client.post("/__lmmock/api/rules", json={"priority": 1, "reply_type": "tool", "reply": {"tool_name": "weather", "arguments": {"city": "Shanghai"}}})
    response = await client.post(path, json={**body, "stream": True})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: {")]
    saved = (await client.get("/__lmmock/api/requests")).json()[0]["response"]
    if kind == "chat":
        call = next(event["choices"][0]["delta"]["tool_calls"][0] for event in events if event.get("choices") and event["choices"][0]["delta"].get("tool_calls"))
        assert call["id"] == saved["choices"][0]["message"]["tool_calls"][0]["id"]
    elif kind == "responses":
        assert events[-1]["response"] == saved
        assert next(event["item"] for event in events if event["type"] == "response.output_item.done") == saved["output"][0]
    else:
        block = next(event["content_block"] for event in events if event["type"] == "content_block_start")
        assert block["id"] == saved["content"][0]["id"]
