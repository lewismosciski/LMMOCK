import json

import httpx
import pytest


def response_events(response: httpx.Response) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


async def configure_codex_key(client: httpx.AsyncClient) -> None:
    settings = (await client.get("/__lmmock/api/settings")).json()
    model = next(item for item in settings["model_configs"] if item["name"] == "gpt-5.6-sol")
    model["api_key"] = "codex-test-key"
    response = await client.put("/__lmmock/api/settings", json={"model_configs": settings["model_configs"]})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_codex_responses_stream_contract(app):
    """Exercise the Responses request shape used by Codex CLI."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await configure_codex_key(client)
        response = await client.post(
            "/openai/v1/responses",
            headers={"authorization": "Bearer codex-test-key"},
            json={
                "model": "gpt-5.6-sol",
                "instructions": "Reply using the mock provider.",
                "input": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "hello"}],
                    }
                ],
                "tools": [],
                "tool_choice": "auto",
                "parallel_tool_calls": True,
                "reasoning": {"effort": "medium"},
                "include": ["reasoning.encrypted_content"],
                "store": False,
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = response_events(response)
    event_types = [event["type"] for event in events]
    assert event_types[0:2] == ["response.created", "response.in_progress"]
    assert "response.output_text.delta" in event_types
    assert event_types[-1] == "response.completed"

    added = next(event for event in events if event["type"] == "response.output_item.added")
    done = next(event for event in events if event["type"] == "response.output_item.done")
    completed = events[-1]["response"]
    assert done["item"]["id"] == added["item"]["id"]
    assert done["item"]["content"][0]["text"] == "LMMock is running."
    assert completed["status"] == "completed"
    assert completed["output"] == [done["item"]]


@pytest.mark.asyncio
async def test_codex_function_call_stream_contract(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/__lmmock/api/rules", json={
            "name": "Codex tool",
            "priority": 1,
            "scopes": ["responses"],
            "match_type": "contains",
            "match_value": "use weather tool",
            "reply_type": "tool",
            "reply": {"tool_name": "get_weather", "arguments": {"city": "Shanghai"}},
        })
        assert created.status_code == 201
        response = await client.post("/openai/v1/responses", json={
            "model": "gpt-5.6-sol",
            "input": "use weather tool",
            "tools": [{
                "type": "function",
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                "strict": False,
            }],
            "stream": True,
        })

    events = response_events(response)
    added = next(event for event in events if event["type"] == "response.output_item.added")
    arguments_done = next(event for event in events if event["type"] == "response.function_call_arguments.done")
    item_done = next(event for event in events if event["type"] == "response.output_item.done")
    assert added["item"]["type"] == "function_call"
    assert item_done["item"]["call_id"] == added["item"]["call_id"]
    assert json.loads(arguments_done["arguments"]) == {"city": "Shanghai"}
    assert item_done["item"]["status"] == "completed"
