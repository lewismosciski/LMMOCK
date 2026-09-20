<p align="center">
  <img src="docs/assets/lmmock.svg" alt="LMMock" width="128" height="128">
</p>

<h1 align="center">LMMock</h1>

<p align="center"><strong>Mock the model. Run the real app.</strong></p>

<p align="center">A local, visual mock server for LLM APIs.</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/stargazers"><img src="https://img.shields.io/github/stars/lewismosciski/LMMOCK?style=flat-square" alt="GitHub stars"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lewismosciski/LMMOCK?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11 or newer">
</p>

LMMock lets an OpenAI or Anthropic SDK talk to a predictable local server. Write a rule in the browser, point your existing app at LMMock, and keep the rest of the app unchanged.

No real provider keys. No model calls. No token spend.

## Quick start

### Docker

```bash
git clone git@github.com:lewismosciski/LMMOCK.git
cd LMMOCK
docker compose up --build
```

### Source checkout

```bash
python3 run.py       # Windows: py run.py
```

The launcher creates `.venv`, installs the checkout, and opens the server at [localhost:8000](http://127.0.0.1:8000). Python 3.11+ is required.

### Python tools

```bash
uvx lmmock
# or: pipx run lmmock
```

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

| Provider | Endpoint |
| --- | --- |
| OpenAI | `POST /v1/chat/completions` |
| OpenAI | `POST /v1/responses` |
| Anthropic | `POST /v1/messages` |

Rules support text, JSON text, tool calls, errors, templates, streaming, and a built-in Playground. The default is mock-only. Optional upstream forwarding is available in Provider Settings; keys come from `LMMOCK_OPENAI_API_KEY` and `LMMOCK_ANTHROPIC_API_KEY` and are never written to SQLite.

## Scope

LMMock is a small mock server. It does not record traffic, replay cassettes, or turn into a CI product.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

More detail lives in [the development plan](docs/development-plan.md), [the distribution plan](docs/distribution-and-launch.md), and [the research notes](docs/research.md).

## License

Apache-2.0
