<p align="center">
  <img src="src/lmmock/static/logo.svg" alt="LMMock" width="132" height="132">
</p>

<h1 align="center">LMMock</h1>

<p align="center"><strong>Mock the model. Run the real app.</strong></p>

<p align="center">A local, visual mock server for OpenAI and Anthropic APIs.</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/lewismosciski/LMMOCK/ci.yml?branch=main&style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/releases"><img src="https://img.shields.io/github/v/release/lewismosciski/LMMOCK?include_prereleases&style=flat-square" alt="Release"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lewismosciski/LMMOCK?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
</p>

LMMock gives your application predictable model replies without changing its SDK calls. Create a rule in the browser, point the app at localhost, and run the real flow without a provider key or token spend.

## Quick start

From a checkout:

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 run.py                  # Windows: py run.py
```

Or with Docker:

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  -v lmmock-data:/data ghcr.io/lewismosciski/lmmock:latest
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Release archives for Linux, macOS, and Windows are available on the [Releases page](https://github.com/lewismosciski/LMMOCK/releases).

## Point your SDK at it

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="mock")
answer = client.responses.create(model="mock-model", input="weather in Shanghai")
print(answer.output_text)
```

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

## Supported APIs

| Provider | Endpoint | JSON | Streaming | Tool calls |
| --- | --- | :---: | :---: | :---: |
| OpenAI | `POST /v1/chat/completions` | ✓ | ✓ | ✓ |
| OpenAI | `POST /v1/responses` | ✓ | ✓ | ✓ |
| Anthropic | `POST /v1/messages` | ✓ | ✓ | ✓ |

Rules can match all requests, text, or a regular expression. Replies can contain text, JSON text, tool calls, HTTP errors, capture templates, and a fixed delay. Rules and provider settings live in a local SQLite file.

Upstream forwarding is optional and off by default. Provider keys are read from `LMMOCK_OPENAI_API_KEY` and `LMMOCK_ANTHROPIC_API_KEY`; LMMock never writes them to SQLite.

## Contributing

Bug reports, protocol fixtures, documentation fixes, and focused pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

LMMock stays focused on local mocking. Traffic recording, cassette replay, and a CI product are outside its scope.

## License

Apache-2.0
