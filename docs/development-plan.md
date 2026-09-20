# LMMock 完整开发规划

版本：Draft 4
日期：2026-09-20
定位：以可视化规则 Mock 为核心的多协议 LLM API Test Double

## 0. 最终方向

### 名称

项目推荐名为 **LMMock**，Python 包与 CLI 均使用 `lmmock`。名称只有 6 个字符，直接表达 “Language Model Mock”，不绑定 OpenAI、Anthropic 或某个 Agent 框架。

截至规划日，PyPI、npm、GitHub 独立仓库/组织名及 `.com/.dev/.ai` RDAP 查询未发现占用；但 `frankfliu/junkyard` 中已有一个同名 Rust/Cargo 子项目在实现 OpenAI Mock Server，因此不能称为零冲突。开始开发时必须完成最终名称决策、基础商标检查并实际预留发行资产。

### 产品只解决三件事

1. 用一组简单规则 Mock OpenAI 与 Anthropic 原生接口。
2. 在浏览器中创建、修改、排序、预览这些规则。
3. 必要时把某个厂商的请求透明转发到真实 API。

### 主次关系

- **主功能：Mock。** 首页、导航、规则模型、开发顺序和文档都围绕 Mock。
- **小功能：Proxy。** 只放在高级设置中，在 Mock 完整可用后实现。
- **不做：**录制回放、Cassette、CI/pytest 产品、复杂状态机、网关治理、多租户和大规模混沌模拟。

## 1. 产品定义与用户体验

### 一句话

> 在浏览器里写一条规则，让 OpenAI 和 Anthropic SDK 得到你指定的回复。

对外主 slogan：

> **Mock the model. Run the real app.**

成本与隐私副句：

> **No real API keys. No model calls. No token spend.**

副句描述默认 `mock-only` 模式；开启高级 Proxy 后可能访问真实上游并产生费用。

### OpenAI 接入

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="mock",
)

result = client.responses.create(
    model="mock-model",
    input="weather in Shanghai",
)
```

### Anthropic 接入

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="http://127.0.0.1:8000",
    api_key="mock",
)

message = client.messages.create(
    model="mock-model",
    max_tokens=256,
    messages=[{"role": "user", "content": "weather in Shanghai"}],
)
```

OpenAI 的 `base_url` 带 `/v1`，Anthropic 的不带；两套官方 SDK 都沿用原生调用方法。

### 五分钟首次体验

1. 从 GitHub Release 下载对应平台压缩包，解压后运行 `lmmock`；Docker 与 `python run.py` 是同屏替代入口。
2. 浏览器自动打开，无需配置文件、API key、pipx 或账号。
3. 点击“新建第一条规则”。
4. 匹配 `weather in (?P<city>.+)`，回复 `Weather in ${city}: sunny.`。
5. 选择适用接口：OpenAI Chat、OpenAI Responses、Anthropic Messages。
6. 在内置 Playground 逐个预览三种协议，再从真实应用调用。

## 2. 产品原则与非目标

### 原则

1. **页面优先**：普通用户无需写 YAML、Python handler 或完整协议 JSON。
2. **首条命中**：规则按页面顺序匹配，第一条满足全部条件的规则生效。
3. **一条规则，多套协议**：用户写语义回复，adapter 负责各厂商 wire format。
4. **无状态优先**：Agent 第二轮依靠请求中已有的 tool result 匹配，不建立服务端场景状态机。
5. **Mock 默认**：不开启高级设置就永远不会访问外网。
6. **兼容声明可验证**：只承诺 capability matrix 中通过官方 SDK 验证的能力。
7. **扩展靠 adapter**：增加厂商不改变规则引擎，也不把所有协议压成错误的最低公分母。

### 非目标

- 不成为 LiteLLM 式生产 Gateway。
- 不做真实本地模型推理。
- 不根据任意 prompt 自动生成“智能”答案。
- 不做流量录制、回放、fixture 学习或黄金样本管理。
- 不做断言、评测、报告、GitHub Action 或测试编排平台。
- 不做用户、团队、RBAC、SSO、多租户和公网托管。
- 不在首版覆盖十几个 provider。

## 3. 版本范围

### 3.1 P0：公开 0.1.0

| Provider | 方法与路径 | Mock 能力 |
|---|---|---|
| OpenAI | `POST /v1/chat/completions` | 文本、JSON 文本、一个或多个 tool calls、错误、固定延迟、JSON 与 SSE |
| OpenAI | `POST /v1/responses` | output text、一个或多个 function calls、错误、固定延迟、JSON 与 typed SSE |
| Anthropic | `POST /v1/messages` | text blocks、一个或多个 tool_use、错误、固定延迟、JSON 与原生 SSE |
| OpenAI / Anthropic | `GET /v1/models` | 根据 `anthropic-version` header 分派响应格式，返回用户配置的虚拟模型 |
| LMMock | `GET /healthz` | 版本、存活状态和当前是否纯 Mock，不暴露 secret |

P0 同时支持：

- 语义规则跨三个创建接口。
- exact、contains、regex 和 model glob。
- system text、last user text、all text、last tool result。
- required tool 与 has tool result 条件。
- Regex 命名捕获和安全模板。
- 文本、JSON、工具调用、provider-shaped HTTP error。
- 每条规则的固定首包延迟、chunk 大小和 chunk 间隔。
- 内存中的最近请求诊断和“为什么命中/未命中”。

### 3.2 P1：0.2 候选

- OpenAI Legacy `POST /v1/completions` 薄适配。
- `GET /v1/models/{id}` 与 Anthropic `POST /v1/messages/count_tokens`。
- Google Gemini `generateContent/streamGenerateContent` adapter。
- Provider 专属 raw JSON/SSE 回复逃生口。
- 规则 JSON 导入/导出。
- 图片/文件等输入 block 的可视化匹配，但不理解其内容。

### 3.3 明确延后

- OpenAI Realtime、Images、Audio、Files、Batch、内置服务端工具。
- Responses retrieve/delete/cancel/background/WebSocket。
- Anthropic Batch、Files、Skills、thinking、prompt caching、server tools。
- Bedrock、Vertex AI、Azure 等云厂商鉴权和路径变体。
- 任意插件代码执行。

## 4. 成功指标

### 用户体验

- 安装到首个 Mock 请求小于 5 分钟。
- 新建一条普通文本规则小于 60 秒。
- 保存后下一次请求立即生效，无需重启。
- 不看文档也能理解规则顺序、当前匹配来源和支持的 endpoint。
- Proxy 未配置时不占据首页空间；启用时才显示醒目的 LIVE 提示。

### 功能验收

- 官方 OpenAI 与 Anthropic Python SDK 只替换 `base_url` 和 dummy key 即可工作。
- 三个 P0 创建接口的 text/tool call 均支持 stream/non-stream。
- 同一条规则能生成三种 SDK 都可解析的协议回复。
- 两条无状态规则能完成“模型请求工具 → 应用回传工具结果 → 模型给最终回答”。
- 修改、排序、禁用规则后行为确定且可解释。
- 重启保留规则和设置，但清空最近请求。

### 初始性能目标

- 无人工延迟的普通 Mock 请求，服务端 p95 小于 20 ms。
- 至少 100 个并发普通请求和 50 个并发 SSE 连接，无规则串扰。
- 默认请求体上限 2 MiB。
- 常驻内存目标低于 150 MiB。
- 0.1 只支持单进程、单 Uvicorn worker。

这些是本地工具的验证目标，不是公开 SLA。

## 5. 总体架构

```text
OpenAI SDK                                      Anthropic SDK
    │                                                │
    ├─ /v1/chat/completions                          └─ /v1/messages
    └─ /v1/responses
                 │
                 ▼
          ProtocolAdapter.parse
                 │
                 ▼
           SemanticRequest
                 │
                 ▼
     ordered RuleMatcher + safe template
                 │
                 ▼
            SemanticReply
                 │
       ┌─────────┼───────────┐
       ▼         ▼           ▼
  Chat renderer  Responses   Anthropic renderer
    JSON/SSE     JSON/SSE       JSON/SSE

Browser ── management API ── SQLite ── atomic in-memory rule snapshot

Optional advanced fallback only:
unmatched request ── provider-specific raw proxy ── real upstream
```

核心边界：

- RuleMatcher 不知道 OpenAI/Anthropic 的具体 JSON envelope。
- Adapter 不负责业务规则，只解析和渲染协议。
- SemanticRequest/Reply 只表达三套协议真正共有的文本、工具和错误语义。
- 未知字段保留在 raw request 中；Mock 模式可忽略，Proxy 模式原样传递。
- Streaming 只共享 chunk 策略，不共享 SSE 事件格式。

## 6. 技术选型

| 层 | 选择 | 原因 |
|---|---|---|
| Python | 3.11+ | async、typing 与生态兼容性的稳妥基线 |
| ASGI | FastAPI + Starlette + Uvicorn | 路由、SSE、静态页面都在一个进程 |
| Schema | Pydantic v2 | 规则、设置和协议最小字段校验；请求 `extra="allow"` |
| Persistence | SQLite + aiosqlite | 本地单文件，无外部服务 |
| Upstream | HTTPX AsyncClient | 小型 Proxy 的异步逐块转发 |
| UI | 原生 HTML/CSS/JavaScript | 无 Node、React、Vite 和前端构建链 |
| Template | 受限 `${name}` 替换 | 不执行表达式、函数或代码 |
| CLI | 标准库 argparse 的薄入口 | 只有 serve/version 两个命令 |
| Source bootstrap | 标准库 `run.py` | clone 后自动管理 `.venv`，无需 pipx 或手动激活 |
| Native bundle | PyInstaller `onedir` | Release 用户无需安装 Python，按平台分别构建 |
| Container | Docker/Compose + GHCR | 可复现、持久化 volume、多架构镜像 |
| Project tests | pytest | 仅用于项目自身协议与回归验证 |

不引入 SQLAlchemy/Alembic、Postgres、Redis、Celery、消息队列或插件框架。

### 建议目录

```text
run.py
compose.yaml
Dockerfile
packaging/
  lmmock.spec
src/lmmock/
  __init__.py
  __main__.py
  cli.py
  config.py
  app.py
  admin.py
  storage.py
  diagnostics.py
  semantic.py
  protocols/
    base.py
    registry.py
    openai/
      chat.py
      responses.py
      models.py
    anthropic/
      messages.py
      models.py
  rules/
    models.py
    matcher.py
    template.py
  proxy/
    forwarder.py
    headers.py
  static/
    index.html
    app.js
    styles.css
tests/
  unit/
  protocol/
  integration/
  sdk/
docs/
  distribution-and-launch.md
```

## 7. Adapter 契约与语义模型

### 7.1 ProtocolAdapter

```python
class ProtocolAdapter(Protocol):
    operation_id: str
    capabilities: Capabilities

    def parse_request(self, body: bytes, headers: Headers) -> SemanticRequest: ...
    def render_response(self, reply: SemanticReply, request: SemanticRequest) -> Response: ...
    def render_stream(self, reply: SemanticReply, request: SemanticRequest) -> AsyncIterator[bytes]: ...
    def render_error(self, error: SemanticError, request_id: str) -> Response: ...
```

Capabilities 至少声明：`text`、`json_text`、`tools`、`multiple_tools`、`streaming`、`raw`。规则保存时校验所有选中 endpoint 都支持该 reply。

### 7.2 SemanticRequest

```text
provider               openai | anthropic
operation              openai.chat | openai.responses | anthropic.messages
model                  string
system_text            string
turns                  normalized text/tool blocks
last_user_text         string
all_text               string
declared_tools         list[name]
has_tool_result        bool
last_tool_result       string
stream                 bool
raw_body               original bytes + parsed JSON
```

映射规则：

| 语义 | OpenAI Chat | OpenAI Responses | Anthropic Messages |
|---|---|---|---|
| system | system/developer message | `instructions` 或输入消息 | 顶层 `system` |
| user text | user message | string input / input_text | user text block |
| tool declaration | nested function tool | flat function tool | `tools[].input_schema` |
| tool result | `role=tool` | `function_call_output` | user `tool_result` block |
| stream | `stream` | `stream` | `stream` |

### 7.3 SemanticReply

```text
kind                   text | json_text | tool_calls | error
text                   optional template result
tool_calls             list[{id, name, arguments object}]
finish_reason          stop | tool_call | length
usage                  optional semantic counts
error                  optional {status, type, code, message}
stream_policy          delay_ms, chunk_size, chunk_interval_ms
```

同一个 tool call 被渲染为：

| 协议 | 输出 |
|---|---|
| OpenAI Chat | `message.tool_calls[]`，arguments 为 JSON 字符串，`finish_reason=tool_calls` |
| OpenAI Responses | `output[]` 中独立 `function_call` item |
| Anthropic | `content[]` 中 `tool_use` block，input 为 JSON 对象，`stop_reason=tool_use` |

## 8. 规则系统

### 8.1 Rule

```text
id                     UUID
name                   string
enabled                bool
position               integer
endpoint_scopes        list[operation_id]
matcher                Matcher
reply                  SemanticReply template
created_at/updated_at  timestamp
```

### 8.2 Matcher

```text
model_glob             optional string
input_source           last_user_text | all_text | system_text | last_tool_result
input_operator         any | exact | contains | regex
input_value            optional string
case_sensitive         bool
required_tool_name     optional string
has_tool_result        any | true | false
```

所有条件使用 AND。规则按 `position ASC`，第一条完全命中者返回结果。不加入 priority、嵌套布尔 DSL、JSONPath、自定义 handler 或任意 header 条件。

### 8.3 安全模板

只允许：

- `${input}`
- `${model}`
- `${system}`
- `${last_tool_result}`
- `${request_id}`
- Regex 命名捕获，如 `${city}`

`$$` 表示字面 `$`。变量缺失时预览与保存报错。tool arguments 替换后必须重新解析为 JSON 对象。

### 8.4 Agent 无状态两轮规则

第一条规则：

```text
source = last_user_text
regex = weather in (?P<city>.+)
required_tool_name = get_weather
reply = tool call get_weather({"city": "${city}"})
```

第二条规则：

```text
source = last_tool_result
operator = any
has_tool_result = true
reply = "Tool returned: ${last_tool_result}"
```

客户端在下一轮带回 tool result，因此无需 Session、状态机或顺序计数器。

## 9. 协议实现要求

### 9.1 OpenAI Chat Completions

至少读取 `model/messages/stream/stream_options/tools/tool_choice/response_format`，其他合法字段宽松接受。

非流式必须生成 SDK 可解析的 `chat.completion`、message/tool_calls、finish_reason 和 usage。流式顺序：

1. assistant role delta。
2. text delta 或带稳定 index/id 的 tool argument delta。
3. finish chunk。
4. 请求 `include_usage` 时发送 usage chunk。
5. `data: [DONE]`。

### 9.2 OpenAI Responses

至少读取 `model/input/instructions/stream/tools/tool_choice/text.format`。`previous_response_id` 宽松接受但首版不恢复服务端历史。

文本的最小 typed SSE 生命周期：

```text
response.created
response.in_progress
response.output_item.added
response.content_part.added
response.output_text.delta × N
response.output_text.done
response.content_part.done
response.output_item.done
response.completed
```

工具调用使用 `response.function_call_arguments.delta/done`。所有事件复用相同 response/item id，并有递增 `sequence_number`。不得套用 Chat 的 chunk 或 `[DONE]`。

### 9.3 Anthropic Messages

至少强校验 `model/max_tokens/messages`，识别 `system/stream/tools/tool_choice/stop_sequences`；其他字段宽松接受。system 是顶层字段，不是 system role。

非流式文本返回：

- `type=message`、`role=assistant`。
- `content[]` text 或 tool_use block。
- `stop_reason=end_turn|tool_use|max_tokens|stop_sequence`。
- `usage.input_tokens/output_tokens`。

Anthropic SSE 不使用 `[DONE]`，固定骨架为：

```text
message_start
content_block_start
content_block_delta × N
content_block_stop
message_delta
message_stop
```

文本 delta 类型为 `text_delta`；工具参数为 `input_json_delta.partial_json`，拼接后必须是合法 JSON 对象。每个 frame 同时包含 `event:` 和 data 内相同的 `type`。`ping` 合法但首版不必发送。

### 9.4 Model list 路径冲突

OpenAI 与 Anthropic 都使用 `GET /v1/models`：

- 存在 `anthropic-version` header：返回 Anthropic 模型列表格式。
- 不存在：返回 OpenAI 模型列表格式。

官方 Anthropic SDK 会自动发送版本 header。虚拟模型由设置页配置；默认接受任意请求 model 并在响应中原样回显，不维护真实厂商型号全集。

### 9.5 Provider-shaped errors

OpenAI：

```json
{"error":{"message":"No mock rule matched.","type":"mock_not_found","param":null,"code":"mock_not_found"}}
```

Anthropic：

```json
{"type":"error","error":{"type":"not_found_error","message":"No mock rule matched."},"request_id":"req_mock"}
```

错误规则保存统一的 semantic error，再由 adapter 映射。P0 预设 400、401、404、429、500、503/529。响应分别带 OpenAI `x-request-id` 或 Anthropic `request-id`。

### 9.6 Usage

允许规则显式覆盖。未设置时采用稳定近似值，例如 `ceil(chars/4)`，并在文档中声明不是厂商 tokenizer 结果。各 renderer 使用自己的字段名，不能把 Chat 的 `prompt_tokens` 写进 Responses 或 Anthropic。

## 10. 持久化与运行时

SQLite 保持最小：

```sql
settings(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);

rules(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  enabled INTEGER NOT NULL,
  position INTEGER NOT NULL,
  endpoint_scopes_json TEXT NOT NULL,
  matcher_json TEXT NOT NULL,
  reply_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

provider_settings(
  provider TEXT PRIMARY KEY,
  mode TEXT NOT NULL,
  upstream_base_url TEXT,
  timeout_seconds INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
```

使用 Pydantic 校验 JSON，`PRAGMA user_version` 做顺序迁移，不引入 ORM。启动时加载不可变规则 tuple；管理 API 事务提交后原子替换快照，数据面不在每次请求查询 SQLite。

最近请求只存内存 `deque(maxlen=100)`：请求 ID、provider、operation、model、输入摘要、规则、mock/proxy 来源、状态和耗时。它不可导出、不落盘、重启清空，不属于录制功能。

## 11. Web UI

### 11.1 Home

- 主标题和“新建第一条规则”。
- OpenAI、Anthropic 两段最短接入代码。
- 三个 P0 endpoint 的可用状态。
- 规则数、最近命中和快速 Playground。
- Proxy 不占主视觉；只有启用时显示一条 LIVE 警告。

### 11.2 Rules

- 启停、新建、复制、删除、拖动排序。
- Scope badge：`OpenAI Chat`、`OpenAI Responses`、`Anthropic Messages`。
- 匹配摘要、回复类型、内存命中次数。

### 11.3 Rule editor

分三步：

1. 选择接口：所有对话接口、所有 OpenAI、仅 Anthropic，或逐项勾选。
2. 配置 model、输入来源、operator、tool 条件。
3. 配置 text/JSON/tools/error、模板和流式参数。

右侧预览使用三个 tab 展示各 endpoint 的最终 JSON 或 SSE；同时展示 SemanticRequest、命中条件实际值和捕获变量。保存前执行跨 endpoint capability 校验。

### 11.4 Playground 与最近请求

- 先选 provider，再选 endpoint。
- 使用最小表单构造文本、tools、stream 请求。
- 展示原始请求、语义请求、命中规则、语义回复和实际 wire response。
- 最近请求只供本次进程诊断，可手动清空。

### 11.5 Settings

- 虚拟模型列表、默认 fallback、chunk 默认值。
- 数据目录与配置覆盖来源只读展示。
- 页面底部折叠区 **Advanced: upstream fallback**，分别配置 OpenAI 与 Anthropic 的简单 Proxy。

不增加 Scenario、Recordings、Users、Audit、Metrics 等页面。

### 11.6 管理 API

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/__lmmock/api/info` | 版本、地址、能力、非 secret 状态 |
| `GET/POST` | `/__lmmock/api/rules` | 列表、新建 |
| `GET/PUT/DELETE` | `/__lmmock/api/rules/{id}` | 查看、替换、删除 |
| `POST` | `/__lmmock/api/rules/reorder` | 事务提交顺序 |
| `POST` | `/__lmmock/api/preview` | 解析、匹配和多协议预览，不访问上游 |
| `GET/PUT` | `/__lmmock/api/settings` | 非 secret 设置 |
| `GET/PUT` | `/__lmmock/api/providers/{provider}` | 高级 upstream fallback 设置 |
| `POST` | `/__lmmock/api/providers/{provider}/check` | 连通性检查，不返回 key |
| `GET/DELETE` | `/__lmmock/api/requests` | 查看或清空内存诊断 |

这是内置 UI 的内部 API，0.x 不承诺外部 SDK 稳定性。

## 12. Proxy 小功能

### 12.1 模式

每个 provider 独立设置：

| 模式 | 行为 |
|---|---|
| `mock-only` | 默认；只匹配 Mock，未命中走 provider-shaped fallback/error |
| `mock-then-proxy` | 规则命中就 Mock，未命中才转发 |
| `proxy-only` | 全部直接转发，主要用于临时对照 |

Proxy 不是 rule action，不做 OpenAI ↔ Anthropic 转换。

### 12.2 上游与 secret

- OpenAI：`LMMOCK_OPENAI_BASE_URL`、`LMMOCK_OPENAI_API_KEY`。
- Anthropic：`LMMOCK_ANTHROPIC_BASE_URL`、`LMMOCK_ANTHROPIC_API_KEY`。
- API key 只来自环境变量，不写 SQLite、不回显。
- 可显式启用 `no_auth` 连接本地兼容服务。

### 12.3 透明转发

- 固定 provider base URL 与已知 endpoint 拼接，客户端不能指定目标 URL。
- 保留 method、query、原始 body 和安全的端到端 headers。
- 删除 Host、Content-Length、hop-by-hop headers 和客户端凭据。
- OpenAI 注入服务器 Bearer token。
- Anthropic 注入服务器 `x-api-key`，保留 `anthropic-version`。
- 非流式返回上游 status/body；SSE 使用 `aiter_raw()` 逐块转发。
- 不自动重试、不记录、不比较、不转换、不生成规则。
- Redirect 默认关闭，客户端取消时关闭上游流。

## 13. CLI、配置与发行入口

```text
lmmock [--host] [--port] [--data-dir] [--no-open-browser]
lmmock serve [--host] [--port] [--data-dir] [--no-open-browser]
lmmock version
lmmock data-dir
```

无子命令的 `lmmock` 与 `lmmock serve` 等价，作为所有 Quick Start 的最短路径；`serve` 保留给脚本和显式配置。

配置优先级：

```text
CLI > LMMOCK_* 环境变量 > SQLite settings > 内置默认值
```

被 CLI/环境变量覆盖的设置在 UI 中标明来源并只读。启动日志只输出 UI 地址、OpenAI/Anthropic base URL、数据库路径、启用规则数和当前是否可能访问真实上游，不打印任何 key。

### 13.1 用户入口优先级

1. **GitHub Release 原生包**：下载、解压、运行，无 Python/Docker 前置要求。
2. **Docker**：一条 `docker run`；clone 后可用 `docker compose up`。
3. **源码**：macOS/Linux 执行 `python3 run.py`，Windows 执行 `py run.py`；脚本自动创建和同步 `.venv`。
4. **Python 工具**：`uvx lmmock`、`pipx run lmmock`、venv 中 `pip install lmmock`，作为可选入口。

所有入口最终执行同一个 `lmmock serve`，不能出现端口、数据目录或安全默认值分叉。详细发行方案见 [快速启动、发行与传播方案](distribution-and-launch.md)。

### 13.2 Release 资产

- PyInstaller `onedir` 压缩包：Linux x86_64、macOS arm64、Windows x86_64 为 0.1 最小矩阵。
- GHCR 镜像：`linux/amd64` 与 `linux/arm64`。
- PyPI wheel/sdist。
- 每个 tag 附 `SHA256SUMS`、build provenance、兼容矩阵和用户可读 Release Notes。
- README 中的每条公开启动命令必须在干净环境做 smoke test，不能只验证构建任务成功。

原生程序默认自动打开浏览器；容器只打印宿主访问地址。数据写入平台用户数据目录，Docker 写 `/data`，不写可执行文件所在目录。

## 14. 安全边界

- 默认监听 `127.0.0.1`。
- 非 loopback 必须显式 `--allow-remote`，并提示 0.1 不适合公网。
- 管理 API 默认同源、无开放 CORS。
- 数据面 CORS 只允许显式 origin，不把 credentials 与 `*` 混用。
- Body、regex、模板、延迟、chunk 和并发流都有上限。
- 不记录 Authorization、x-api-key、Cookie；输入摘要截断。
- Secret 只来自环境，不进入数据库、UI 响应、异常或日志。
- 模板没有代码、文件或网络执行能力。
- 上游 URL 只允许 http/https，redirect 默认关闭。
- 0.1 强制一个 worker，避免进程间规则快照不一致。
- 产品不宣称公网、多租户或强隔离安全性。

## 15. 项目自身验证

这些测试是维护 LMMock 的工程保障，不是面向用户的 CI 产品。

### 15.1 单元测试

- 三种请求到 SemanticRequest 的映射。
- Rule 顺序、glob、exact/contains/regex、capture、tool result。
- 模板白名单、缺失变量、JSON arguments 校验。
- Capability 跨 endpoint 保存校验。
- SQLite CRUD、重排、快照和迁移。

### 15.2 协议 golden tests

- OpenAI Chat 文本/多工具 JSON 与 SSE、usage 和 `[DONE]`。
- OpenAI Responses 文本/function call 的完整 typed event 顺序。
- Anthropic text/tool_use 的 Message 与 SSE 生命周期。
- 两种 provider 的错误 envelope 和 request ID header。
- `/v1/models` 根据 `anthropic-version` 正确分派。

### 15.3 官方 SDK 黑盒测试

OpenAI Python SDK：

- 同步与异步 Chat、Responses。
- stream/non-stream、文本、JSON、单/多工具、tool result。
- Model list 和 typed errors。

Anthropic Python SDK：

- `messages.create()` 文本与 tool_use。
- `stream=True` 原始事件。
- `messages.stream()` 的 `text_stream` 与 `get_final_message()`。
- 单/多工具、tool_result、typed errors、models.list。

测试只能更换 `base_url`，不能调用内部 renderer。

### 15.4 Agent 两轮测试

分别通过 Chat、Responses、Messages 跑：

1. 用户请求天气。
2. LMMock 返回 get_weather。
3. 测试应用执行工具并回传结果。
4. 第二条规则识别 tool result 并返回最终文本。

验证三条路径都无需 LMMock Session state。

### 15.5 Proxy 集成测试

只使用本地假上游，验证 path/body/headers、凭据替换、status、SSE 透传、取消和“零持久化副作用”。真实厂商 smoke test 仅人工执行。

### 15.6 UI smoke test

覆盖“新建跨协议规则 → 三个 tab 预览 → Playground 命中 → 编辑后立即变化”。其余视觉细节使用发布前手工检查表，不建立大型浏览器测试体系。

## 16. 0.1.0 发布验收

- [ ] `lmmock` 名称已完成复核并实际预留。
- [ ] Release、Docker、`python run.py` 和至少一种 Python tool 入口均在干净环境单命令启动。
- [ ] 默认纯 Mock、零外网访问。
- [ ] 三个 P0 创建接口 capability matrix 已发布。
- [ ] 一条 text 规则和一条 tool 规则可跨三个 endpoint。
- [ ] 三个 endpoint 的 stream/non-stream 均通过官方 SDK。
- [ ] 三条 Agent 工具两轮路径通过。
- [ ] UI 的规则 CRUD、排序、预览、Playground 和诊断可用。
- [ ] 重启保留规则/设置并清空请求诊断。
- [ ] OpenAI/Anthropic errors 和 model list 可被 SDK 解析。
- [ ] Proxy 不保存流量、不重试、不泄露客户端 key。
- [ ] Linux/macOS/Windows 最小原生包、wheel/sdist 和多架构 Docker 镜像在对应环境验证。
- [ ] Release 包含 SHA256、build provenance、平台/架构标识和已知限制。
- [ ] README 的每条公开启动命令均由发布 smoke test 实际执行。
- [ ] 首屏包含主 slogan、20 秒真实 SDK 演示、下载入口和三协议兼容信息。
- [ ] README 不声称“完整支持所有 LLM API”。

## 17. 里程碑与工期

按一名熟练 Python 全栈开发者估算：可演示 alpha 约 12–15 个工作日；加入三平台原生包、Docker 多架构、发行验证和传播物料后，达到公开 0.1.0 约 23–29 个工作日。代码签名证书审批时间不计入开发工期。

### M0：名称预留与骨架，2 天

- 复核并预留 LMMock 的包、仓库、镜像和域名。
- 初始化 Git、`pyproject.toml`、Apache-2.0、CLI、FastAPI、SQLite 和静态 UI。
- 固定三个 P0 endpoint 的 capability matrix 与官方文档 revision。

退出条件：包能安装启动，首页与 `/healthz` 可访问；名称风险已有明确决策且关键发行资产已经预留。

### M1：语义层与规则内核，3 天

- SemanticRequest/Reply、adapter registry、capabilities。
- Rule/Matcher/template/capture。
- SQLite CRUD、重排和原子快照。
- 无协议依赖的规则预览。

退出条件：语义测试覆盖文本、工具和 tool result，两条规则完成无状态两轮。

### M2：OpenAI Mock，4 天

- Chat JSON/SSE。
- Responses JSON/typed SSE。
- 文本、JSON、单/多工具、错误、usage。
- OpenAI 官方 SDK 黑盒测试。

退出条件：Chat 与 Responses 的 stream/non-stream 全部通过 SDK。

### M3：Anthropic Mock，3 天

- Messages 请求解析、text/tool_use JSON。
- Anthropic 完整 SSE 骨架。
- tool_result、错误、model list header 分派。
- Anthropic 官方 SDK 黑盒测试。

退出条件：Messages 的普通、stream、工具两轮与 typed errors 全部通过 SDK。

### M4：Mock-first Web UI，4–5 天

- Home、Rules、Rule editor、Playground、Settings。
- Scope 选择、capability 校验、三协议 wire preview。
- 最近请求与匹配解释。
- 可用性、空状态、键盘操作和错误反馈。

退出条件：用户不编辑文件即可完成跨协议文本和工具规则。

### M5：Proxy 小功能，1–2 天

- 两个 provider 的高级 upstream 设置。
- 三种 mode、secret/header policy、JSON/SSE 透传。
- 本地假上游测试与 LIVE 提示。

退出条件：Proxy 不影响纯 Mock 使用，未命中透传且无持久化副作用。

### M6：发行与发布硬化，6–10 天

- 完整 SDK 矩阵、边界、安全和性能基线。
- 标准库 `run.py`、wheel/sdist、Docker 多架构与三平台 PyInstaller 包。
- 各入口 smoke test、SHA256、attestation、平台签名/已知警告说明。
- Quickstart、20 秒演示、截图、规则示例、兼容矩阵和安全说明。
- 发布 0.1.0。

## 18. 开发 Backlog

### Epic A：Foundation

- CLI、配置、生命周期、健康检查、统一 request ID。
- SQLite schema/migration、body limit、单 worker 约束。

### Epic B：Semantic rule engine

- SemanticRequest/Reply、matcher、capture、template。
- Capability validation、预览和 match explanation。

### Epic C：OpenAI adapters

- Chat、Responses、OpenAI errors/models。

### Epic D：Anthropic adapters

- Messages、Anthropic errors/models。

### Epic E：Mock-first UI

- 页面、管理 API、Playground、诊断。

### Epic F：Optional upstream fallback

- 两个 provider 的 raw forwarder 与高级设置。

### Epic G：Release

- SDK matrix、`run.py`、原生包、容器、PyPI、发行验证、演示与文档。

每个 issue 必须落入一个 Epic，并描述可由用户或 SDK 验证的结果；不创建“未来也许有用”的平台抽象。

## 19. 主要风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| LMMock 名称尚未实际预留，且已有低可见度同名子项目 | 发布受阻、搜索混淆 | M0 第一件事做最终决策、基础商标搜索并预留关键资产 |
| 原生包扩大平台维护面 | 某个平台无法启动或出现系统安全警告 | 每个 OS 原生构建和 smoke test；签名条件不足时明确提示并提供 Docker/源码入口 |
| README 命令随 Release 失效 | 首次体验失败、传播流量浪费 | 发布流程实际执行每条公开命令并检查资产下载链接 |
| 三套协议快速演进 | SDK 解析失败 | Adapter 独立、官方 SDK black-box、公开 capability matrix |
| 过度统一 wire format | 流式或工具字段失真 | 只共享语义层，三套 renderer 独立 |
| Provider 数继续膨胀 | 偏离简单产品 | 0.1 只做 OpenAI/Anthropic；Gemini 必须用真实需求决定 |
| UI 变成通用 API 平台 | 工期和理解成本失控 | 固定 Mock-first 页面；Proxy 只在高级设置 |
| Agent 测试诱发状态机需求 | 复杂度上升 | 优先匹配客户端回传的 tool result；不保存会话状态 |
| Hybrid 意外产生费用 | 失去信任 | 默认 mock-only、key 只来自环境、LIVE 提示和切换确认 |
| Proxy 泄露 dummy key | 安全问题 | 总是剥离客户端 auth，集成测试验证 |
| SQLite 多 worker 不一致 | 行为不确定 | 0.1 强制单 worker |

## 20. 开源与发布

- 推荐 Apache-2.0；提供 LICENSE、CONTRIBUTING、CODE_OF_CONDUCT、SECURITY、CHANGELOG。
- 使用 SemVer；0.x 的管理 API 可演进，但 SQLite 数据必须自动迁移。
- 发布三平台最小原生包、PyPI wheel/sdist 和一个多架构 Docker 镜像；pipx 只作为可选入口。
- 使用 PyPI Trusted Publishing、签名 tag、SHA256、artifact attestation 和 GitHub Release；这些是维护流程，不是用户侧 CI 功能。
- README 首屏展示主 slogan、20 秒真实 SDK 演示、Release/Docker/source/Python 入口和 P0 能力；架构与贡献说明后置。
- Issue 模板收集 provider、endpoint、SDK 版本、stream、最小请求及脱敏响应。
- 新 provider 必须实现 adapter 契约、官方 SDK 测试和 capability 文档，不能向规则引擎加入厂商特殊分支。

## 21. 开始编码前的五个动作

1. 复核并预留 `LMMock/lmmock` 的公开资产。
2. 固定 OpenAI Chat、Responses、Anthropic Messages 的官方协议快照与 SDK 版本。
3. 固定四类发行入口及 smoke-test 矩阵，确认 macOS/Windows 签名资源。
4. 画出 Rule editor 与 20 秒演示的低保真脚本，确定个性文本、天气工具两条内置规则。
5. 按 M0 → M6 开始实现；Legacy Completions 与 Gemini 不进入 0.1 critical path。

完成以上动作后不需要继续扩架构预研，应该直接做最薄的纵向切片：一条规则同时跑通 OpenAI Chat、Responses 和 Anthropic Messages 的非流式文本，然后再补工具和流式。

## 22. 协议一手资料

- OpenAI 机器可读规范：[openai/openai-openapi](https://github.com/openai/openai-openapi)
- OpenAI Chat Completions：[Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- OpenAI Responses：[Create a response](https://developers.openai.com/api/reference/resources/responses/methods/create)
- OpenAI Responses 流事件：[Streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events)
- OpenAI Python SDK：[openai-python](https://github.com/openai/openai-python)
- Anthropic Messages：[Create a Message](https://platform.claude.com/docs/en/api/messages/create)
- Anthropic SSE：[Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming)
- Anthropic 工具调用：[Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- Anthropic 错误：[Claude API errors](https://platform.claude.com/docs/en/api/errors)
- Anthropic Models：[List Models](https://platform.claude.com/docs/en/api/models/list)
- Anthropic Python SDK：[anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)
