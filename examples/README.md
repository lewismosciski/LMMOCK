# LMMock examples

Start LMMock, then create a virtual environment and install the two official Python SDKs:

```bash
python3 -m venv .venv-examples
source .venv-examples/bin/activate
python -m pip install -r examples/requirements.txt
```

On Debian or Ubuntu, install `python3-venv` with `apt` first if creating the virtual environment is unavailable. Do not install the example dependencies into the system Python.

Run any example from the repository root:

```bash
python examples/openai_chat.py
python examples/openai_completions.py
python examples/openai_responses.py
python examples/anthropic_messages.py
```

The examples use LMMock's default URLs, model names, and `mock` as the API key. No request is sent to a real provider. Override any value when needed:

| Variable | Default |
| --- | --- |
| `OPENAI_BASE_URL` | `http://127.0.0.1:17321/openai/v1` |
| `OPENAI_API_KEY` | `mock` |
| `OPENAI_MODEL` | `gpt-5.6-sol` |
| `ANTHROPIC_BASE_URL` | `http://127.0.0.1:17321/anthropic` |
| `ANTHROPIC_API_KEY` | `mock` |
| `ANTHROPIC_MODEL` | `claude-5-1-opus` |

If you set a Mock API key for a model in the LMMock UI, use the same value in the corresponding environment variable.
