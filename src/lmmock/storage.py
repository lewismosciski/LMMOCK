from __future__ import annotations

import json
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

DEFAULT_GROUP = {
    "name": "Default",
    "description": "The default behavior for requests without an explicit group.",
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
                """CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
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
            now = self._now()
            conn.execute(
                "INSERT OR IGNORE INTO groups(name,description,created_at,updated_at) VALUES (?,?,?,?)",
                (DEFAULT_GROUP["name"], DEFAULT_GROUP["description"], now, now),
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(rules)").fetchall()}
            if "group_id" not in columns:
                conn.execute("ALTER TABLE rules ADD COLUMN group_id INTEGER")
            default_group_id = conn.execute("SELECT id FROM groups ORDER BY id LIMIT 1").fetchone()["id"]
            conn.execute("UPDATE rules SET group_id=? WHERE group_id IS NULL", (default_group_id,))
            if conn.execute("SELECT 1 FROM rules LIMIT 1").fetchone() is None:
                self.create_rule({**DEFAULT_RULE, "group_id": default_group_id}, conn=conn)

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
            "group_id": row["group_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_rules(self, group_id: int | None = None) -> list[dict[str, Any]]:
        with self.lock, self._connect() as conn:
            if group_id is None:
                rows = conn.execute("SELECT * FROM rules ORDER BY priority ASC, id ASC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM rules WHERE group_id=? ORDER BY priority ASC, id ASC", (group_id,)).fetchall()
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
            if conn.execute("SELECT 1 FROM groups WHERE id=?", (values["group_id"],)).fetchone() is None:
                raise ValueError("group_id does not exist")
            cur = conn.execute(
                """INSERT INTO rules
                (name, enabled, priority, scopes, match_type, match_value, reply_type, reply_json, delay_ms, group_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["name"], int(values["enabled"]), values["priority"], json.dumps(values["scopes"]),
                    values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                    values["delay_ms"], values["group_id"], now, now,
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
            if conn.execute("SELECT 1 FROM groups WHERE id=?", (values["group_id"],)).fetchone() is None:
                raise ValueError("group_id does not exist")
            cur = conn.execute(
                """UPDATE rules SET name=?, enabled=?, priority=?, scopes=?, match_type=?, match_value=?,
                reply_type=?, reply_json=?, delay_ms=?, group_id=?, updated_at=? WHERE id=?""",
                (values["name"], int(values["enabled"]), values["priority"], json.dumps(values["scopes"]),
                 values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                 values["delay_ms"], values["group_id"], self._now(), rule_id),
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

    @staticmethod
    def _group_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_groups(self) -> list[dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM groups ORDER BY id").fetchall()
            return [self._group_row(row) for row in rows]

    def create_group(self, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "")).strip()[:120]
        if not name:
            raise ValueError("Group name is required")
        description = str(data.get("description", "")).strip()[:500]
        now = self._now()
        with self.lock, self._connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO groups(name,description,created_at,updated_at) VALUES (?,?,?,?)",
                    (name, description, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Group name must be unique") from exc
            conn.commit()
            return self._group_row(conn.execute("SELECT * FROM groups WHERE id=?", (cur.lastrowid,)).fetchone())

    def update_group(self, group_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        name = str(data.get("name", "")).strip()[:120]
        if not name:
            raise ValueError("Group name is required")
        description = str(data.get("description", "")).strip()[:500]
        with self.lock, self._connect() as conn:
            try:
                cur = conn.execute(
                    "UPDATE groups SET name=?, description=?, updated_at=? WHERE id=?",
                    (name, description, self._now(), group_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Group name must be unique") from exc
            conn.commit()
            if cur.rowcount == 0:
                return None
            return self._group_row(conn.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone())

    def delete_group(self, group_id: int) -> bool:
        with self.lock, self._connect() as conn:
            if conn.execute("SELECT COUNT(*) AS count FROM groups").fetchone()["count"] <= 1:
                raise ValueError("The last behavior group cannot be deleted")
            if conn.execute("SELECT 1 FROM rules WHERE group_id=? LIMIT 1", (group_id,)).fetchone():
                raise ValueError("Move or delete this group's rules first")
            cur = conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_settings(self) -> dict[str, Any]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        result: dict[str, Any] = {
            "models": ["mock-model"],
            "default_model": "mock-model",
            "enabled_operations": ["chat", "completions", "responses", "messages"],
            "active_group_id": self.list_groups()[0]["id"],
            "api_key": "",
        }
        saved = {row["key"]: json.loads(row["value"]) for row in rows}
        for key in result:
            if key in saved:
                result[key] = saved[key]
        if "models" not in saved and "model" in saved:
            result["models"] = [str(saved["model"])]
            result["default_model"] = str(saved["model"])
        group_ids = {group["id"] for group in self.list_groups()}
        if result["active_group_id"] not in group_ids:
            result["active_group_id"] = min(group_ids)
        return result

    def set_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "models", "default_model", "enabled_operations", "active_group_id",
            "api_key",
        }
        candidate = self.get_settings()
        candidate.update({key: value for key, value in values.items() if key in allowed})
        if not isinstance(candidate["models"], list):
            raise ValueError("models must be a list")
        models = list(dict.fromkeys(str(model).strip()[:120] for model in candidate["models"] if str(model).strip()))
        if not models:
            raise ValueError("At least one model is required")
        default_model = str(candidate["default_model"]).strip()
        if default_model not in models:
            raise ValueError("default_model must be included in models")
        valid_operations = {"chat", "completions", "responses", "messages"}
        if not isinstance(candidate["enabled_operations"], list):
            raise ValueError("enabled_operations must be a list")
        operations = list(dict.fromkeys(candidate["enabled_operations"]))
        if not operations or any(operation not in valid_operations for operation in operations):
            raise ValueError("enabled_operations contains an unsupported operation")
        group_ids = {group["id"] for group in self.list_groups()}
        active_group_id = int(candidate["active_group_id"])
        if active_group_id not in group_ids:
            raise ValueError("active_group_id does not exist")
        normalized = {
            **candidate,
            "models": models,
            "default_model": default_model,
            "enabled_operations": operations,
            "active_group_id": active_group_id,
        }
        with self.lock, self._connect() as conn:
            for key in values:
                if key in allowed:
                    value = normalized[key]
                    if key == "api_key":
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
        result["group_id"] = int(result.get("group_id") or 1)
        return result
