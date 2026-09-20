# Security

Please report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/lewismosciski/LMMOCK/security/advisories/new), not a public issue.

LMMock binds to `127.0.0.1` by default. To make it reachable from another machine, bind it to a network interface and enable API key protection at the same time:

```bash
export LMMOCK_API_KEY="choose-a-long-random-key"
python3 run.py --host 0.0.0.0
```

The host can also be set with `LMMOCK_HOST`; `--api-key` is available for temporary local testing, but an environment variable avoids putting the key in the process command line. When protection is enabled, all model endpoints and management APIs require the key as either `Authorization: Bearer <key>` or `x-api-key: <key>`. The web assets and health check remain public so the browser can load and ask for the key.

Use a firewall or private network in addition to the key when exposing LMMock. The built-in protection is intentionally simple; it does not provide users, roles, rate limiting, or TLS. Put LMMock behind an HTTPS reverse proxy before using it across an untrusted network.

Real provider keys are read from `LMMOCK_OPENAI_API_KEY` and `LMMOCK_ANTHROPIC_API_KEY`. They are not stored in SQLite or returned by the management API. Recent request bodies may contain prompts, so protect access to the management API and the machine holding the SQLite data directory.
