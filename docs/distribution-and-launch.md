# LMMock 快速启动、发行与开源传播方案

版本：Draft 1
日期：2026-09-20
范围：只讨论如何让用户更快运行 LMMock，以及如何清晰传播 Mock-first 产品；不扩展录制回放、CI 平台等产品能力

## 1. 结论

`pipx` 不应是首屏主安装方式。LMMock 应提供四条互不依赖的入口，README 按下面的顺序展示：

| 优先级 | 用户入口 | 最短体验 | 适合人群 |
|---:|---|---|---|
| 1 | GitHub Release 原生包 | 下载、解压、运行 `lmmock` | 不想安装 Python 或 Docker 的大多数试用者 |
| 2 | Docker 镜像 | 一条 `docker run`，或 clone 后 `docker compose up` | 已有 Docker、重视隔离和可复现性的人 |
| 3 | Git clone 源码启动 | `python run.py` | Python 开发者、贡献者、需要看源码的人 |
| 4 | Python 工具入口 | `uvx lmmock`、`pipx run lmmock`、venv 中 `pip install lmmock` | 已经使用 Python 工具链的人 |

产品级目标：

- 没有 Python 的用户，下载 Release 后 30 秒内看到页面。
- 有 Python 的用户，clone 后只输入一条启动命令，不手动创建或激活虚拟环境。
- 有 Docker 的用户，一条命令启动且规则数据不会随容器删除。
- 所有入口启动同一个 CLI、同一套默认值和同一份 Web UI。
- 默认只监听 loopback、只做 Mock，不要求 API key，也不访问真实厂商。

这不是四套产品。它们只是同一个 `lmmock serve` 的四种交付外壳。

实现顺序与 README 展示顺序可以不同：开发期先跑通 wheel/`uvx`、Docker 和源码，再稳定 PyInstaller 产物；面向公众的 0.1 发布完成三平台原生包后，才把 Download 放到首位。若签名或某个平台包尚不可靠，就诚实标为 preview，并让该平台优先看到 Docker/`uvx`，不能为了排版宣称一个并不稳定的首选入口。

## 2. 为什么要提供多入口

成熟本地开发工具通常不会强迫所有用户先接受自身语言生态：

- [mitmproxy](https://docs.mitmproxy.org/stable/overview/installation/) 在 Linux 首推自包含二进制，也提供 Windows 安装包、Homebrew、PyPI 和 Docker；其文档明确说明二进制与镜像已经包含 Python 和依赖。
- [Mockoon](https://mockoon.com/download/) 为桌面用户提供各平台安装包及 winget/choco/Homebrew 等入口，同时另有 CLI 与 Docker。
- [WireMock](https://wiremock.org/docs/standalone/) 同时提供 standalone JAR 与 Docker；[Docker 快速启动](https://wiremock.org/docs/standalone/docker/)只要求一次 `docker run`。
- 同赛道的 [mock-openai-api](https://github.com/zerob13/mock-openai-api) 把 Docker 放在 Quick Start 第一位，再提供 Compose 和 npm。
- [uv](https://docs.astral.sh/uv/concepts/tools/) 的 `uvx` 很适合临时运行 Python CLI，但它仍要求用户先拥有 uv，因此应该是便利入口而不是唯一入口。

可借鉴的共同点不是“大家都用 Docker”，而是：**面向最终用户提供自包含产物，面向已有工具链的用户提供原生命令，面向贡献者保留源码路径。**

## 3. 推荐的启动体验

以下命令是发行设计，当前仓库尚未实现，不能在 README 中伪装成已经可用。

### 3.1 GitHub Release：默认推荐

Release 页面按平台提供压缩包：

```text
lmmock-v0.1.0-linux-x86_64.tar.gz
lmmock-v0.1.0-linux-aarch64.tar.gz
lmmock-v0.1.0-macos-x86_64.zip
lmmock-v0.1.0-macos-arm64.zip
lmmock-v0.1.0-windows-x86_64.zip
SHA256SUMS
SBOM.spdx.json
```

解压后：

```bash
./lmmock
```

Windows：

```powershell
.\lmmock.exe
```

默认行为：

1. 监听 `127.0.0.1:8000`。
2. 初始化平台数据目录中的 SQLite 文件。
3. 打印 OpenAI、Anthropic 和管理页面地址。
4. 自动打开 `http://127.0.0.1:8000`；无桌面环境时只打印地址。
5. Ctrl+C 优雅退出。

自动打开必须等 `/healthz` 已可访问；Docker、无 TTY 或无图形桌面环境不尝试控制浏览器，打开失败也不能让服务退出。

原生包应作为首选，因为它没有 Python、pip、pipx、uv 或 Docker 前置要求。[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)本身支持在 tag 上附加二进制文件、Release Notes 和下载统计。

### 3.2 Docker：最稳定的隔离入口

直接运行：

```bash
docker run --rm \
  -p 127.0.0.1:8000:8000 \
  -v lmmock-data:/data \
  ghcr.io/OWNER/lmmock:0.1.0
```

clone 后运行：

```bash
docker compose up
```

`compose.yaml` 应默认：

- 使用已发布的版本化镜像，而不是在用户机器上重新构建。
- 将容器的 `/data` 映射到 named volume。
- 容器内监听 `0.0.0.0`，但宿主端口只绑定 `127.0.0.1`。
- 提供 `/healthz` healthcheck。
- 使用非 root 用户。
- 不传任何真实 API key。

文档需明确：`docker compose down` 保留 named volume，而 `docker compose down -v` 会删除规则数据。

Docker Compose 官方定义的 `docker compose up` 会创建并启动服务，并在配置变化后重建容器而保留 volume，适合 clone 后的一条命令体验。[Docker Compose `up`](https://docs.docker.com/reference/cli/docker/compose/up/)

不要把 Docker 作为唯一入口：第一次试用一个本地 Mock Server，不应强迫没有 Docker 的用户安装 Docker Desktop。

### 3.3 Git clone：只依赖 Python

macOS / Linux：

```bash
git clone https://github.com/OWNER/lmmock.git
cd lmmock
python3 run.py
```

Windows：

```powershell
git clone https://github.com/OWNER/lmmock.git
cd lmmock
py run.py
```

仓库根目录的 `run.py` 只使用 Python 标准库，负责：

1. 检查 Python 3.11+。
2. 在仓库内创建 `.venv`，不污染系统环境。
3. 以锁定依赖安装当前源码；仅在首次运行或 lock hash 改变时同步。
4. 使用虚拟环境解释器执行 `python -m lmmock`。
5. 原样透传 `--port`、`--data-dir`、`--no-open-browser` 等参数。
6. 安装或启动失败时给出可复制的诊断命令，而不是吞掉 pip 输出。

例如：

```bash
python3 run.py --port 9000 --no-open-browser
```

`run.py` 比 `run.sh + run.ps1 + run.cmd` 更容易保持三平台行为一致。它不能解决“用户没有 Python”的情况，因此 Release 仍排第一。

这是一条命令，不是零依赖或离线安装：用户仍需 Python，首次运行仍需从包索引下载依赖。脚本必须在执行前说明只会创建仓库内的 `.venv`，不得修改全局 Python；若系统缺少 `venv/ensurepip`，应给出明确诊断。

对已经安装 uv 的贡献者，额外提供：

```bash
uv run --frozen lmmock
```

uv 会在项目中创建/更新隔离环境并按照 lockfile 运行命令，无需手动激活虚拟环境。[uv project run](https://docs.astral.sh/uv/concepts/projects/run/)

### 3.4 Python 工具入口：保留但降级

无需永久安装：

```bash
uvx lmmock
pipx run lmmock
```

安装到独立工具环境：

```bash
uv tool install lmmock
pipx install lmmock
```

普通 venv：

```bash
python -m pip install lmmock
lmmock
```

README 首屏只展示 `uvx lmmock` 作为折叠的 Python 入口，不把安装 pipx/uv 本身写成主 Quick Start。

## 4. 原生 Release 的实现选择

### 4.1 推荐 PyInstaller `onedir`

首版推荐用 PyInstaller 将 Python 解释器、依赖和静态页面打进平台包。PyInstaller 产物不要求目标机器安装 Python，但它不是通用交叉编译器，Windows、macOS 和 Linux 应分别在对应 runner 上构建。[PyInstaller manual](https://pyinstaller.org/en/latest/)

首版选择 `onedir` 后压缩，而不是强求单文件：

- 启动时不需要每次解压全部运行时。
- 静态 HTML/CSS/JS 和 Pydantic 等依赖更容易诊断。
- Windows 杀毒软件误报和临时目录限制通常更少。
- 用户看到的仍然是一个下载包，解压后只需运行顶层可执行文件。

`onefile` 可以在后续作为额外资产试验，但不能为了“一只 exe”牺牲启动速度和可信度。mitmproxy 也提示其会解压的 standalone binary 启动明显更慢。[mitmproxy installation](https://docs.mitmproxy.org/stable/overview/installation/)

PEX、Shiv 和普通 zipapp 仍依赖兼容 Python 解释器，不满足“下载即运行”；Nuitka 可行但构建调试成本更高，首版没有必要。

### 4.2 构建矩阵

| OS | 架构 | 构建方式 | 发布要求 |
|---|---|---|---|
| Linux | x86_64 | 较老的 glibc runner/container | 在当前 Ubuntu LTS 与上一个 LTS 验证 |
| Linux | arm64 | 原生 arm64 runner 或受控构建器 | 至少在 arm64 Linux/Docker 验证 |
| macOS | x86_64 | Intel macOS runner | 签名，条件允许时 notarize |
| macOS | arm64 | Apple Silicon runner | 签名，条件允许时 notarize |
| Windows | x86_64 | Windows runner | ZIP、SHA256，条件允许时代码签名 |

PyInstaller 在 Linux 不打包系统 `libc`，所以 Linux 产物必须在足够老的构建基线上产生并做真实系统验证。[PyInstaller usage](https://pyinstaller.org/en/latest/usage.html)

暂不承诺 Windows arm64。每增加一个平台，就必须有一个启动、页面、SQLite 写入和 SDK 请求的 smoke test。

### 4.3 资源与数据

- Web 静态资源通过 `importlib.resources` 读取，不能依赖当前工作目录。
- 可执行文件目录视为只读，SQLite 永远写入用户数据目录或显式 `--data-dir`。
- 平台默认数据目录：Linux 遵循 XDG、macOS 使用 Application Support、Windows 使用 LocalAppData。
- Docker 固定使用 `/data`。
- 所有入口都支持 `LMMOCK_DATA_DIR` 覆盖。

### 4.4 供应链与平台信任

每次正式 Release 应包含：

- 版本化资产，不只提供会漂移的 `latest`。
- `SHA256SUMS`。
- SPDX 或 CycloneDX SBOM。
- 来自 tag 的 Release Notes 与兼容矩阵。
- GitHub build provenance attestation；官方文档支持为二进制和容器生成并验证 attestation。[GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- GHCR 镜像 digest 和 `linux/amd64,linux/arm64` manifest。

macOS notarization和 Windows 签名直接影响首次启动信任。如果 0.1 尚未完成签名，应在下载页明确提示，不能把绕过 Gatekeeper/SmartScreen 的复杂命令藏起来；此时 Docker 与源码入口应在对应平台紧随 Release 展示。

macOS 成品使用 ZIP、DMG 或 PKG 提交公证并发布，不使用 `tar.gz` 作为公证载体；构建完成并签名后不能再修改 bundle 内容。[Apple notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow)

## 5. README 的正确首屏

首屏在用户第一次滚动前只回答五个问题：

1. 这是什么？
2. 为什么需要它？
3. 它真的能工作吗？
4. 如何立刻运行？
5. 支持哪些 API？

推荐结构：

```text
[Logo] LMMock
Mock the model. Run the real app.
No real API keys. No model calls. No token spend.

[18–25 秒演示 GIF / WebP]

[Download for macOS] [Download for Windows] [Linux] [Docker]

docker run ...

✓ OpenAI Chat Completions  ✓ OpenAI Responses  ✓ Anthropic Messages
```

其后立刻展示“替换一个 `base_url`”的 OpenAI 与 Anthropic 最短代码，再讲规则编辑、工具调用和架构。不要先展示十几个 badge、长篇愿景或贡献指南。

GitHub 也建议 README 明确项目用途、价值、启动方式和求助入口；README 往往是访客看到的第一项内容。[GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)

## 6. 宣传语与信息层级

### 主 slogan

> **Mock the model. Run the real app.**

中文表达：

> **Mock 掉模型，跑通真实应用。**

它同时表达两层价值：被替换的只有模型/API，用户运行的仍是自己的真实应用或 Agent 调用链。

### 成本与隐私副句

> **No real API keys. No model calls. No token spend.**

中文：

> **无需真实密钥，不调真模型，不烧 Token。**

这里必须使用 `no token spend`，而不是 `no tokens`：

- LMMock 仍会返回可配置或估算的 usage/token 字段，保证 SDK 与应用流程正常。
- “token”也可能被理解为认证 token。
- 部分官方 SDK 仍要求传入非空占位值，例如 `api_key="mock"`；`no real API keys` 指不需要任何真实厂商 secret。
- 开启高级 Proxy 后可能产生真实上游费用，因此宣传页应注明这句话描述默认 `mock-only` 模式。

### 产品描述

> **A visual local mock server for OpenAI, Anthropic, and AI agent workflows.**

中文：

> **一个为 OpenAI、Anthropic 和 AI Agent 调用链设计的可视化本地 Mock Server。**

### 可轮换的短句

- `One rule. Every supported LLM API.` —— 突出跨协议语义规则。
- `Predictable replies for unpredictable AI apps.` —— 突出确定性。
- `Your agent runs. Your token bill doesn't.` —— 适合社交媒体，但正文需解释是 Mock 模式。
- `Make every model reply exactly as your test needs.` —— 突出可控回复。
- `Open the UI. Write a rule. Point your SDK.` —— 突出简单上手。
- `Mock once. Reply across APIs.` —— 突出 OpenAI/Anthropic adapter。

不建议使用：

- `The complete LLM mock platform`：与“简单 Mock Server”定位冲突。
- `100% OpenAI/Anthropic compatible`：协议持续变化，无法严格证明。
- `Run AI without tokens`：容易被理解为真的本地推理或完全不涉及 token。
- `Free AI API`：会吸引错误受众，也可能被误认为提供真实模型能力。

## 7. 20 秒演示脚本

传播物料只展示一个完整闭环，不做功能巡游：

| 时间 | 画面 | 字幕 |
|---:|---|---|
| 0–3 秒 | 一个 Agent 因缺少 API key/上游 429 而失败 | `Your app depends on an unpredictable model.` |
| 3–6 秒 | 双击 `lmmock`，浏览器自动打开 | `Start locally. No real API key.` |
| 6–11 秒 | 在页面输入 `weather in (.+)`，选择 `tool_call: get_weather` | `Write one rule.` |
| 11–16 秒 | Agent 再次运行，完成工具调用并得到最终回复 | `Run the real agent flow.` |
| 16–20 秒 | 三个 tab 展示 Chat、Responses、Anthropic wire preview | `One rule. OpenAI + Anthropic.` |

演示必须使用真实 SDK 示例进程，不只在内置 Playground 自说自话。GIF/WebP 下方放可复制命令和对应 `examples/weather_agent/`，让观看者能复现。

## 8. 让项目更容易获得传播

无法保证“火爆”，但可以系统性提高被采用和二次传播的概率。

### 8.1 发布前门槛

在公开引流前必须满足：

- 三个平台至少一种入口真的可以在全新环境启动。
- OpenAI Responses、Chat Completions、Anthropic Messages 均有一个真实 SDK demo。
- 首次启动不需要配置文件、账号或 API key。
- 默认自带两条示例规则，空页面不是用户第一印象。
- 一个 20 秒演示和一个 60 秒可复制 Quick Start。
- README 明确“不做录制回放/CI 平台”，避免吸引错误预期。
- 问题模板能收集 OS、启动方式、SDK、endpoint 和最小复现。

### 8.2 首轮只攻高意图人群

不要同一天把同一段广告复制到几十个社区。优先找正在遭受真实 API 成本、限流和非确定性问题的人：

1. OpenAI/Anthropic SDK 与 Agent 框架开发者社区。
2. `r/LocalLLaMA`、`r/LLMDevs`、相关 Python 社区，遵守各自 self-promotion 规则。
3. Show HN：标题直接描述成果，例如 `Show HN: LMMock – run OpenAI and Anthropic agent flows without model calls`。
4. 中文社区使用中文案例：V2EX、掘金、知乎，以及 Python/Agent 微信群或论坛。
5. Product Hunt 放在已有真实用户、稳定 Release 与高质量演示之后，而不是把空仓库当首发。

一份对开源项目增长案例的复盘显示，小而精准的垂直社区、根据反馈持续交付、再集中做大版本发布，比只追求一次泛流量曝光更可持续；这是案例经验而不是成功保证。[Open-source launch case study](https://github.com/About-Intelligence/OpenCMO/blob/main/references/topics/launch-playbook.md)

### 8.3 每个平台讲不同的真实故事

- Hacker News：协议实现、跨 provider adapter 和为何不做状态机。
- Reddit：真实痛点、20 秒 GIF、开源地址，并主动问“还缺哪个 SDK 行为”。
- X / LinkedIn：一句 slogan + GIF + 一条可复制命令。
- 中文长文：从一次 Agent 调试为什么烧 token/触发限流讲起，再展示无 key 复现。
- 框架社区：提交一个最小 `examples/<framework>`，不空投营销链接。

### 8.4 形成可持续反馈循环

```text
真实用户问题
  → 最小协议修复或示例
  → 发布小版本
  → 用“用户提出的问题已经可运行”写更新
  → 原社区回访
  → 新用户与新问题
```

首发后的两周比首发当天更重要：快速响应前 20 个有效 issue、每周发布一次兼容修复、公开 capability matrix，并把真实反馈变成短演示。

### 8.5 GitHub 可发现性基础

- 上传 1280×640 的 social preview，内容只放 Logo、主 slogan 和三协议标识。GitHub 官方支持自定义链接展开图，并推荐 1280×640。[Social preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
- topics 使用 `llm`、`mock-server`、`openai`、`anthropic`、`ai-agents`、`fastapi`、`testing`、`python`；topics 会进入对应发现页面。[GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)
- 在首发前补齐 README、LICENSE、CONTRIBUTING、CODE_OF_CONDUCT、SECURITY 与 issue forms；这些也是 GitHub community profile 的公开信任信号。[Community profile](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)
- 每个 Release 有用户可读的变化、可下载资产和已知限制，不只自动生成 commit 列表。

### 8.6 应衡量什么

Stars 是传播指标，不等于使用。前 30 天同时记录：

- Release 资产下载量及不同 OS 占比。
- Docker pulls、PyPI 下载和示例仓库 clone/访问趋势。
- 首个有效 issue 的时间、问题关闭时间、外部贡献者数。
- 有多少问题来自真实 SDK 请求，而不是只问“项目何时可用”。
- README 到 Release 页的点击和演示完成率；若没有站点分析，至少用 GitHub Release 下载量替代。

本地工具默认不添加遥测。若未来考虑 opt-in telemetry，必须单独设计并明确征得同意，不能为了增长数据损害“本地、无 key”的信任定位。

## 9. 实施顺序

### 0.1 必须完成

1. 统一 `lmmock` CLI 和所有入口的默认行为。
2. 加入标准库 `run.py` 与锁定依赖。
3. 发布 `linux/amd64`、`macos/arm64`、`windows/amd64` 三个最小原生包。
4. 发布 GHCR `linux/amd64,linux/arm64` 多架构镜像和 `compose.yaml`。
5. 自动生成 SHA256、attestation、Release Notes 和 smoke-test 结果。
6. README 首屏改为主 slogan、演示、Release/Docker/source/Python 四入口。
7. 做 weather tool-call 的三协议真实 SDK 演示。

### 0.1 后按需求增加

- macOS Intel 与 Linux arm64 原生包。
- Homebrew tap、winget、Scoop 或 Chocolatey。
- 安装脚本与自动更新检查。
- PyInstaller `onefile` 实验资产。

不要在第一版同时维护五个系统包管理仓库。先根据 Release 下载平台占比决定 Homebrew、winget 或其他入口的优先级。

## 10. 名称风险补充

进一步检索发现，`frankfliu/junkyard` 中已有一个名为 [`lmmock`](https://github.com/frankfliu/junkyard/tree/master/lmmock) 的 Rust/Cargo 子项目，也在实现 OpenAI-compatible Mock Server。它不是独立仓库，且没有占用 PyPI、npm、`github.com/lmmock` 或已检查域名，但属于真实同类使用。

因此文档不能再声称 LMMock “没有同类冲突”。在投入 Logo、签名证书和大规模传播前，M0 必须做最终名称决策与基础商标检索。若继续使用 LMMock，应把结论写成“关键发行资产当前可用，但存在一个低可见度同类子项目”。
