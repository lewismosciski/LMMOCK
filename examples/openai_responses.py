"""Call LMMock through the OpenAI Responses API."""

import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:17321/openai/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "mock"),
)

response = client.responses.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
    input="Hello from the Responses example.",
)

print(response.output_text)
