"""Call LMMock through the OpenAI Chat Completions API."""

import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:17321/openai/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "mock"),
)

completion = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
    messages=[{"role": "user", "content": "Hello from the Chat Completions example."}],
)

print(completion.choices[0].message.content)
