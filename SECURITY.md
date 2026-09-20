# Security

Please report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/lewismosciski/LMMOCK/security/advisories/new), not a public issue.

LMMock binds to `127.0.0.1` by default. It has no authentication layer and should not be exposed to an untrusted network. Real provider keys are read from environment variables and are not stored in SQLite or returned by the management API.
