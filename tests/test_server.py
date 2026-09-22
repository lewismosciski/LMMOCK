import json
import sqlite3

import httpx
import pytest

from lmmock.app import create_app
from lmmock.config import port
from lmmock.storage import Store


@pytest.mark.asyncio
async def test_health_ui_and_default_chat(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.json()["ok"] is True
        ui = await client.get("/")
        logo = await client.get("/static/logo.svg")
        hero = await client.get("/static/hero.svg")
        assert "Shape the model response" in ui.text
        assert "Recent requests" in ui.text
        assert "Keep your app real" not in ui.text
        assert "MOCK-FIRST" not in ui.text
        assert "local workspace" not in ui.text
        assert "Default model" not in ui.text
        assert 'id="language-toggle"' in ui.text
        assert 'id="language-toggle" class="language-toggle" type="button" aria-label="Switch language">EN' in ui.text
        assert 'id="model-configs"' in ui.text
        assert "model-api-key" in (await client.get("/static/app.js")).text
        assert 'id="request-dialog"' in ui.text
        assert 'id="playground-request"' in ui.text
        assert 'id="playground-output"' in ui.text
        assert 'id="group-select"' in ui.text
        assert 'id="model-pattern"' in ui.text
        assert "OpenAI Completions" in ui.text
        assert logo.status_code == 200
        assert "image/svg+xml" in logo.headers["content-type"]
        assert hero.status_code == 200
        assert "Mock the model" in hero.text
        response = await client.post("/openai/v1/chat/completions", json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
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
        chat = await client.post("/openai/v1/chat/completions", json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "weather in Shanghai"}]})
        responses = await client.post("/openai/v1/responses", json={"model": "gpt-5.6-sol", "input": "weather in Shanghai"})
        anthropic = await client.post("/anthropic/v1/messages", headers={"anthropic-version": "2023-06-01"}, json={"model": "claude-5-1-opus", "max_tokens": 30, "messages": [{"role": "user", "content": "weather in Shanghai"}]})
    assert chat.json()["choices"][0]["message"]["content"] == "Shanghai is sunny."
    assert responses.json()["output_text"] == "Shanghai is sunny."
    assert anthropic.json()["content"][0]["text"] == "Shanghai is sunny."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body", "extract"),
    [
        (
            "/openai/v1/chat/completions",
            {"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "你吃饭了吗？"}]},
            lambda data: data["choices"][0]["message"]["content"],
        ),
        (
            "/openai/v1/completions",
            {"model": "gpt-5.6-sol", "prompt": "你吃饭了吗?"},
            lambda data: data["choices"][0]["text"],
        ),
        (
            "/openai/v1/responses",
            {"model": "gpt-5.6-sol", "input": "你吃饭了吗"},
            lambda data: data["output_text"],
        ),
        (
            "/anthropic/v1/messages",
            {"model": "claude-5-1-opus", "max_tokens": 32, "messages": [{"role": "user", "content": "你吃饭了呢？"}]},
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
            "model": "gpt-5.6-sol",
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
        chat = await client.post("/openai/v1/chat/completions", json={"model": "gpt-5.6-sol", "stream": True, "messages": [{"role": "user", "content": "use tool"}]})
        responses = await client.post("/openai/v1/responses", json={"model": "gpt-5.6-sol", "stream": True, "input": "use tool"})
        anthropic = await client.post("/anthropic/v1/messages", json={"model": "claude-5-1-opus", "stream": True, "max_tokens": 30, "messages": [{"role": "user", "content": "use tool"}]})
    assert "[DONE]" in chat.text
    assert "response.function_call_arguments.delta" in responses.text
    assert "message_start" in anthropic.text and "input_json_delta" in anthropic.text

@pytest.mark.asyncio
async def test_provider_model_routes_have_distinct_shapes(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        openai = await client.get("/openai/v1/models")
        anthropic = await client.get("/anthropic/v1/models")
    assert openai.json()["object"] == "list"
    assert [model["id"] for model in openai.json()["data"]] == ["gpt-5.6-sol"]
    assert anthropic.json()["data"][0]["type"] == "model"
    assert [model["id"] for model in anthropic.json()["data"]] == ["claude-5-1-opus"]


@pytest.mark.asyncio
async def test_mock_api_key_is_visible_and_persisted(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        settings = (await client.get("/__lmmock/api/settings")).json()
        settings["model_configs"][0]["api_key"] = "visible-test-key"
        saved = await client.put("/__lmmock/api/settings", json={"model_configs": settings["model_configs"]})
        settings = await client.get("/__lmmock/api/settings")
    assert saved.status_code == 200
    assert settings.json()["model_configs"][0]["api_key"] == "visible-test-key"
    assert "default_model" not in settings.json()
    assert "openai_base_url" not in settings.json()


@pytest.mark.asyncio
async def test_no_matching_rule_returns_mock_fallback(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        rules = (await client.get("/__lmmock/api/rules")).json()
        for rule in rules:
            rule["enabled"] = False
            await client.put(f"/__lmmock/api/rules/{rule['id']}", json=rule)
        response = await client.post("/anthropic/v1/messages", json={
            "model": "claude-5-1-opus",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "No rule matched."


@pytest.mark.asyncio
async def test_recent_requests_include_openable_request_and_response(app):
    request_body = {
        "model": "gpt-5.6-sol",
        "messages": [{"role": "user", "content": "inspect me"}],
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/openai/v1/chat/completions", json=request_body)
        requests = (await client.get("/__lmmock/api/requests")).json()
    assert response.status_code == 200
    assert requests[0]["request"] == request_body
    assert requests[0]["response"]["choices"][0]["message"]["content"] == "LMMock is running."


@pytest.mark.asyncio
async def test_model_configuration_controls_interface_and_first_model(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        group_id = (await client.get("/__lmmock/api/groups")).json()[0]["id"]
        saved = await client.put("/__lmmock/api/settings", json={
            "model_configs": [
                {"name": "demo-one", "protocol": "anthropic", "api_key": "", "group_ids": [group_id]},
                {"name": "demo-two", "protocol": "openai", "api_key": "", "group_ids": [group_id]},
            ],
        })
        models = await client.get("/openai/v1/models")
        anthropic_models = await client.get("/anthropic/v1/models")
        completion = await client.post("/openai/v1/completions", json={"prompt": "hello"})
        wrong_interface = await client.post("/openai/v1/responses", json={"model": "demo-one", "input": "hello"})
        unknown = await client.post("/openai/v1/completions", json={"model": "missing", "prompt": "hello"})
        invalid_groups = await client.put("/__lmmock/api/settings", json={"model_configs": [{"name": "broken", "protocol": "openai", "api_key": "", "group_ids": []}]})
    assert saved.status_code == 200
    assert [item["id"] for item in models.json()["data"]] == ["demo-two"]
    assert [item["id"] for item in anthropic_models.json()["data"]] == ["demo-one"]
    assert completion.json()["model"] == "demo-two"
    assert completion.json()["choices"][0]["text"] == "LMMock is running."
    assert wrong_interface.status_code == 404
    assert unknown.status_code == 404
    assert invalid_groups.status_code == 400


@pytest.mark.asyncio
async def test_multiple_backends_keep_original_model_names_and_select_model_rules(app):
    models = ["deepseek-chat", "gpt-4o", "claude-3-7-sonnet", "glm-4-plus"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        group_id = (await client.get("/__lmmock/api/groups")).json()[0]["id"]
        model_configs = [{"name": model, "protocol": "anthropic" if model.startswith("claude") else "openai", "api_key": "", "group_ids": [group_id]} for model in models]
        await client.put("/__lmmock/api/settings", json={"model_configs": model_configs})
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
        settings = (await client.get("/__lmmock/api/settings")).json()
        settings["model_configs"][0]["group_ids"].append(group["id"])
        await client.put("/__lmmock/api/settings", json={"model_configs": settings["model_configs"]})
        combined = await client.post("/openai/v1/chat/completions", json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
        selected = await client.post("/openai/v1/chat/completions", headers={"x-lmmock-group": "Default"}, json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
    assert created.status_code == 201
    assert combined.json()["choices"][0]["message"]["content"] == "Selected failure group."
    assert selected.json()["choices"][0]["message"]["content"] == "LMMock is running."


@pytest.mark.asyncio
async def test_api_key_protects_only_model_apis(tmp_path):
    protected_app = create_app(tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=protected_app), base_url="http://test") as client:
        settings = (await client.get("/__lmmock/api/settings")).json()
        settings["model_configs"][0]["api_key"] = "openai-key"
        settings["model_configs"][1]["api_key"] = "anthropic-key"
        configured = await client.put("/__lmmock/api/settings", json={"model_configs": settings["model_configs"]})
        assert configured.status_code == 200
        assert (await client.get("/")).status_code == 200
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/openai/v1/models")).status_code == 200
        settings = await client.get("/__lmmock/api/settings")
        assert settings.status_code == 200
        missing = await client.post("/openai/v1/chat/completions", json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
        wrong = await client.post("/openai/v1/chat/completions", headers={"authorization": "Bearer wrong"}, json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
        bearer = await client.post("/openai/v1/chat/completions", headers={"authorization": "Bearer openai-key"}, json={"model": "gpt-5.6-sol", "messages": [{"role": "user", "content": "hello"}]})
        api_key = await client.post("/anthropic/v1/messages", headers={"x-api-key": "anthropic-key"}, json={
            "model": "claude-5-1-opus",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hello"}],
        })
        wrong_model_key = await client.post("/anthropic/v1/messages", headers={"x-api-key": "openai-key"}, json={
            "model": "claude-5-1-opus",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hello"}],
        })
        tokens = await client.post("/anthropic/v1/messages/count_tokens", headers={"x-api-key": "anthropic-key"}, json={
            "model": "claude-5-1-opus",
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert bearer.status_code == 200
    assert api_key.status_code == 200
    assert wrong_model_key.status_code == 401
    assert tokens.json()["input_tokens"] > 0
    assert [config["api_key"] for config in settings.json()["model_configs"]] == ["openai-key", "anthropic-key"]


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
    assert settings["model_configs"] == [{"name": "old-model", "protocol": "openai", "api_key": "", "group_ids": [store.list_groups()[0]["id"]]}]


def test_previous_builtin_model_names_are_migrated(tmp_path):
    database = tmp_path / "lmmock.sqlite3"
    store = Store(database)
    group_id = store.list_groups()[0]["id"]
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (
            "model_configs",
            json.dumps([
                {"name": "mock-model", "protocol": "openai", "api_key": "", "group_ids": [group_id]},
                {"name": "mock-claude", "protocol": "anthropic", "api_key": "", "group_ids": [group_id]},
            ]),
        ))
        connection.execute("INSERT OR REPLACE INTO settings VALUES ('default_model', '\"mock-model\"')")
    migrated = Store(database).get_settings()
    assert [config["name"] for config in migrated["model_configs"]] == ["gpt-5.6-sol", "claude-5-1-opus"]
    assert "default_model" not in migrated


def test_default_port_is_uncommon(monkeypatch):
    monkeypatch.delenv("LMMOCK_PORT", raising=False)
    assert port() == 17321


@pytest.mark.asyncio
async def test_random_reply_generates_requested_size(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/__lmmock/api/rules", json={
            "name": "Random payload",
            "priority": 1,
            "scopes": ["*"],
            "match_type": "contains",
            "match_value": "large payload",
            "reply_type": "random",
            "reply": {},
        })
        first = await client.post("/openai/v1/chat/completions", json={
            "model": "gpt-5.6-sol",
            "messages": [{"role": "user", "content": "large payload"}],
        })
        second = await client.post("/openai/v1/chat/completions", json={
            "model": "gpt-5.6-sol",
            "messages": [{"role": "user", "content": "large payload"}],
        })
    first_text = first.json()["choices"][0]["message"]["content"]
    second_text = second.json()["choices"][0]["message"]["content"]
    assert created.status_code == 201
    assert len(first_text.encode("ascii")) == 4096
    assert len(second_text) == 4096
    assert first_text != second_text
    assert first.json()["usage"]["completion_tokens"] == 1024


@pytest.mark.asyncio
async def test_token_statistics_aggregate_by_model_and_reset(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        openai = await client.post("/openai/v1/completions", json={"model": "gpt-5.6-sol", "prompt": "hello"})
        anthropic = await client.post("/anthropic/v1/messages", json={
            "model": "claude-5-1-opus",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "hello"}],
        })
        recent = (await client.get("/__lmmock/api/requests")).json()
        stats = (await client.get("/__lmmock/api/stats")).json()
        cleared = await client.delete("/__lmmock/api/requests")
        empty_stats = (await client.get("/__lmmock/api/stats")).json()

    expected_total = openai.json()["usage"]["total_tokens"] + sum(anthropic.json()["usage"].values())
    assert stats["estimated"] is True
    assert stats["requests"] == 2
    assert stats["total_tokens"] == expected_total
    assert stats["total_tokens"] == stats["input_tokens"] + stats["output_tokens"]
    assert set(stats["by_model"]) == {"gpt-5.6-sol", "claude-5-1-opus"}
    assert all("usage" in item for item in recent)
    assert cleared.status_code == 204
    assert empty_stats == {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_model": {}, "estimated": True}
