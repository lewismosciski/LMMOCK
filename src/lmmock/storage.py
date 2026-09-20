from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RULE = {
    "name": "Default reply",
    "enabled": True,
    "priority": 1000,
    "scopes": ["*"],
    "match_type": "all",
    "match_value": "",
    "reply_type": "text",
    "reply": {"content": "LMMock is running."},
    "delay_ms": 0,
}


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 100,
                    scopes TEXT NOT NULL,
                    match_type TEXT NOT NULL,
                    match_value TEXT NOT NULL DEFAULT '',
                    reply_type TEXT NOT NULL,
                    reply_json TEXT NOT NULL,
                    delay_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            if conn.execute("SELECT 1 FROM rules LIMIT 1").fetchone() is None:
                self.create_rule(DEFAULT_RULE, conn=conn)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "enabled": bool(row["enabled"]),
            "priority": row["priority"],
            "scopes": json.loads(row["scopes"]),
            "match_type": row["match_type"],
            "match_value": row["match_value"],
            "reply_type": row["reply_type"],
            "reply": json.loads(row["reply_json"]),
            "delay_ms": row["delay_ms"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_rules(self) -> list[dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM rules ORDER BY priority ASC, id ASC").fetchall()
            return [self._row(row) for row in rows]

    def create_rule(self, data: dict[str, Any], conn: sqlite3.Connection | None = None) -> dict[str, Any]:
        values = self._validate_rule(data)
        own = conn is None
        if own:
            self.lock.acquire()
            conn = self._connect()
        assert conn is not None
        now = self._now()
        try:
            cur = conn.execute(
                """INSERT INTO rules
                (name, enabled, priority, scopes, match_type, match_value, reply_type, reply_json, delay_ms, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["name"], int(values["enabled"]), values["priority"], json.dumps(values["scopes"]),
                    values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                    values["delay_ms"], now, now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM rules WHERE id=?", (cur.lastrowid,)).fetchone()
            return self._row(row)
        finally:
            if own:
                conn.close()
                self.lock.release()

    def update_rule(self, rule_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        values = self._validate_rule(data)
        with self.lock, self._connect() as conn:
            cur = conn.execute(
                """UPDATE rules SET name=?, enabled=?, priority=?, scopes=?, match_type=?, match_value=?,
                reply_type=?, reply_json=?, delay_ms=?, updated_at=? WHERE id=?""",
                (values["name"], int(values["enabled"]), values["priority"], json.dumps(values["scopes"]),
                 values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                 values["delay_ms"], self._now(), rule_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            return self._row(conn.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone())

    def delete_rule(self, rule_id: int) -> bool:
        with self.lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_settings(self) -> dict[str, Any]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        result: dict[str, Any] = {
            "model": "mock-model",
            "forward_openai": False,
            "forward_anthropic": False,
            "openai_base_url": "",
            "anthropic_base_url": "",
            "openai_api_key_configured": bool(os.getenv("LMMOCK_OPENAI_API_KEY")),
            "anthropic_api_key_configured": bool(os.getenv("LMMOCK_ANTHROPIC_API_KEY")),
        }
        saved = {row["key"]: json.loads(row["value"]) for row in rows}
        for key in result:
            if key in saved:
                result[key] = saved[key]
        # Migrate settings written by versions that exposed three proxy modes.
        for provider in ("openai", "anthropic"):
            forward_key = f"forward_{provider}"
            mode_key = f"mode_{provider}"
            if forward_key not in saved and mode_key in saved:
                result[forward_key] = saved[mode_key] != "mock-only"
        return result

    def set_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {"model", "forward_openai", "forward_anthropic", "openai_base_url", "anthropic_base_url"}
        with self.lock, self._connect() as conn:
            for key, value in values.items():
                if key in allowed:
                    if key in {"forward_openai", "forward_anthropic"}:
                        if not isinstance(value, bool):
                            raise ValueError(f"{key} must be true or false")
                    if key.endswith("base_url"):
                        value = str(value or "")[:500]
                    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, json.dumps(value)))
            conn.commit()
        return self.get_settings()

    @staticmethod
    def _validate_rule(data: dict[str, Any]) -> dict[str, Any]:
        result = dict(DEFAULT_RULE)
        result.update({key: value for key, value in data.items() if value is not None})
        result["name"] = str(result["name"])[:120] or "Untitled rule"
        result["enabled"] = bool(result["enabled"])
        result["priority"] = int(result["priority"])
        result["scopes"] = list(result["scopes"] or ["*"])
        result["match_type"] = str(result["match_type"])
        if result["match_type"] not in {"all", "contains", "regex"}:
            raise ValueError("match_type must be all, contains, or regex")
        result["match_value"] = str(result.get("match_value", ""))[:4000]
        result["reply_type"] = str(result["reply_type"])
        if result["reply_type"] not in {"text", "json", "tool", "error"}:
            raise ValueError("reply_type must be text, json, tool, or error")
        result["reply"] = dict(result.get("reply") or {})
        result["delay_ms"] = max(0, min(int(result.get("delay_ms", 0)), 30_000))
        return result
