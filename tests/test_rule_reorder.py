import sqlite3

import httpx
import pytest

from lmmock.storage import Store


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as session:
        yield session


@pytest.mark.parametrize("invalid", ["bad", None, True, 1.5, 0, -1, 999999, 10**30])
async def test_invalid_reorder_leaves_all_rules_unchanged(client, invalid):
    before = (await client.get("/__lmmock/api/rules")).json()
    response = await client.post("/__lmmock/api/rules/reorder", json={"ids": [before[0]["id"], invalid]})
    assert response.status_code == 400
    assert "error" in response.json()
    assert (await client.get("/__lmmock/api/rules")).json() == before


@pytest.mark.parametrize("ids", [None, "12", 1, {}, [1, 1]])
async def test_invalid_reorder_list_is_rejected(client, ids):
    before = (await client.get("/__lmmock/api/rules")).json()
    assert (await client.post("/__lmmock/api/rules/reorder", json={"ids": ids})).status_code == 400
    assert (await client.get("/__lmmock/api/rules")).json() == before


async def test_reorder_only_updates_requested_priorities(client):
    before = (await client.get("/__lmmock/api/rules")).json()
    extra = (await client.post("/__lmmock/api/rules", json={"name": "Leave me unchanged", "priority": 500})).json()
    ids = [rule["id"] for rule in reversed(before)]
    response = await client.post("/__lmmock/api/rules/reorder", json={"ids": ids})
    assert response.status_code == 200
    after = response.json()
    assert [rule["id"] for rule in after[:len(ids)]] == ids
    for priority, rule_id in enumerate(ids, 1):
        old = next(rule for rule in before if rule["id"] == rule_id)
        new = next(rule for rule in after if rule["id"] == rule_id)
        assert new["priority"] == priority
        assert new == {**old, "priority": priority, "updated_at": new["updated_at"]}
    assert next(rule for rule in after if rule["id"] == extra["id"]) == extra
    for body in ({}, {"ids": []}):
        assert (await client.post("/__lmmock/api/rules/reorder", json=body)).json() == after


def test_database_failure_rolls_back_entire_reorder(tmp_path):
    store = Store(tmp_path / "state.db")
    before = store.list_rules()
    ids = [rule["id"] for rule in before]
    with store._connection() as conn:
        conn.execute(f"""CREATE TRIGGER fail_second_update BEFORE UPDATE ON rules
            WHEN NEW.id = {ids[1]}
            BEGIN SELECT RAISE(ABORT, 'simulated failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="simulated failure"):
        store.reorder_rules(ids)
    assert store.list_rules() == before
