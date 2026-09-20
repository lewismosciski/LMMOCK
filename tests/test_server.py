import json
import sqlite3

import httpx
import pytest

from lmmock.app import create_app
from lmmock.config import port
from lmmock.storage import Store


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path)


@pytest.mark.asyncio
async def test_health_ui_and_default_chat(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.json()["ok"] is True
        ui = await client.get("/")
        logo = await client.get("/static/logo.svg")
        assert "Shape the model response" in ui.text
        assert "Recent requests" in ui.text
        assert "Keep your app real" not in ui.text
        assert "MOCK-FIRST" not in ui.text
        assert 'id="language-toggle"' in ui.text
        assert 'id="language-toggle" class="language-toggle" type="button" aria-label="Switch language">EN' in ui.text
        assert 'id="mock-api-key"' in ui.text
        assert 'id="request-dialog"' in ui.text
        assert 'id="playground-request"' in ui.text
        assert 'id="playground-output"' in ui.text
        assert 'id="group-select"' in ui.text
        assert 'id="models"' in ui.text
        assert 'id="model-pattern"' in ui.text
        assert "OpenAI Completions" in ui.text
        assert logo.status_code == 200
        assert "image/svg+xml" in logo.headers["content-type"]
        response = await client.post("/openai/v1/chat/completions", json={"model": "mock-model", "messages": [{"role": "user", "content": "hello"}]})
        assert (await client.get("/v1/models")).status_code == 404
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "LMMock is running."


@pytest.mark.asyncio
async def test_rule_matches_and_templates_across_protocols(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/__lmmock/api/rules", json={
            "name": "Weather",
            "priority": 1,
            "scopes": ["*"],
            "match_type": "regex",
            "match_value": r"weather in (?P<city>.+)",
            "reply_type": "text",
            "reply": {"content": "${city} is sunny."},
        })
        assert created.status_code == 201
        chat = await client.post("/openai/v1/chat/completions", json={"model": "mock-model", "messages": [{"role": "user", "content": "weather in Shanghai"}]})
        responses = await client.post("/openai/v1/responses", json={"model": "mock-model", "input": "weather in Shanghai"})
        anthropic = await client.post("/anthropic/v1/messages", headers={"anthropic-version": "2023-06-01"}, json={"model": "mock-model", "max_tokens": 30, "messages": [{"role": "user", "content": "weather in Shanghai"}]})
    assert chat.json()["choices"][0]["message"]["content"] == "Shanghai is sunny."
    assert responses.json()["output_text"] == "Shanghai is sunny."
    assert anthropic.json()["content"][0]["text"] == "Shanghai is sunny."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body", "extract"),
    [
        (
            "/openai/v1/chat/completions",
            {"model": "mock-model", "messages": [{"role": "user", "content": "你吃饭了吗？"}]},
            lambda data: data["choices"][0]["message"]["content"],
        ),
        (
            "/openai/v1/completions",
            {"model": "mock-model", "prompt": "你吃饭了吗?"},
            lambda data: data["choices"][0]["text"],
        ),
        (
            "/openai/v1/responses",
            {"model": "mock-model", "input": "你吃饭了吗"},
            lambda data: data["output_text"],
        ),
        (
            "/anthropic/v1/messages",
            {"model": "mock-model", "max_tokens": 32, "messages": [{"role": "user", "content": "你吃饭了呢？"}]},
            lambda data: data["content"][0]["text"],
        ),
    ],
)
async def test_default_fool_ai_rule_across_protocols(app, path, body, extract):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(path, json=body)
    assert response.status_code == 200
    assert extract(response.json()) == "我吃饭了！"


@pytest.mark.asyncio
async def test_default_fool_ai_rule_does_not_match_statements(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/openai/v1/chat/completions", json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "你吃饭了。"}],
        })
        rules = (await client.get("/__lmmock/api/rules")).json()
    assert response.json()["choices"][0]["message"]["content"] == "LMMock is running."
    assert [rule["name"] for rule in rules] == ["foolAI", "Default reply"]


@pytest.mark.asyncio
async def test_tool_and_stream_shapes(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/__lmmock/api/rules", json={
            "name": "Weather tool",
            "priority": 1,
            "scopes": ["*"],
            "match_type": "contains",
            "match_value": "use tool",
            "reply_type": "tool",
            "reply": {"tool_name": "get_weather", "arguments": {"city": "Shanghai"}},
        })
        chat = await client.post("/openai/v1/chat/completions", json={"model": "mock-model", "stream": True, "messages": [{"role": "user", "content": "use tool"}]})
        responses = await client.post("/openai/v1/responses", json={"model": "mock-model", "stream": True, "input": "use tool"})
        anthropic = await client.post("/anthropic/v1/messages", json={"model": "mock-model", "stream": True, "max_tokens": 30, "messages": [{"role": "user", "content": "use tool"}]})
    assert "[DONE]" in chat.text
    assert "response.function_call_arguments.delta" in responses.text
    assert "message_start" in anthropic.text and "input_json_delta" in anthropic.text


@pytest.mark.asyncio
async def test_provider_model_routes_have_distinct_shapes(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        openai = await client.get("/openai/v1/models")
        anthropic = await client.get("/anthropic/v1/models")
    assert openai.json()["object"] == "list"
    assert anthropic.json()["data"][0]["type"] == "model"


@pytest.mark.asyncio
async def test_mock_api_key_is_visible_and_persisted(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        saved = await client.put("/__lmmock/api/settings", json={"api_key": "visible-test-key"})
        settings = await client.get("/__lmmock/api/settings")
    assert saved.status_code == 200
    assert settings.json()["api_key"] == "visible-test-key"
    assert "openai_base_url" not in settings.json()


@pytest.mark.asyncio
async def test_no_matching_rule_returns_mock_fallback(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        rules = (await client.get("/__lmmock/api/rules")).json()
        for rule in rules:
            rule["enabled"] = False
            await client.put(f"/__lmmock/api/rules/{rule['id']}", json=rule)
        response = await client.post("/anthropic/v1/messages", json={
            "model": "mock-model",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "No rule matched."


@pytest.mark.asyncio
async def test_recent_requests_include_openable_request_and_response(app):
    request_body = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "inspect me"}],
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/openai/v1/chat/completions", json=request_body)
        requests = (await client.get("/__lmmock/api/requests")).json()
    assert response.status_code == 200
    assert requests[0]["request"] == request_body
    assert requests[0]["response"]["choices"][0]["message"]["content"] == "LMMock is running."


@pytest.mark.asyncio
async def test_models_completions_and_interface_switches(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        saved = await client.put("/__lmmock/api/settings", json={
            "models": ["demo-one", "demo-two"],
            "default_model": "demo-two",
            "enabled_operations": ["completions", "messages"],
        })
        models = await client.get("/openai/v1/models")
        completion = await client.post("/openai/v1/completions", json={"prompt": "hello"})
        disabled = await client.post("/openai/v1/responses", json={"model": "demo-two", "input": "hello"})
        unknown = await client.post("/openai/v1/completions", json={"model": "missing", "prompt": "hello"})
    assert saved.status_code == 200
    assert [item["id"] for item in models.json()["data"]] == ["demo-one", "demo-two"]
    assert completion.json()["model"] == "demo-two"
    assert completion.json()["choices"][0]["text"] == "LMMock is running."
    assert disabled.status_code == 404
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_multiple_backends_keep_original_model_names_and_select_model_rules(app):
    models = ["deepseek-chat", "gpt-4o", "claude-3-7-sonnet", "glm-4-plus"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/__lmmock/api/settings", json={"models": models, "default_model": "gpt-4o"})
        for priority, model in enumerate(models, 1):
            created = await client.post("/__lmmock/api/rules", json={
                "name": f"{model} reply",
                "priority": priority,
                "model_pattern": "gpt-*" if model == "gpt-4o" else model,
                "scopes": ["*"],
                "match_type": "all",
                "reply_type": "text",
                "reply": {"content": f"mocked by {model}"},
            })
            assert created.status_code == 201

        replies = {}
        for model in ("deepseek-chat", "gpt-4o", "glm-4-plus"):
            response = await client.post("/openai/v1/chat/completions", json={
                "model": model,
                "messages": [{"role": "user", "content": "same prompt"}],
            })
            replies[model] = response.json()["choices"][0]["message"]["content"]
        claude = await client.post("/anthropic/v1/messages", json={
            "model": "claude-3-7-sonnet",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "same prompt"}],
        })
        replies["claude-3-7-sonnet"] = claude.json()["content"][0]["text"]

    assert replies == {model: f"mocked by {model}" for model in models}


@pytest.mark.asyncio
async def test_behavior_groups_isolate_rules(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        group = (await client.post("/__lmmock/api/groups", json={"name": "Failures", "description": "Error cases"})).json()
        created = await client.post("/__lmmock/api/rules", json={
            "name": "Failure reply",
            "group_id": group["id"],
            "priority": 1,
            "scopes": ["*"],
            "match_type": "all",
            "reply_type": "text",
            "reply": {"content": "Selected failure group."},
        })
        normal = await client.post("/openai/v1/chat/completions", json={"model": "mock-model", "messages": [{"role": "user", "content": "hello"}]})
        selected = await client.post("/openai/v1/chat/completions", headers={"x-lmmock-group": "Failures"}, json={"model": "mock-model", "messages": [{"role": "user", "content": "hello"}]})
    assert created.status_code == 201
    assert normal.json()["choices"][0]["message"]["content"] == "LMMock is running."
    assert selected.json()["choices"][0]["message"]["content"] == "Selected failure group."


@pytest.mark.asyncio
async def test_api_key_protects_only_model_apis(tmp_path):
    protected_app = create_app(tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=protected_app), base_url="http://test") as client:
        configured = await client.put("/__lmmock/api/settings", json={"api_key": "secret-key"})
        assert configured.status_code == 200
        assert (await client.get("/")).status_code == 200
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/openai/v1/models")).status_code == 401
        assert (await client.get("/openai/v1/models", headers={"authorization": "Bearer wrong"})).status_code == 401
        assert (await client.get("/anthropic/v1/models", headers={"x-api-key": "wrong"})).status_code == 401
        settings = await client.get("/__lmmock/api/settings")
        assert settings.status_code == 200
        bearer = await client.get("/openai/v1/models", headers={"authorization": "Bearer secret-key"})
        api_key = await client.post("/anthropic/v1/messages", headers={"x-api-key": "secret-key"}, json={
            "model": "mock-model",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hello"}],
        })
        tokens = await client.post("/anthropic/v1/messages/count_tokens", headers={"x-api-key": "secret-key"}, json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert bearer.status_code == 200
    assert api_key.status_code == 200
    assert tokens.json()["input_tokens"] > 0
    assert settings.json()["api_key"] == "secret-key"


def test_existing_database_migrates_to_groups_and_model_list(tmp_path):
    database = tmp_path / "lmmock.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, enabled INTEGER NOT NULL,
                priority INTEGER NOT NULL, scopes TEXT NOT NULL, match_type TEXT NOT NULL,
                match_value TEXT NOT NULL, reply_type TEXT NOT NULL, reply_json TEXT NOT NULL,
                delay_ms INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO rules
            (name,enabled,priority,scopes,match_type,match_value,reply_type,reply_json,delay_ms,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            ("Existing", 1, 10, '["*"]', "all", "", "text", '{"content":"kept"}', 0, "now", "now"),
        )
        connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO settings VALUES ('model', '\"old-model\"')")
    store = Store(database)
    rules = store.list_rules()
    settings = store.get_settings()
    assert rules[0]["name"] == "Existing"
    assert rules[0]["group_id"] == store.list_groups()[0]["id"]
    assert [rule["name"] for rule in rules].count("foolAI") == 1
    assert settings["models"] == ["old-model"]
    assert settings["default_model"] == "old-model"
    assert settings["api_key"] == ""


def test_default_port_is_uncommon(monkeypatch):
    monkeypatch.delenv("LMMOCK_PORT", raising=False)
    assert port() == 17321
