import json

import httpx
import pytest


def anthropic_events(response: httpx.Response) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = ""
    for line in response.text.splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            events.append((event_name, json.loads(line.removeprefix("data: "))))
    return events


async def configure_claude_key(client: httpx.AsyncClient) -> None:
    settings = (await client.get("/__lmmock/api/settings")).json()
    model = next(item for item in settings["model_configs"] if item["name"] == "claude-5-1-opus")
    model["api_key"] = "claude-test-key"
    response = await client.put("/__lmmock/api/settings", json={"model_configs": settings["model_configs"]})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_claude_code_discovery_and_messages_stream_contract(app):
    """Exercise model discovery and the Messages request shape used by Claude Code."""
    headers = {
        "authorization": "Bearer claude-test-key",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "prompt-caching-2024-07-31",
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await configure_claude_key(client)
        models = await client.get("/anthropic/v1/models?limit=1000", headers=headers)
        response = await client.post(
            "/anthropic/v1/messages?beta=true",
            headers=headers,
            json={
                "model": "claude-5-1-opus",
                "max_tokens": 1024,
                "system": [{"type": "text", "text": "You are Claude Code."}],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "hello"}]},
                ],
                "tools": [],
                "metadata": {"user_id": "claude-code-test"},
                "stream": True,
            },
        )

    assert models.status_code == 200
    assert [model["id"] for model in models.json()["data"]] == ["claude-5-1-opus"]
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = anthropic_events(response)
    assert [name for name, _ in events] == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    text_delta = next(data for name, data in events if name == "content_block_delta")
    assert text_delta["delta"] == {"type": "text_delta", "text": "LMMock is running."}
    assert events[-1][1]["type"] == "message_stop"


@pytest.mark.asyncio
async def test_claude_code_tool_use_stream_contract(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/__lmmock/api/rules", json={
            "name": "Claude Code tool",
            "priority": 1,
            "scopes": ["messages"],
            "match_type": "contains",
            "match_value": "read a file",
            "reply_type": "tool",
            "reply": {"tool_name": "Read", "arguments": {"file_path": "/tmp/example.txt"}},
        })
        assert created.status_code == 201
        response = await client.post("/anthropic/v1/messages?beta=true", json={
            "model": "claude-5-1-opus",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "read a file"}]}],
            "tools": [{
                "name": "Read",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            }],
            "stream": True,
        })

    events = anthropic_events(response)
    block_start = next(data for name, data in events if name == "content_block_start")
    json_delta = next(data for name, data in events if name == "content_block_delta")
    message_delta = next(data for name, data in events if name == "message_delta")
    assert block_start["content_block"]["type"] == "tool_use"
    assert block_start["content_block"]["name"] == "Read"
    assert json.loads(json_delta["delta"]["partial_json"]) == {"file_path": "/tmp/example.txt"}
    assert message_delta["delta"]["stop_reason"] == "tool_use"
