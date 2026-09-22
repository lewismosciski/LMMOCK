import sqlite3

import pytest

from lmmock.storage import Store


def test_store_closes_connections(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    opened = []
    connect = store._connect

    def tracking_connect():
        conn = connect()
        opened.append(conn)
        return conn

    monkeypatch.setattr(store, "_connect", tracking_connect)
    store.list_rules()
    store.get_settings()
    store.list_groups()
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            conn.execute("SELECT 1")


def test_create_rule_respects_callers_transaction(tmp_path):
    store = Store(tmp_path / "state.db")
    with pytest.raises(RuntimeError):
        with store._connection() as conn:
            store.create_rule({"name": "must roll back"}, conn=conn)
            raise RuntimeError("abort")
    assert all(rule["name"] != "must roll back" for rule in store.list_rules())


def test_deleted_rules_stay_deleted_after_restart(tmp_path):
    path = tmp_path / "state.db"
    store = Store(path)
    for rule in store.list_rules():
        store.delete_rule(rule["id"])
    assert Store(path).list_rules() == []
