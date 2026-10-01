import httpx
import pytest


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as session:
        yield session


@pytest.mark.parametrize("scopes", ["chat", "", {}, {"chat": True}, 0, False, 1, [None], [1], [{}], ["chta"], ["chat", "unknown"]])
async def test_invalid_scopes_are_rejected_without_changing_rules(client, scopes):
    before = (await client.get("/__lmmock/api/rules")).json()
    for method, path in (("POST", "/__lmmock/api/rules"), ("PUT", f"/__lmmock/api/rules/{before[0]['id']}")):
        response = await client.request(method, path, json={"scopes": scopes})
        assert response.status_code == 400
        assert "scopes" in response.json()["error"]
        assert (await client.get("/__lmmock/api/rules")).json() == before


@pytest.mark.parametrize("scopes", [["*"], ["chat"], ["completions"], ["responses"], ["messages"], ["generateContent"], ["chat", "responses"]])
async def test_supported_scopes_are_preserved(client, scopes):
    response = await client.post("/__lmmock/api/rules", json={"scopes": scopes})
    assert response.status_code == 201
    rule = response.json()
    assert rule["scopes"] == scopes
    response = await client.put(f"/__lmmock/api/rules/{rule['id']}", json=rule)
    assert response.status_code == 200
    assert response.json()["scopes"] == scopes


@pytest.mark.parametrize("body", [{}, {"scopes": None}, {"scopes": []}])
async def test_unspecified_scopes_keep_wildcard_default(client, body):
    response = await client.post("/__lmmock/api/rules", json=body)
    assert response.status_code == 201
    assert response.json()["scopes"] == ["*"]


async def test_multi_scope_rule_matches_only_selected_operations(client):
    response = await client.post("/__lmmock/api/rules", json={
        "priority": 1, "scopes": ["chat", "completions"], "reply": {"content": "scoped reply"},
    })
    assert response.status_code == 201
    chat = await client.post("/openai/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]})
    assert chat.json()["choices"][0]["message"]["content"] == "scoped reply"
    completion = await client.post("/openai/v1/completions", json={"prompt": "hello"})
    assert completion.json()["choices"][0]["text"] == "scoped reply"
    other = await client.post("/anthropic/v1/messages", json={"messages": [{"role": "user", "content": "hello"}]})
    assert other.status_code == 200
    assert other.json()["content"][0]["text"] != "scoped reply"
