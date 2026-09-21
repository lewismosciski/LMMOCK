"""Add gemini-2.5-flash with the Gemini interface in the UI before running."""

import os

from google import genai
from google.genai import types


with genai.Client(
    vertexai=False,
    api_key=os.getenv("GEMINI_API_KEY", "mock"),
    http_options=types.HttpOptions(
        base_url=os.getenv("GEMINI_BASE_URL", "http://127.0.0.1:17321/gemini"),
        api_version="v1beta",
    ),
) as client:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    print(client.models.generate_content(model=model, contents="Hello").text)
    for chunk in client.models.generate_content_stream(model=model, contents="Hello"):
        print(chunk.text or "", end="", flush=True)
    print()
    print("Estimated tokens:", client.models.count_tokens(model=model, contents="Hello").total_tokens)
    print("Models:", [item.name for item in client.models.list()])
