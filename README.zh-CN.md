<p align="center">
  <img src="src/lmmock/static/logo.svg" alt="LMMock" width="132" height="132">
</p>

<h1 align="center">LMMock</h1>

<p align="center"><strong>Mock 模型，运行真实应用。</strong></p>

<p align="center">面向 OpenAI 与 Anthropic API 的本地可视化 Mock Server。</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lewismosciski/LMMOCK/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/lewismosciski/LMMOCK/ci.yml?branch=main&style=flat-square&label=tests" alt="测试状态"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/releases"><img src="https://img.shields.io/github/v/release/lewismosciski/LMMOCK?include_prereleases&style=flat-square" alt="发行版本"></a>
  <a href="https://github.com/lewismosciski/LMMOCK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lewismosciski/LMMOCK?style=flat-square" alt="开源协议"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
</p>

LMMock 让应用获得稳定可控的大模型回复，同时保留原来的 SDK 调用代码。在网页中创建规则，把应用指向本地地址，就能在没有真实 API Key 和 Token 消耗的情况下运行完整流程。

## 快速启动

从源码启动：

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 run.py                  # Windows: py run.py
```

或使用 Docker：

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  -v lmmock-data:/data ghcr.io/lewismosciski/lmmock:latest
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。Linux、macOS 与 Windows 的压缩包可以从 [Releases 页面](https://github.com/lewismosciski/LMMOCK/releases)下载。

## 接入现有 SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="mock")
answer = client.responses.create(model="mock-model", input="上海天气如何")
print(answer.output_text)
```

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://127.0.0.1:8000", api_key="mock")
answer = client.messages.create(
    model="mock-model",
    max_tokens=128,
    messages=[{"role": "user", "content": "上海天气如何"}],
)
print(answer.content[0].text)
```

## 支持范围

| Provider | Endpoint | JSON | 流式响应 | 工具调用 |
| --- | --- | :---: | :---: | :---: |
| OpenAI | `POST /v1/chat/completions` | ✓ | ✓ | ✓ |
| OpenAI | `POST /v1/responses` | ✓ | ✓ | ✓ |
| Anthropic | `POST /v1/messages` | ✓ | ✓ | ✓ |

规则可以匹配全部请求、普通文本或正则表达式；回复支持文本、JSON 文本、工具调用、HTTP 错误、捕获变量模板和固定延迟。规则与 Provider 设置保存在本地 SQLite 文件中。

上游转发默认关闭。真实密钥只从 `LMMOCK_OPENAI_API_KEY` 和 `LMMOCK_ANTHROPIC_API_KEY` 环境变量读取，不会写入 SQLite。

## 参与贡献

我们非常欢迎 Bug 报告、协议样例、文档修正和范围清晰的 Pull Request。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

LMMock 专注于本地 Mock，不扩展流量录制、Cassette 回放或 CI 产品。

## 开源协议

Apache-2.0
