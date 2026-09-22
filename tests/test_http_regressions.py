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
