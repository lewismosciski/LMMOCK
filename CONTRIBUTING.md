# Contributing to LMMock

Thank you for helping LMMock give AI applications predictable local replies. Small, focused contributions are the easiest to review and merge.

## Good contributions

- Reproducible OpenAI or Anthropic compatibility fixes
- Protocol fixtures and regression tests
- Clearer rule editing and diagnostics
- Installation fixes for Linux, macOS, Windows, or Docker
- Documentation and translation corrections

Please open an issue before starting a large feature. LMMock is mock-first: recording, cassette replay, hosted multi-user features, and a CI product remain out of scope.

## Development setup

```bash
git clone https://github.com/lewismosciski/LMMOCK.git
cd LMMOCK
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

Before submitting a pull request:

1. Add a test for behavior changes.
2. Run `python -m pytest`.
3. Keep public claims limited to behavior the tests cover.
4. Update both READMEs when changing user-facing instructions.

## Pull requests

Explain the problem, the chosen behavior, and how you verified it. Screenshots help for interface changes; raw request and response shapes help for protocol changes. Do not include provider API keys, copied production traffic, or generated fixture data containing private content.

---

# 参与 LMMock 贡献

感谢你帮助 LMMock 为 AI 应用提供稳定可控的本地回复。范围清晰、改动集中的贡献最容易审查与合并。

我们特别欢迎：

- 可复现的 OpenAI 或 Anthropic 兼容性修复
- 协议样例与回归测试
- 规则编辑和请求诊断改进
- Linux、macOS、Windows 或 Docker 安装修复
- 文档与翻译修正

大型功能请先创建 Issue 讨论。LMMock 坚持 Mock-first，流量录制、Cassette 回放、多人托管和 CI 产品不在项目范围内。

提交 Pull Request 前，请为行为变化补充测试、运行 `python -m pytest`，并同步修改中英文 README。协议问题请附上最小请求与响应结构，界面修改建议附截图。不要提交真实 Provider API Key、生产流量或包含隐私内容的 Fixture。
