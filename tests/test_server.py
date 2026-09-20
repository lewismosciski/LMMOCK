import json

import httpx
import pytest

import lmmock.app as app_module
from lmmock.app import create_app


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
        assert 'id="openai-forward"' in ui.text
        assert 'id="request-dialog"' in ui.text
        assert logo.status_code == 200
        assert "image/svg+xml" in logo.headers["content-type"]
        response = await client.post("/v1/chat/completions", json={"model": "mock-model", "messages": [{"role": "user", "content": "hello"}]})
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
        chat = await client.post("/v1/chat/completions", json={"model": "mock", "messages": [{"role": "user", "content": "weather in Shanghai"}]})
        responses = await client.post("/v1/responses", json={"model": "mock", "input": "weather in Shanghai"})
        anthropic = await client.post("/v1/messages", headers={"anthropic-version": "2023-06-01"}, json={"model": "mock", "max_tokens": 30, "messages": [{"role": "user", "content": "weather in Shanghai"}]})
    assert chat.json()["choices"][0]["message"]["content"] == "Shanghai is sunny."
    assert responses.json()["output_text"] == "Shanghai is sunny."
    assert anthropic.json()["content"][0]["text"] == "Shanghai is sunny."


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
        chat = await client.post("/v1/chat/completions", json={"model": "mock", "stream": True, "messages": [{"role": "user", "content": "use tool"}]})
        responses = await client.post("/v1/responses", json={"model": "mock", "stream": True, "input": "use tool"})
        anthropic = await client.post("/v1/messages", json={"model": "mock", "stream": True, "max_tokens": 30, "messages": [{"role": "user", "content": "use tool"}]})
    assert "[DONE]" in chat.text
    assert "response.function_call_arguments.delta" in responses.text
    assert "message_start" in anthropic.text and "input_json_delta" in anthropic.text


@pytest.mark.asyncio
async def test_models_dispatch_by_anthropic_header(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        openai = await client.get("/v1/models")
        anthropic = await client.get("/v1/models", headers={"anthropic-version": "2023-06-01"})
    assert openai.json()["object"] == "list"
    assert anthropic.json()["data"][0]["type"] == "model"


@pytest.mark.asyncio
async def test_provider_settings_are_persisted_without_keys(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        saved = await client.put("/__lmmock/api/settings", json={
            "forward_openai": True,
            "openai_base_url": "https://api.openai.com",
        })
        settings = await client.get("/__lmmock/api/settings")
        invalid = await client.put("/__lmmock/api/settings", json={"forward_openai": "yes"})
    assert saved.status_code == 200
    assert settings.json()["forward_openai"] is True
    assert "mode_openai" not in settings.json()
    assert settings.json()["openai_base_url"] == "https://api.openai.com"
    assert "api_key" not in settings.json()
    assert invalid.status_code == 400


@pytest.mark.asyncio
async def test_forwarding_does_not_call_upstream_when_a_rule_matches(app, monkeypatch):
    called = False

    async def fake_proxy(*args, **kwargs):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(app_module, "_proxy", fake_proxy)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/__lmmock/api/settings", json={
            "forward_openai": True,
            "openai_base_url": "https://api.openai.com",
        })
        response = await client.post("/v1/chat/completions", json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "LMMock is running."
    assert called is False


@pytest.mark.asyncio
async def test_forwarding_requires_a_base_url_when_no_rule_matches(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        rules = (await client.get("/__lmmock/api/rules")).json()
        default_rule = rules[0]
        default_rule["enabled"] = False
        await client.put(f"/__lmmock/api/rules/{default_rule['id']}", json=default_rule)
        await client.put("/__lmmock/api/settings", json={"forward_anthropic": True})
        response = await client.post("/v1/messages", json={
            "model": "mock-model",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "hello"}],
        })
    assert response.status_code == 502
    assert response.json()["error"]["type"] == "upstream_error"


@pytest.mark.asyncio
async def test_recent_requests_include_openable_request_and_response(app):
    request_body = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "inspect me"}],
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/chat/completions", json=request_body)
        requests = (await client.get("/__lmmock/api/requests")).json()
    assert response.status_code == 200
    assert requests[0]["request"] == request_body
    assert requests[0]["response"]["choices"][0]["message"]["content"] == "LMMock is running."
