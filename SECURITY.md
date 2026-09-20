# Security

Please report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/lewismosciski/LMMOCK/security/advisories/new), not a public issue.

LMMock binds to `127.0.0.1` by default. To make it reachable from another machine, bind it to a network interface:

```bash
python3 run.py --host 0.0.0.0
```

The host can also be set with `LMMOCK_HOST`. The optional Mock API key is configured and displayed directly in the web UI, and stored as plain text in the local SQLite database. When set, `/openai/v1/*` and `/anthropic/v1/*` model endpoints require it as either `Authorization: Bearer <key>` or `x-api-key: <key>`.

The management UI and `/__lmmock/api/*` endpoints are intentionally not authenticated. They expose rules, settings, the Mock API key, and recent request bodies. Only use network binding on a trusted private network, and use firewall rules plus a separate authenticated HTTPS gateway if stronger access control is needed. LMMock does not provide users, roles, rate limiting, or TLS.

Recent request bodies may contain prompts, so protect network access and the machine holding the SQLite data directory. Do not use a real provider credential as the Mock API key.
