<p align="center">
  <img src="src/lmmock/static/hero.svg" alt="LMMock — Mock the model. Run the real app." width="100%">
</p>

<p align="center">A visual mock server for OpenAI and Anthropic APIs.</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/lewismosciski/LMMOCK/ci.yml?branch=main&style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/releases"><img src="https://img.shields.io/github/v/release/lewismosciski/LMMOCK?include_prereleases&style=flat-square" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
</p>

LMMock gives AI applications deterministic model replies without changing their SDK calls. Configure models, interfaces, behavior groups, and rules in the browser, then run the real application without provider tokens.

- **Lightweight:** one local service with SQLite storage and no external infrastructure.
- **Easy to use:** configure models and reusable rules in the browser, then change only your SDK Base URL.
- **Broadly compatible:** mock OpenAI Chat Completions, Completions, Responses, and Anthropic Messages.
- **Cross-platform:** run from source, Docker, or a Linux, macOS, or Windows release archive.
- **No provider cost:** deterministic testing without real API calls or tokens.

## Quick start

### Release archive (no Python required)

Download the archive for your system from [Releases](https://github.com/lewismosciski/LMMOCK/releases), extract it, run `lmmock` (`lmmock.exe` on Windows), then open [http://127.0.0.1:17321](http://127.0.0.1:17321).

### From source

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 run.py
```

### Docker

```bash
docker run --rm -p 127.0.0.1:17321:17321 \
  -v lmmock-data:/data ghcr.io/lewismosciski/lmmock:latest
```

## Models, behavior groups, and rules

You only need to configure a model, add a rule, and point your application's SDK to LMMock.

<p align="center"><img src=".github/assets/lmmock-ui.png" alt="LMMock browser interface" width="100%"></p>

1. In **Models, interfaces & API keys**, keep the model name used by your app, choose OpenAI-compatible or Anthropic, and assign one or more behavior groups.
2. In **Rules**, select a template or define what to match and what LMMock should return. Rules can return text, JSON, tool calls, errors, or exact-size random data.
3. Change only the SDK Base URL: use `http://127.0.0.1:17321/openai/v1` for OpenAI-compatible clients or `http://127.0.0.1:17321/anthropic` for Anthropic clients.

Use the Playground to try a rule immediately. Recent requests shows the full request, response, and estimated token usage.

## Supported APIs

| Provider | Endpoint | JSON | Streaming | Tool calls |
| --- | --- | :---: | :---: | :---: |
| OpenAI-compatible | `POST /openai/v1/completions` | ✓ | ✓ | — |
| OpenAI-compatible | `POST /openai/v1/chat/completions` | ✓ | ✓ | ✓ |
| OpenAI-compatible | `POST /openai/v1/responses` | ✓ | ✓ | ✓ |
| OpenAI-compatible | `GET /openai/v1/models` | ✓ | — | — |
| Anthropic | `POST /anthropic/v1/messages` | ✓ | ✓ | ✓ |
| Anthropic | `POST /anthropic/v1/messages/count_tokens` | ✓ | — | — |
| Anthropic | `GET /anthropic/v1/models` | ✓ | — | — |

List configured models for each interface:

```bash
curl http://127.0.0.1:17321/openai/v1/models
curl http://127.0.0.1:17321/anthropic/v1/models
```

## SDK examples

Runnable examples for OpenAI Chat Completions, Completions, Responses, and Anthropic Messages are in [`examples/`](examples/README.md). They use the official Python SDKs and connect only to your local LMMock server by default.

## Use with Claude Code

LMMock exposes Anthropic-format Messages and Models APIs. Configure the built-in Anthropic model `claude-5-1-opus` with API key `local-test-key`, point Claude Code to LMMock, enable gateway model discovery, then choose `claude-5-1-opus` from `/model`:

```bash
python3 run.py

export ANTHROPIC_BASE_URL="http://127.0.0.1:17321/anthropic"
export ANTHROPIC_AUTH_TOKEN="local-test-key"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
claude
```

Run `/status` to verify the base URL. See Anthropic's [gateway connection documentation](https://code.claude.com/docs/en/llm-gateway-connect) for persistent configuration.

## Use with Codex CLI

Add a custom provider to your user-level `~/.codex/config.toml`:

```toml
model = "gpt-5.6-sol"
model_provider = "lmmock"

[model_providers.lmmock]
name = "LMMock"
base_url = "http://127.0.0.1:17321/openai/v1"
env_key = "LMMOCK_API_KEY"
wire_api = "responses"
```

Set the `gpt-5.6-sol` row's API key to `local-test-key` in Configuration. The environment variable below is read by Codex because `env_key` points to it; LMMock checks it against that model's visible key:

```bash
export LMMOCK_API_KEY="local-test-key"
python3 run.py
codex
```

Codex provider settings belong in the user configuration, not a project-local file. See the official OpenAI documentation for [custom model providers](https://developers.openai.com/es-419/docs/config-file/config-advanced#proveedores-de-modelos-personalizados) and the [configuration reference](https://developers.openai.com/es-419/docs/config-file/config-reference).

## Mock multiple model backends

For an existing multi-agent application, keep every original model name and change only its base URL:

- OpenAI, DeepSeek, GLM, and other OpenAI-compatible clients: `http://127.0.0.1:17321/openai/v1`
- Claude or Anthropic clients: `http://127.0.0.1:17321/anthropic`

Add one Configuration row for every existing name—such as `gpt-4o`, `deepseek-chat`, `claude-3-7-sonnet`, and `glm-4-plus`. Select its interface, enter the key already used by that client (or leave it blank to accept any key), and check one or more behavior groups. Rules from those groups are combined by priority; their Models field can further narrow a rule with an exact name or comma-separated globs such as `gpt-*, o3-*`.

## Network access and API keys

Localhost is the safe default. To share LMMock on a trusted LAN, bind to all interfaces:

```bash
python3 run.py --host 0.0.0.0
```

Then open Configuration and optionally set a different Mock API key for each model. Keys are intentionally visible in the web UI and stored in the local SQLite database. They protect generation and token-count requests for their model; model discovery, the management UI, and management API remain open.

## Contributing

Contributions of every size are very welcome. Issues and pull requests are always appreciated—see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
