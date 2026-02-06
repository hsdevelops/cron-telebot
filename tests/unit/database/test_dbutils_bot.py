import pytest

from database.dbutils import dbutils_bot


@pytest.mark.asyncio
async def test_upsert_new_bot_missing_id(mongo_service):
    res = await dbutils_bot.upsert_new_bot(mongo_service, user_id=1, bot_data={})
    assert res.modified_count == 0


@pytest.mark.asyncio
async def test_upsert_new_bot_inserts(mongo_service):
    bot_data = {"id": 123, "username": "bot"}
    res = await dbutils_bot.upsert_new_bot(mongo_service, user_id=1, bot_data=bot_data)
    assert res.matched_count >= 0
    stored = await mongo_service.find_one_bot({"id": 123})
    assert stored["username"] == "bot"
