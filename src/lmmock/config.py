from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    configured = os.getenv("LMMOCK_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LMMock"
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", Path.home())) / "LMMock"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "LMMock"


def env_or(name: str, default: str) -> str:
    return os.getenv(name, default)


def host() -> str:
    return env_or("LMMOCK_HOST", "127.0.0.1")


def port() -> int:
    return int(env_or("LMMOCK_PORT", "8000"))


def api_key() -> str:
    return os.getenv("LMMOCK_API_KEY", "")


def no_browser() -> bool:
    return os.getenv("LMMOCK_NO_BROWSER", "").lower() in {"1", "true", "yes"}
