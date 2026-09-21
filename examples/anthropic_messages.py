"""Call LMMock through the Anthropic Messages API."""

import os

from anthropic import Anthropic


client = Anthropic(
    base_url=os.getenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:17321/anthropic"),
    api_key=os.getenv("ANTHROPIC_API_KEY", "mock"),
)

message = client.messages.create(
    model=os.getenv("ANTHROPIC_MODEL", "claude-5-1-opus"),
    max_tokens=128,
    messages=[{"role": "user", "content": "Hello from the Anthropic Messages example."}],
)

print("".join(block.text for block in message.content if block.type == "text"))
