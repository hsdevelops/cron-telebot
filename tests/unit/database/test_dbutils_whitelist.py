import pytest

from database.dbutils import dbutils_whitelist


@pytest.mark.asyncio
async def test_get_user_limit_default(monkeypatch, mongo_service):
    async def fake_count(*_):
        return 0

    monkeypatch.setattr("database.dbutils.dbutils.count_entries_by_userid", fake_count)
    exceeded, limit = await dbutils_whitelist.get_user_limit(mongo_service, 1)
    assert exceeded is False
    assert limit > 0


@pytest.mark.asyncio
async def test_get_user_limit_with_whitelist(monkeypatch, mongo_service):
    async def fake_count(*_):
        return 3

    monkeypatch.setattr("database.dbutils.dbutils.count_entries_by_userid", fake_count)
    await mongo_service.user_whitelist_collection.insert_one(
        {"user_id": 1, "removed_ts": "", "new_limit": 5}
    )
    current_count, limit = await dbutils_whitelist.get_user_limit(mongo_service, 1)
    assert current_count == 3
    assert limit == 5
