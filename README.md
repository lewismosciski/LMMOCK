# LMMock

**Mock the model. Run the real app.**

Local, visual mock server for OpenAI Chat/Responses and Anthropic Messages. Edit a reply in the browser, point your SDK at LMMock, and keep the rest of your app unchanged.

No real provider keys. No model calls. No token spend.

## Start

### Docker

```bash
docker compose up --build
```

Or build a local image and run it directly:

```bash
docker build -t lmmock:local .
docker run --rm -p 127.0.0.1:8000:8000 -v lmmock-data:/data lmmock:local
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### From a checkout

```bash
# after cloning this repository
cd lmmock
python3 run.py       # Windows: py run.py
```

The launcher creates a local `.venv` and starts the server. It needs Python 3.11+ and downloads dependencies on the first run.

### Python tools

```bash
uvx lmmock
# or: pipx run lmmock
```

GitHub Release binaries are planned for Linux, macOS, and Windows. See [distribution and launch](docs/distribution-and-launch.md) for the full matrix.

## Point your SDK at it

OpenAI:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="mock")
answer = client.responses.create(model="mock-model", input="weather in Shanghai")
print(answer.output_text)
```

Anthropic:

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://127.0.0.1:8000", api_key="mock")
answer = client.messages.create(
    model="mock-model",
    max_tokens=128,
    messages=[{"role": "user", "content": "weather in Shanghai"}],
)
print(answer.content[0].text)
```

## What it mocks

- OpenAI `POST /v1/chat/completions`
- OpenAI `POST /v1/responses`
- Anthropic `POST /v1/messages`
- Text, JSON text, tool calls, errors, usage, streaming, and model lists
- Browser rules with contains/regex matching, templates, ordering, and a playground

The default is mock-only. Optional upstream forwarding lives under Advanced Settings and is off until you configure it.
Provider keys are read from `LMMOCK_OPENAI_API_KEY` and `LMMOCK_ANTHROPIC_API_KEY`; they are never stored in the rule database.

## Scope

LMMock is a small mock server. It does not record traffic, replay cassettes, run a CI product, or pretend to be a complete provider implementation.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

See:

- [Development plan](docs/development-plan.md)
- [Distribution and launch](docs/distribution-and-launch.md)
- [Research](docs/research.md)

## License

Apache-2.0
