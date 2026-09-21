<p align="center">
  <img src="src/lmmock/static/hero.svg" alt="LMMock — Mock 模型，运行真实应用。" width="100%">
</p>

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

- **轻量化：**单个本地服务、SQLite 存储，不依赖外部基础设施。
- **简单易用：**在网页中配置模型和可复用规则，只需修改 SDK Base URL。
- **广泛兼容：**支持 Mock OpenAI Chat Completions、Completions、Responses 和 Anthropic Messages。
- **跨平台：**支持源码、Docker，以及 Linux、macOS、Windows Release 压缩包。
- **零 Provider 成本：**无需真实 API 请求或 Token，即可获得稳定可控的测试结果。

## 快速启动

### Release 压缩包（无需 Python）

前往 [Releases](https://github.com/lewismosciski/LMMOCK/releases) 下载对应系统的压缩包，解压后运行 `lmmock`（Windows 为 `lmmock.exe`），再打开 [http://127.0.0.1:17321](http://127.0.0.1:17321)。

### 从源码启动

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

## 模型、行为组与规则

你只需要配置模型、添加规则，再把应用的 SDK 指向 LMMock。

<p align="center"><img src=".github/assets/lmmock-ui.png" alt="LMMock 网页界面" width="100%"></p>

1. 在**模型、接口与 API 密钥**中保留应用原本使用的模型名，选择 OpenAI 兼容或 Anthropic 接口，并绑定一个或多个行为组。
2. 在**规则**中选择模板，或者自行设置匹配条件和回复。规则可以返回文本、JSON、工具调用、错误或指定大小的随机数据。
3. 只修改 SDK Base URL：OpenAI 兼容客户端使用 `http://127.0.0.1:17321/openai/v1`，Anthropic 客户端使用 `http://127.0.0.1:17321/anthropic`。

使用 Playground 可以立即验证规则；最近请求会展示完整请求、响应和 Token 估算。

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

[`examples/`](examples/README.md) 提供可直接运行的 OpenAI Chat Completions、Completions、Responses 和 Anthropic Messages 示例。它们使用官方 Python SDK，默认只连接本地 LMMock 服务。

## 在 Claude Code 中使用

LMMock 提供 Anthropic Messages 和 Models 兼容接口。先把内置 Anthropic 模型 `claude-5-1-opus` 的 API Key 设为 `local-test-key`；再把 Claude Code 指向本地服务，开启 Gateway 模型发现，然后在 `/model` 中选择 `claude-5-1-opus`：

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
model = "gpt-5.6-sol"
model_provider = "lmmock"

[model_providers.lmmock]
name = "LMMock"
base_url = "http://127.0.0.1:17321/openai/v1"
env_key = "LMMOCK_API_KEY"
wire_api = "responses"
```

先在 Configuration 中把 `gpt-5.6-sol` 这一行的 API Key 设为 `local-test-key`。下面的环境变量由 Codex 读取，因为 `env_key` 指向它；LMMock 会和该模型直接显示的 Key 比较：

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

然后打开 Configuration，按需为每个模型设置不同的 Mock API Key。Key 会直接显示在网页中，并保存在本地 SQLite 数据库；它保护该模型的生成与 Token 计数请求，模型列表、管理页面和管理 API 始终开放。

## 参与贡献

我们非常欢迎任何形式、任何规模的贡献。欢迎提交 Issue 或 Pull Request，参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 友情链接

- [LINUX DO](https://linux.do/)

## 开源协议

MIT
