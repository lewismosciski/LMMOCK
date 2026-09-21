"""Call LMMock through the OpenAI Completions API."""

import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:17321/openai/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "mock"),
)

completion = client.completions.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
    prompt="Hello from the Completions example.",
    max_tokens=128,
)

print(completion.choices[0].text)
