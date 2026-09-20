<p align="center">
  <img src="src/lmmock/static/logo.svg" alt="LMMock" width="132" height="132">
</p>

<h1 align="center">LMMock</h1>

<p align="center"><strong>Mock the model. Run the real app.</strong></p>

<p align="center">A visual mock server for OpenAI and Anthropic APIs.</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/lewismosciski/LMMOCK/ci.yml?branch=main&style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/releases"><img src="https://img.shields.io/github/v/release/lewismosciski/LMMOCK?include_prereleases&style=flat-square" alt="Release"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lewismosciski/LMMOCK?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
</p>

LMMock gives AI applications deterministic model replies without changing their SDK calls. Configure models, interfaces, behavior groups, and rules in the browser, then run the real application without provider tokens.

## Quick start

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 run.py                  # Windows: py run.py
```

Or use Docker:

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  -v lmmock-data:/data ghcr.io/lewismosciski/lmmock:latest
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Standalone Linux, macOS, and Windows builds are on the [Releases page](https://github.com/lewismosciski/LMMOCK/releases).

## Models, behavior groups, and rules

- **Models** are the names your application is allowed to request. Add real-looking names such as `gpt-5-mock` or `claude-mock` and choose a default.
- **Interfaces** can be enabled independently in Configuration.
- **Behavior groups** isolate sets of rules, such as `happy-path`, `tool-calls`, and `failures`.
- **Rules** belong to one group and match every request, contained text, or a regular expression.

The active group is used by default. Select another group per request with `x-lmmock-group: happy-path` or `x-lmmock-group: 2`.

## Supported APIs

| Provider | Endpoint | JSON | Streaming | Tool calls |
| --- | --- | :---: | :---: | :---: |
| OpenAI | `POST /v1/completions` | ✓ | ✓ | — |
| OpenAI | `POST /v1/chat/completions` | ✓ | ✓ | ✓ |
| OpenAI | `POST /v1/responses` | ✓ | ✓ | ✓ |
| OpenAI | `GET /v1/models` | ✓ | — | — |
| Anthropic | `POST /v1/messages` | ✓ | ✓ | ✓ |
| Anthropic | `POST /v1/messages/count_tokens` | ✓ | — | — |
| Anthropic | `GET /v1/models` | ✓ | — | — |

List every configured model:

```bash
curl http://127.0.0.1:8000/v1/models
```

## SDK examples

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="mock")

client.completions.create(model="mock-model", prompt="hello")
client.chat.completions.create(
    model="mock-model",
    messages=[{"role": "user", "content": "hello"}],
)
client.responses.create(model="mock-model", input="hello")
client.models.list()
```

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://127.0.0.1:8000", api_key="mock")
client.messages.create(
    model="mock-model",
    max_tokens=128,
    messages=[{"role": "user", "content": "hello"}],
)
client.models.list()
```

## Use with Claude Code

LMMock exposes Anthropic-format Messages and Models APIs. Start LMMock with a key, point Claude Code to it, enable gateway model discovery, then choose `mock-model` from `/model`:

```bash
export LMMOCK_API_KEY="local-test-key"
python3 run.py

export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
export ANTHROPIC_AUTH_TOKEN="$LMMOCK_API_KEY"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
claude
```

Run `/status` to verify the base URL. See Anthropic's [gateway connection documentation](https://code.claude.com/docs/en/llm-gateway-connect) for persistent configuration.

## Use with Codex CLI

Add a custom provider to your user-level `~/.codex/config.toml`:

```toml
model = "mock-model"
model_provider = "lmmock"

[model_providers.lmmock]
name = "LMMock"
base_url = "http://127.0.0.1:8000/v1"
env_key = "LMMOCK_API_KEY"
wire_api = "responses"
```

Then start both processes with the same local key:

```bash
export LMMOCK_API_KEY="local-test-key"
python3 run.py
codex
```

Codex provider settings belong in the user configuration, not a project-local file. See the official OpenAI documentation for [custom model providers](https://developers.openai.com/es-419/docs/config-file/config-advanced#proveedores-de-modelos-personalizados) and the [configuration reference](https://developers.openai.com/es-419/docs/config-file/config-reference).

## Network access and API keys

Localhost is the safe default. To share LMMock on a LAN or behind a reverse proxy, bind to all interfaces and require a key:

```bash
export LMMOCK_API_KEY="choose-a-long-random-key"
python3 run.py --host 0.0.0.0
```

Clients may send the key as `Authorization: Bearer ...` or `x-api-key: ...`. The equivalent environment variables are `LMMOCK_HOST` and `LMMOCK_API_KEY`. Read [SECURITY.md](SECURITY.md) before exposing the server.

Provider forwarding is optional and off by default. Real upstream keys come only from `LMMOCK_OPENAI_API_KEY` and `LMMOCK_ANTHROPIC_API_KEY`; they are never returned by the management API.

## Contributing

Contributions of every size are very welcome. Issues and pull requests are always appreciated—see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
