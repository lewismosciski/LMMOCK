import json

import httpx
from anthropic import Anthropic, DefaultHttpxClient
from openai import OpenAI


def test_openai_sdk_usage_and_responses_stream(live_server):
    with OpenAI(base_url=live_server + "/openai/v1", api_key="mock", http_client=httpx.Client(trust_env=False)) as sdk:
        chat = sdk.chat.completions.create(model="gpt-5.6-sol", messages=[{"role": "user", "content": "hello"}])
        assert chat.usage.completion_tokens > 0
        completion = sdk.completions.create(model="gpt-5.6-sol", prompt="hello")
        assert completion.usage.prompt_tokens > 0
        chunks = list(sdk.chat.completions.create(model="gpt-5.6-sol", messages=[], stream=True, stream_options={"include_usage": True}))
        assert chunks[-1].usage.completion_tokens > 0
        with sdk.responses.stream(model="gpt-5.6-sol", input="hello") as stream:
            response = stream.get_final_response()
        assert response.output_text == "LMMock is running."
        assert response.usage.output_tokens > 0


def test_openai_sdk_tool_stream(live_server, app):
    app.state.lmmock.store.create_rule({"priority": 1, "reply_type": "tool", "reply": {"tool_name": "weather", "arguments": {"city": "Shanghai"}}})
    with OpenAI(base_url=live_server + "/openai/v1", api_key="mock", http_client=httpx.Client(trust_env=False)) as sdk:
        chunks = list(sdk.chat.completions.create(model="gpt-5.6-sol", messages=[], stream=True))
        calls = [call for chunk in chunks for choice in chunk.choices for call in choice.delta.tool_calls or []]
        assert calls[0].function.name == "weather"
        assert json.loads("".join(call.function.arguments or "" for call in calls)) == {"city": "Shanghai"}
        assert calls[0].id == app.state.lmmock.requests[0]["response"]["choices"][0]["message"]["tool_calls"][0]["id"]


def test_anthropic_sdk_text_and_tool_stream(live_server, app):
    with Anthropic(base_url=live_server + "/anthropic", api_key="mock", http_client=DefaultHttpxClient(trust_env=False)) as sdk:
        message = sdk.messages.create(model="claude-5-1-opus", max_tokens=128, messages=[{"role": "user", "content": "hello"}])
        assert message.content[0].text == "LMMock is running."
        with sdk.messages.stream(model="claude-5-1-opus", max_tokens=128, messages=[{"role": "user", "content": "hello"}]) as stream:
            assert stream.get_final_message().content[0].text == message.content[0].text
        app.state.lmmock.store.create_rule({"priority": 1, "reply_type": "tool", "reply": {"tool_name": "weather", "arguments": {"city": "Shanghai"}}})
        with sdk.messages.stream(model="claude-5-1-opus", max_tokens=128, messages=[{"role": "user", "content": "hello"}]) as stream:
            message = stream.get_final_message()
        assert message.content[0].input == {"city": "Shanghai"}
        assert message.content[0].id == app.state.lmmock.requests[0]["response"]["content"][0]["id"]
