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
