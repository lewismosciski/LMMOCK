import json

import httpx
import pytest

from lmmock.app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path)


@pytest.mark.asyncio
async def test_health_ui_and_default_chat(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.json()["ok"] is True
        assert "LMMock" in (await client.get("/")).text
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
            "mode_openai": "proxy-only",
            "openai_base_url": "https://api.openai.com",
        })
        settings = await client.get("/__lmmock/api/settings")
        invalid = await client.put("/__lmmock/api/settings", json={"mode_openai": "unsafe"})
    assert saved.status_code == 200
    assert settings.json()["mode_openai"] == "proxy-only"
    assert settings.json()["openai_base_url"] == "https://api.openai.com"
    assert "api_key" not in settings.json()
    assert invalid.status_code == 400
