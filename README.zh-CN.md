<p align="center">
  <img src="src/lmmock/static/logo.svg" alt="LMMock" width="132" height="132">
</p>

<h1 align="center">LMMock</h1>

<p align="center"><strong>Mock 模型，运行真实应用。</strong></p>

<p align="center">面向 OpenAI 与 Anthropic API 的可视化 Mock Server。</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/lewismosciski/LMMOCK/ci.yml?branch=main&style=flat-square&label=tests" alt="测试状态"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/releases"><img src="https://img.shields.io/github/v/release/lewismosciski/LMMOCK?include_prereleases&style=flat-square" alt="发行版本"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="MIT 开源协议"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
</p>

LMMock 让 AI 应用获得稳定可控的模型回复，同时保留原有 SDK 调用。你可以在网页中配置模型、接口、行为组与规则，无需真实 Provider Token 即可运行应用。

## 快速启动

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 run.py                  # Windows: py run.py
```

或使用 Docker：

```bash
docker run --rm -p 127.0.0.1:17321:17321 \
  -v lmmock-data:/data ghcr.io/lewismosciski/lmmock:latest
```

打开 [http://127.0.0.1:17321](http://127.0.0.1:17321)。Linux、macOS 与 Windows 独立程序可在 [Releases 页面](https://github.com/lewismosciski/LMMOCK/releases)下载。

## 模型、行为组与规则

- **模型**：保留应用已经使用的名称。每个模型独立选择 OpenAI 兼容或 Anthropic 接口、直接显示的 Mock API Key，以及一个或多个行为组。
- **行为组**：隔离可复用的规则集合，例如 `happy-path`、`tool-calls`、`failures`；一个模型可以组合多个组。
- **规则**：归属于一个行为组，可以限定精确模型名或 `gpt-*` 这样的通配模式，并匹配全部请求、包含文本或正则表达式。

请求默认按优先级匹配该模型绑定的全部行为组。也可以通过 `x-lmmock-group: happy-path` 或数字 ID，将单次请求限定到其中一个已绑定的行为组。

新工作区的默认行为组包含一条可编辑的 `foolAI` 示例规则，例如把 `你吃饭了吗？` 稳定回复为 `我吃饭了！`；也可以从模板列表再次创建它。

## 支持的 API

| Provider | Endpoint | JSON | 流式响应 | 工具调用 |
| --- | --- | :---: | :---: | :---: |
| OpenAI 兼容 | `POST /openai/v1/completions` | ✓ | ✓ | — |
| OpenAI 兼容 | `POST /openai/v1/chat/completions` | ✓ | ✓ | ✓ |
| OpenAI 兼容 | `POST /openai/v1/responses` | ✓ | ✓ | ✓ |
| OpenAI 兼容 | `GET /openai/v1/models` | ✓ | — | — |
| Anthropic | `POST /anthropic/v1/messages` | ✓ | ✓ | ✓ |
| Anthropic | `POST /anthropic/v1/messages/count_tokens` | ✓ | — | — |
| Anthropic | `GET /anthropic/v1/models` | ✓ | — | — |

分别查看两个接口已配置的模型：

```bash
curl http://127.0.0.1:17321/openai/v1/models
curl http://127.0.0.1:17321/anthropic/v1/models
```

## SDK 示例

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:17321/openai/v1", api_key="mock")

client.completions.create(model="mock-model", prompt="hello")
client.chat.completions.create(
    model="mock-claude",
    messages=[{"role": "user", "content": "hello"}],
)
client.responses.create(model="mock-model", input="hello")
client.models.list()
```

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://127.0.0.1:17321/anthropic", api_key="mock")
client.messages.create(
    model="mock-model",
    max_tokens=128,
    messages=[{"role": "user", "content": "hello"}],
)
client.models.list()
```

## 在 Claude Code 中使用

LMMock 提供 Anthropic Messages 和 Models 兼容接口。先配置一个名为 `mock-claude` 的 Anthropic 模型，并将它的 API Key 设为 `local-test-key`；再把 Claude Code 指向本地服务，开启 Gateway 模型发现，然后在 `/model` 中选择 `mock-claude`：

```bash
python3 run.py

export ANTHROPIC_BASE_URL="http://127.0.0.1:17321/anthropic"
export ANTHROPIC_AUTH_TOKEN="local-test-key"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
claude
```

可以运行 `/status` 检查 Base URL。持久化配置方式见 Anthropic 官方的 [Gateway 接入文档](https://code.claude.com/docs/en/llm-gateway-connect)。

## 在 Codex CLI 中使用

在用户级 `~/.codex/config.toml` 中添加自定义 Provider：

```toml
model = "mock-model"
model_provider = "lmmock"

[model_providers.lmmock]
name = "LMMock"
base_url = "http://127.0.0.1:17321/openai/v1"
env_key = "LMMOCK_API_KEY"
wire_api = "responses"
```

先在 Configuration 中把 `mock-model` 这一行的 API Key 设为 `local-test-key`。下面的环境变量由 Codex 读取，因为 `env_key` 指向它；LMMock 会和该模型直接显示的 Key 比较：

```bash
export LMMOCK_API_KEY="local-test-key"
python3 run.py
codex
```

Codex 的 Provider 设置必须放在用户级配置中，而不是项目本地配置。可参考 OpenAI 官方的[自定义模型 Provider](https://developers.openai.com/es-419/docs/config-file/config-advanced#proveedores-de-modelos-personalizados)与[配置参考](https://developers.openai.com/es-419/docs/config-file/config-reference)。

## Mock 多个模型后端

对于已有的多 Agent 应用，保留全部原始模型名，只修改 Base URL：

- OpenAI、DeepSeek、GLM 以及其他 OpenAI 兼容客户端：`http://127.0.0.1:17321/openai/v1`
- Claude 或 Anthropic 客户端：`http://127.0.0.1:17321/anthropic`

在 Configuration 中为应用现有的每个模型建立一行，例如 `gpt-4o`、`deepseek-chat`、`claude-3-7-sonnet` 和 `glm-4-plus`。分别选择接口格式、填写该客户端已经使用的 Key（留空则接受任意 Key），并勾选一个或多个行为组。LMMock 会按优先级合并这些组中的规则；规则的“适用模型”还可以用精确名称或 `gpt-*, o3-*` 进一步筛选。

## 网络访问与 API Key

默认只监听本机。需要在可信局域网共享时，可以监听所有网卡：

```bash
python3 run.py --host 0.0.0.0
```

然后打开 Configuration，按需为每个模型设置不同的 Mock API Key。Key 会直接显示在网页中，并保存在本地 SQLite 数据库；它保护该模型的生成与 Token 计数请求，模型列表、管理页面和管理 API 始终开放。暴露服务前请阅读 [SECURITY.md](SECURITY.md)。

## 参与贡献

我们非常欢迎任何形式、任何规模的贡献。欢迎提交 Issue 或 Pull Request，参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 开源协议

MIT
