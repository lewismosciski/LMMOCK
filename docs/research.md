# LMMock：多协议 LLM Mock Server 市场与技术调研

调研日期：2026-09-20
项目状态：绿地项目，当前目录原本为空且尚未初始化 Git
产品边界：以网页规则驱动的 Mock 为核心，首版支持 OpenAI 与 Anthropic；真实 API 透传只是辅助功能；不规划录制回放或 CI 产品能力

## 1. 结论先行

这个方向可做，但赛道已经拥挤，不能把“能返回 OpenAI 格式 JSON”当作差异化。现有项目已经覆盖多厂商协议、SSE、故障模拟、录制回放甚至 Web 管理台。

最合理的切入点是刻意做窄：

> 一个 Python 原生、单命令启动、网页可编辑，且同一条规则能服务 OpenAI 与 Anthropic 接口的本地 Mock Server。

它不和大型工具比协议数量、吞吐、录制或测试编排，而是把核心流程压缩成：

```text
启动服务 → 浏览器新建规则 → 应用替换 base_url → 立即得到可控回复
```

值得保留的差异点只有四个：

- Python 项目可直接安装和二次开发。
- 无前端构建链，单进程内置轻量 Web UI。
- 同一条语义规则可渲染为 OpenAI Chat、OpenAI Responses 或 Anthropic Messages 格式。
- Mock 是首页、规则系统和路线图的中心；真实 API 接入只藏在高级设置中，不演化成复杂网关。

## 2. 用户问题与最小需求

目标用户是开发 AI 应用或 Agent 的个人与小团队。他们需要：

- 不消耗真实 token 就能调通完整 HTTP/SDK 调用链。
- 根据输入内容稳定返回指定文本、JSON 或工具调用。
- 测试 OpenAI Chat/Responses 与 Anthropic Messages 客户端代码。
- 不改配置文件也能在浏览器里快速改回复。
- 临时切到真实 API，或只把未匹配请求交给真实 API。

他们不一定需要：录制真实流量、Cassette 管理、复杂对话状态机、断流混沌、断言 SDK、GitHub Action、团队权限和生产级网关能力。这些功能会显著提高学习和维护成本，也偏离本项目“简单易用”的约束。

## 3. OpenAI 与 Anthropic 协议基线

OpenAI 官方 API Reference 提供端点与对象 schema，官方 GitHub 也提供机器可读规范入口；实现时应固定一份协议快照并用官方 SDK 做黑盒验证，而不是靠博客或手写示例猜字段。[OpenAI API Reference](https://developers.openai.com/api/reference/overview)、[OpenAI OpenAPI repository](https://github.com/openai/openai-openapi)

Anthropic 的 Messages API 同样有独立的 JSON 结构、`tool_use/tool_result` block 和 SSE 事件生命周期，不能通过“把字段名改一下”复用 OpenAI 的 wire format。[Anthropic Create a Message](https://platform.claude.com/docs/en/api/messages/create)、[Anthropic Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming)

### 首版应覆盖的接口

| 接口 | 首版能力 | 取舍 |
|---|---|---|
| `POST /v1/chat/completions` | 文本、JSON 文本、tool calls、非流式与 SSE | 仍被大量现有应用使用；请求字段宽松读取 |
| `POST /v1/responses` | output text、function call、非流式与类型化 SSE | OpenAI 推荐的新接口；必须使用独立事件格式 |
| `POST /v1/messages` | Anthropic text、tool_use、非流式与原生 SSE | P0；使用 `message_start/content_block_*/message_stop` 生命周期 |
| `POST /v1/completions` | 单 prompt 文本、非流式与 SSE | P1 薄兼容层，不阻塞三种核心对话接口 |
| `GET /v1/models` | 按 `anthropic-version` 请求头区分厂商后返回配置模型 | P0 轻量兼容；不维护真实厂商型号全集 |
| `GET /healthz` | 进程健康信息 | 项目自有接口，仅供本地检查 |

[Chat Completions 参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)和 [Responses 参考](https://developers.openai.com/api/reference/resources/responses/methods/create)显示两者是独立接口，因此都应保留。[Responses streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses)则表明 Responses 使用 `response.created`、内容 delta、`response.completed` 等类型化事件，不能直接复用 Chat 的 `chat.completion.chunk` 和 `[DONE]` 逻辑。Anthropic 流又是第三种格式，因此三套 renderer 必须独立实现。

### 首版明确不承诺

- Responses retrieve/delete/cancel/background、Conversation 和 WebSocket。
- OpenAI Realtime、Images、Audio、Embeddings、Moderations、Files、Batch。
- Anthropic Batches、Files、Skills、Managed Agents 和云厂商托管变体。
- OpenAI 内置工具的真实执行，如 web search、file search、computer use。
- 完整多模态生成；图片等输入只在透传模式原样交给上游。
- 每个模型的精确 token 计算和全部模型特有参数。
- “完整兼容 OpenAI API”这种无法验证的笼统承诺。

实现策略应是：Mock 模式识别首版所需字段并宽松接受未知字段；Proxy 模式尽量保留原始请求和响应。项目发布一张逐端点、逐能力的 capability matrix。

## 4. 竞品扫描

### 直接或高度相关项目

| 项目 | 已有优势 | 对本项目的启示 |
|---|---|---|
| [zerob13/mock-openai-api](https://github.com/zerob13/mock-openai-api) | Chat、Responses、Anthropic、Web 管理台、场景编辑、API 测试和录制回放 | 与原始设想重合度最高；不能只靠“有 UI”区分，应更轻、更聚焦 Python 和规则编辑 |
| [CopilotKit/aimock](https://github.com/CopilotKit/aimock) | 多厂商、多协议、MCP/A2A/AG-UI、录制回放、混沌、GitHub Action 等完整测试设施 | 协议广度竞争不可取；其复杂度反而验证了极简产品的空间 |
| [VidaiMock](https://github.com/vidaiUK/VidaiMock) | Rust 单文件、高性能、多厂商、流式时序和故障模拟 | 不应把性能和“真实网络物理”当作首版目标 |
| [larsakerlund/llmock](https://github.com/larsakerlund/llmock) | OpenAI/Anthropic/Gemini、规则、故障与录制回放，强调 wire format | 再次证明 `llmock` 名称和宽功能定位都已拥挤 |
| [JulienRabault/LLMock](https://github.com/JulienRabault/LLMock) | Python/FastAPI、多个模型厂商、错误注入，并已发布同名 PyPI 包 | Python 本身不是充分差异点；公开包名也已冲突 |
| [theblixguy/llm-mock-server](https://github.com/theblixguy/llm-mock-server) | Chat、Responses、Anthropic、规则、流式、工具调用和请求历史 | 轻量规则引擎已有先例，Web 编辑体验必须真正降低使用门槛 |
| [Mockoon](https://mockoon.com/) | 成熟的本地 API 编辑器、动态模板、规则和 proxy mode | UX 是重要参考，但通用 HTTP Mock 不原生理解两套 OpenAI 流和工具调用语义 |
| [MockServer](https://github.com/mock-server/mockserver-monorepo) | 成熟通用 Mock/Proxy，并已增加 LLM 流量展示能力 | 大而全的通用平台不是本项目目标；首版不做团队部署或多协议基础设施 |

### 相邻但不是直接替代

- [LiteLLM](https://github.com/BerriAI/litellm) 的核心定位是多模型 Gateway、路由和治理，而不是让用户在网页上编排固定 Mock 回复。
- [promptfoo](https://github.com/promptfoo/promptfoo) 侧重评测、对比和红队，不是一个轻量的 OpenAI 兼容回复编辑器。
- [openai-responses-python](https://github.com/mharrisb1/openai-responses-python) 侧重进程内/pytest Mock，不能完全替代独立 HTTP Server 的端到端调用路径。

## 5. 命名决策

`LLMock` 不适合作为最终公开名称：

- GitHub 已存在多个同名或近同名项目，包括上表两个活跃实现。
- PyPI 的 [`llmock`](https://pypi.org/project/llmock/) 已被发布使用。
- CopilotKit 也曾使用 `@copilotkit/llmock`，之后迁移到 aimock，但生态里仍保留该名称痕迹。

新的主推荐名称是 **LMMock**，副标题为 **Visual mock server for LLM APIs**。

选择理由：

- `LM + Mock` 直接标明品类，第一次看到名称就能判断它与语言模型 Mock 有关。
- 只有 6 个字符、无连字符，品牌、PyPI 包、Python import 和 CLI 可以统一为 `LMMock/lmmock`。
- 相比字面更自然的 `MockLLM`、`AIMock`、`MockAI` 和 `LLMock`，关键发行资产暂未占用且搜索噪声更低；但后续检索发现一个低可见度的同名 Rust 子项目，因此不能称为零冲突。
- 不使用 OpenAI、GPT、Claude 或 Anthropic 商标，未来增加 Gemini 等 adapter 不需要改名。
- 英文标语可以直接写成 “Mock LLM APIs locally.”。

主要候选排雷：

| 名称 | 结论 |
|---|---|
| `MockLLM` | [PyPI](https://pypi.org/project/mockllm/) 和多个同类项目已使用，且已有 [`mockllm.io`](https://mockllm.io/) 商业服务 |
| `AIMock` | [CopilotKit](https://github.com/CopilotKit/aimock) 已使用 `aimock` 包、项目和 CLI，直接同类冲突 |
| `MockAI` | [PyPI](https://pypi.org/project/mockai/) 与 [GitHub](https://github.com/polly3d/mockai) 已有同名项目 |
| `LLMock` | [PyPI](https://pypi.org/project/llmock/) 已占用，CopilotKit 仍保留 `llmock` CLI 兼容别名 |
| `MockLM` | PyPI 暂未占用，但 [GitHub 已有同类项目](https://github.com/JSLEEKR/mocklm)，而且常被用作代码内部类名 |
| `LLMMock` | 含义最准，但双 `M` 容易漏写，并会被误输成已占用的 `llmock` |

截至 2026-09-20 的初步可用性检查：

| 检查项 | `lmmock` 结果 |
|---|---|
| PyPI JSON API | 404，未发现现有项目 |
| npm Registry | 404，未发现现有包 |
| GitHub 独立 repository name 搜索 | 未发现精确命名结果 |
| GitHub organization | 404，未发现同名组织 |
| GitHub 子项目检索 | [`frankfliu/junkyard/lmmock`](https://github.com/frankfliu/junkyard/tree/master/lmmock) 为同类 OpenAI Mock Server |
| `lmmock.dev` RDAP | 404，未发现注册记录 |
| `lmmock.ai` RDAP | 404，未发现注册记录 |
| `lmmock.com` RDAP | 404，未发现注册记录 |

核验入口：[PyPI JSON](https://pypi.org/pypi/lmmock/json)、[npm Registry](https://registry.npmjs.org/lmmock)、[GitHub repositories](https://github.com/search?q=LMMock&type=repositories)、[GitHub organization](https://github.com/lmmock)、[`.com` RDAP](https://rdap.verisign.com/com/v1/domain/lmmock.com)、[`.dev` RDAP](https://pubapi.registry.google/rdap/domain/lmmock.dev)、[`.ai` RDAP](https://rdap.identitydigital.services/rdap/domain/lmmock.ai)。

这只是技术查重快照，不是商标法律意见，也不代表名称已经被预留。LMMock 的独立仓库、PyPI 与常见域名仍有机会取得，但同类子项目意味着它并非完全独占。M0 必须先完成最终名称决策、基础商标搜索并尽快注册仓库、包名和域名。备选名为 `LLMocker` 和 `LLMMock`：前者更独特但容易被拼成 `llmmocker`，后者字面最准但双 `M` 容易漏写。

## 6. 建议定位

### 一句话定位

> 在浏览器中写一条规则，让 OpenAI 和 Anthropic SDK 得到你指定的回复。

### 产品原则

1. **五分钟可用**：安装、启动、打开页面、创建首条规则不超过五分钟。
2. **页面优先**：普通用户不需要先学习 YAML DSL 或写 Python handler。
3. **行为可解释**：严格按页面顺序首条命中，页面能说明命中了哪条规则。
4. **Mock 优先**：首页、规则编辑和文档都围绕 Mock；Proxy 只作为高级兜底。
5. **安全默认**：默认 Mock、默认只监听本机、真实 API key 只从环境变量读取。
6. **兼容面诚实**：只宣称经过官方 SDK 验证的字段和事件。
7. **范围克制**：新功能必须直接改善“配置回复并让 SDK 调用”这一主流程。

### 非目标

- 成为生产 LLM Gateway、负载均衡器或成本平台。
- 模拟模型智能或根据任意 prompt 自动生成高质量答案。
- 一开始覆盖所有厂商；首版只做 OpenAI 与 Anthropic，后续按真实需求增加 adapter。
- 成为录制回放、评测、测试编排或可观测性平台。
- 支持公网多租户部署。

## 7. 机会与风险判断

### 机会

- OpenAI Chat、OpenAI Responses 与 Anthropic Messages 的流式格式互不相同，通用 HTTP Mock 配置成本高。
- 很多专项工具偏 CLI、代码或配置文件，轻量可视化规则编辑仍有体验空间。
- Python 单进程和无前端构建链适合 Python AI 应用开发者理解、安装和贡献。
- “命中规则，否则转发”能覆盖本地开发的大部分实际需要，而无需演化为网关。

### 风险

- 直接竞品已经存在，项目的成功更依赖交互细节、文档和稳定性，而非功能清单。
- OpenAI Responses 事件继续演进，需要明确兼容版本并维护 capability matrix。
- 所谓 OpenAI-compatible 服务之间仍可能存在字段差异；Proxy 只能承诺透明转发，不能承诺所有上游都兼容。
- Web UI 很容易膨胀成通用 API 平台，应以四个页面和固定规则字段控制范围。

## 8. 调研后的最终取舍

采用：

- OpenAI Chat Completions、OpenAI Responses、Anthropic Messages，以及轻量 Models list；Legacy Completions 降为次要兼容项。
- 文本、JSON 文本、工具调用、固定 HTTP 错误和固定延迟。
- exact/contains/regex、model glob、tool presence 等少量 matcher。
- 网页 CRUD、排序、预览和内存中的最近请求诊断。
- OpenAI/Anthropic 各自可选的简单 passthrough；入口放在高级设置，不出现在核心 Mock 流程。

不采用：

- 录制、回放、Cassette、fixture 学习模式。
- CI/pytest 插件、断言 API、GitHub Action。
- 场景图、会话状态机、概率混沌和中途断流。
- 多上游路由、预算、重试、熔断、鉴权管理。
- React/Vite、Postgres、Redis、消息队列和插件系统。

详细实现边界、接口语义和里程碑见[完整开发规划](development-plan.md)。
