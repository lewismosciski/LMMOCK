import pytest

from lmmock.storage import Store


def test_default_rules_are_seeded_once(tmp_path):
    database = tmp_path / "lmmock.sqlite3"
    first = Store(database)
    second = Store(database)
    names = [rule["name"] for rule in second.list_rules()]
    assert names == ["foolAI", "Default reply"]
    assert names.count("foolAI") == 1
    assert first.list_groups() == second.list_groups()


def test_rule_validation_rejects_unsupported_types_and_clamps_delay(tmp_path):
    store = Store(tmp_path / "lmmock.sqlite3")
    group_id = store.list_groups()[0]["id"]
    with pytest.raises(ValueError, match="match_type"):
        store.create_rule({"group_id": group_id, "match_type": "prefix"})
    with pytest.raises(ValueError, match="reply_type"):
        store.create_rule({"group_id": group_id, "reply_type": "image"})
    created = store.create_rule({"group_id": group_id, "name": "Delayed", "delay_ms": 999_999})
    assert created["delay_ms"] == 30_000


def test_settings_validation_preserves_last_valid_values(tmp_path):
    store = Store(tmp_path / "lmmock.sqlite3")
    original = store.get_settings()
    with pytest.raises(ValueError, match="At least one model"):
        store.set_settings({"models": [], "default_model": ""})
    with pytest.raises(ValueError, match="default_model"):
        store.set_settings({"models": ["one"], "default_model": "missing"})
    with pytest.raises(ValueError, match="unsupported operation"):
        store.set_settings({"enabled_operations": ["images"]})
    assert store.get_settings() == original


def test_group_deletion_guards_last_and_nonempty_groups(tmp_path):
    store = Store(tmp_path / "lmmock.sqlite3")
    default_group = store.list_groups()[0]
    with pytest.raises(ValueError, match="last behavior group"):
        store.delete_group(default_group["id"])
    extra = store.create_group({"name": "Extra"})
    store.create_rule({"group_id": extra["id"], "name": "Extra reply"})
    with pytest.raises(ValueError, match="Move or delete"):
        store.delete_group(extra["id"])
