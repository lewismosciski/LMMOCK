from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DEFAULT_RULE = {
    "name": "Default reply",
    "enabled": True,
    "priority": 1000,
    "model_pattern": "*",
    "scopes": ["*"],
    "match_type": "all",
    "match_value": "",
    "reply_type": "text",
    "reply": {"content": "LMMock is running."},
    "delay_ms": 0,
}

FOOL_AI_RULE = {
    "name": "foolAI",
    "enabled": True,
    "priority": 100,
    "model_pattern": "*",
    "scopes": ["*"],
    "match_type": "regex",
    "match_value": r"(?:^|\n)(?:user:\s*)?(?P<question>[^\n]+?)(?:[?？]+|[吗么嘛呢])(?:[\"'”’])?\s*$",
    "reply_type": "text",
    "reply": {"content": "${question|foolAI}"},
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

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.lock, self._connection() as conn:
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
                    model_pattern TEXT NOT NULL DEFAULT '*',
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
            if "model_pattern" not in columns:
                conn.execute("ALTER TABLE rules ADD COLUMN model_pattern TEXT NOT NULL DEFAULT '*'")
            default_group_id = conn.execute("SELECT id FROM groups ORDER BY id LIMIT 1").fetchone()["id"]
            conn.execute("UPDATE rules SET group_id=? WHERE group_id IS NULL", (default_group_id,))
            if conn.execute("SELECT 1 FROM rules LIMIT 1").fetchone() is None:
                self.create_rule({**DEFAULT_RULE, "group_id": default_group_id}, conn=conn)
            seeded = conn.execute("SELECT 1 FROM settings WHERE key='seed_fool_ai_v1'").fetchone()
            if seeded is None:
                exists = conn.execute("SELECT 1 FROM rules WHERE name=? LIMIT 1", (FOOL_AI_RULE["name"],)).fetchone()
                if exists is None:
                    self.create_rule({**FOOL_AI_RULE, "group_id": default_group_id}, conn=conn)
                conn.execute(
                    "INSERT INTO settings(key,value) VALUES ('seed_fool_ai_v1', 'true')"
                )
            configured = conn.execute("SELECT value FROM settings WHERE key='model_configs'").fetchone()
            if configured is not None:
                model_configs = json.loads(configured["value"])
                names_and_protocols = [(item.get("name"), item.get("protocol")) for item in model_configs]
                if names_and_protocols == [("mock-model", "openai"), ("mock-claude", "anthropic")]:
                    model_configs[0]["name"] = "gpt-5.6-sol"
                    model_configs[1]["name"] = "claude-5-1-opus"
                    conn.execute(
                        "UPDATE settings SET value=? WHERE key='model_configs'",
                        (json.dumps(model_configs),),
                    )
            conn.execute("DELETE FROM settings WHERE key='default_model'")

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
            "model_pattern": row["model_pattern"],
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
        with self.lock, self._connection() as conn:
            if group_id is None:
                rows = conn.execute("SELECT * FROM rules ORDER BY priority ASC, id ASC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM rules WHERE group_id=? ORDER BY priority ASC, id ASC", (group_id,)).fetchall()
            return [self._row(row) for row in rows]

    def create_rule(self, data: dict[str, Any], conn: sqlite3.Connection | None = None) -> dict[str, Any]:
        if conn is None:
            with self.lock, self._connection() as owned:
                return self.create_rule(data, conn=owned)
        values = self._validate_rule(data)
        now = self._now()
        if conn.execute("SELECT 1 FROM groups WHERE id=?", (values["group_id"],)).fetchone() is None:
            raise ValueError("group_id does not exist")
        cur = conn.execute(
            """INSERT INTO rules
            (name, enabled, priority, model_pattern, scopes, match_type, match_value, reply_type, reply_json, delay_ms, group_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                values["name"], int(values["enabled"]), values["priority"], values["model_pattern"], json.dumps(values["scopes"]),
                values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                values["delay_ms"], values["group_id"], now, now,
            ),
        )
        return self._row(conn.execute("SELECT * FROM rules WHERE id=?", (cur.lastrowid,)).fetchone())

    def update_rule(self, rule_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        values = self._validate_rule(data)
        with self.lock, self._connection() as conn:
            if conn.execute("SELECT 1 FROM groups WHERE id=?", (values["group_id"],)).fetchone() is None:
                raise ValueError("group_id does not exist")
            cur = conn.execute(
                """UPDATE rules SET name=?, enabled=?, priority=?, model_pattern=?, scopes=?, match_type=?, match_value=?,
                reply_type=?, reply_json=?, delay_ms=?, group_id=?, updated_at=? WHERE id=?""",
                (values["name"], int(values["enabled"]), values["priority"], values["model_pattern"], json.dumps(values["scopes"]),
                 values["match_type"], values["match_value"], values["reply_type"], json.dumps(values["reply"]),
                 values["delay_ms"], values["group_id"], self._now(), rule_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            return self._row(conn.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone())

    def delete_rule(self, rule_id: int) -> bool:
        with self.lock, self._connection() as conn:
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
        with self.lock, self._connection() as conn:
            rows = conn.execute("SELECT * FROM groups ORDER BY id").fetchall()
            return [self._group_row(row) for row in rows]

    def create_group(self, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "")).strip()[:120]
        if not name:
            raise ValueError("Group name is required")
        description = str(data.get("description", "")).strip()[:500]
        now = self._now()
        with self.lock, self._connection() as conn:
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
        with self.lock, self._connection() as conn:
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
        with self.lock, self._connection() as conn:
            if conn.execute("SELECT COUNT(*) AS count FROM groups").fetchone()["count"] <= 1:
                raise ValueError("The last behavior group cannot be deleted")
            configured = conn.execute("SELECT value FROM settings WHERE key='model_configs'").fetchone()
            if configured and any(group_id in item.get("group_ids", []) for item in json.loads(configured["value"])):
                raise ValueError("Remove this group from its models first")
            if conn.execute("SELECT 1 FROM rules WHERE group_id=? LIMIT 1", (group_id,)).fetchone():
                raise ValueError("Move or delete this group's rules first")
            cur = conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_settings(self) -> dict[str, Any]:
        with self.lock, self._connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        groups = self.list_groups()
        default_group_id = groups[0]["id"]
        result: dict[str, Any] = {
            "model_configs": [
                {"name": "gpt-5.6-sol", "protocol": "openai", "api_key": "", "group_ids": [default_group_id]},
                {"name": "claude-5-1-opus", "protocol": "anthropic", "api_key": "", "group_ids": [default_group_id]},
            ],
            "active_group_id": default_group_id,
        }
        saved = {row["key"]: json.loads(row["value"]) for row in rows}
        for key in result:
            if key in saved:
                result[key] = saved[key]
        if "model_configs" not in saved and ("models" in saved or "model" in saved):
            legacy_models = saved.get("models") or [saved["model"]]
            result["model_configs"] = [
                {"name": str(model), "protocol": "openai", "api_key": saved.get("api_key", ""), "group_ids": [default_group_id]}
                for model in legacy_models
            ]
        group_ids = {group["id"] for group in groups}
        if result["active_group_id"] not in group_ids:
            result["active_group_id"] = min(group_ids)
        result["models"] = [config["name"] for config in result["model_configs"]]
        return result

    def set_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "model_configs", "active_group_id",
        }
        candidate = self.get_settings()
        candidate.update({key: value for key, value in values.items() if key in allowed})
        if not isinstance(candidate["model_configs"], list) or not candidate["model_configs"]:
            raise ValueError("At least one model is required")
        group_ids = {group["id"] for group in self.list_groups()}
        model_configs = []
        for item in candidate["model_configs"]:
            if not isinstance(item, dict):
                raise ValueError("Each model configuration must be an object")
            name = str(item.get("name", "")).strip()[:120]
            if not name:
                raise ValueError("Each model requires a name")
            protocol = str(item.get("protocol", "openai"))
            if protocol not in {"openai", "anthropic", "gemini"}:
                raise ValueError("Model protocol must be openai, anthropic, or gemini")
            assigned_groups = list(dict.fromkeys(int(group_id) for group_id in item.get("group_ids", [])))
            if not assigned_groups or any(group_id not in group_ids for group_id in assigned_groups):
                raise ValueError("Each model requires one or more existing behavior groups")
            model_configs.append({
                "name": name,
                "protocol": protocol,
                "api_key": str(item.get("api_key", ""))[:500],
                "group_ids": assigned_groups,
            })
        models = [config["name"] for config in model_configs]
        if len(models) != len(set(models)):
            raise ValueError("Model names must be unique")
        active_group_id = int(candidate["active_group_id"])
        if active_group_id not in group_ids:
            raise ValueError("active_group_id does not exist")
        normalized = {
            **candidate,
            "model_configs": model_configs,
            "active_group_id": active_group_id,
        }
        with self.lock, self._connection() as conn:
            for key in values:
                if key in allowed:
                    value = normalized[key]
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
        result["model_pattern"] = str(result.get("model_pattern", "*")).strip()[:1000] or "*"
        result["scopes"] = list(result["scopes"] or ["*"])
        result["match_type"] = str(result["match_type"])
        if result["match_type"] not in {"all", "contains", "regex"}:
            raise ValueError("match_type must be all, contains, or regex")
        result["match_value"] = str(result.get("match_value", ""))[:4000]
        result["reply_type"] = str(result["reply_type"])
        if result["reply_type"] not in {"text", "json", "tool", "error", "random"}:
            raise ValueError("reply_type must be text, json, tool, error, or random")
        result["reply"] = dict(result.get("reply") or {})
        if result["reply_type"] == "random":
            result["reply"]["size"] = max(0, min(int(result["reply"].get("size", 4096)), 10_000_000))
        result["delay_ms"] = max(0, min(int(result.get("delay_ms", 0)), 30_000))
        result["group_id"] = int(result.get("group_id") or 1)
        return result
