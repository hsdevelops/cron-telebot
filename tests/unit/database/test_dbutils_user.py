from unittest import mock

import pytest

from database.dbutils import dbutils_user


@pytest.mark.asyncio
async def test_add_and_retrieve_user(mongo_service):
    await dbutils_user.add_user(mongo_service, user_id=1, username="u", first_name="f")
    res = await dbutils_user.retrieve_user_data(mongo_service, user_id=1)
    assert res is not None
    assert res["username"] == "u"
    assert res["first_name"] == "f"


@pytest.mark.asyncio
async def test_refresh_user_updates_last_used_at(mongo_service):
    await dbutils_user.add_user(mongo_service, user_id=1, username="u", first_name="f")
    entry = await dbutils_user.retrieve_user_data(mongo_service, 1)
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await dbutils_user.refresh_user(mongo_service, entry)

    res = await dbutils_user.retrieve_user_data(mongo_service, 1)
    assert res["last_used_at"] == "ts"


@pytest.mark.asyncio
async def test_supersede_user_sets_superseded_at(mongo_service):
    await dbutils_user.add_user(mongo_service, user_id=1, username="u", first_name="f")
    entry = await dbutils_user.retrieve_user_data(mongo_service, 1)
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await dbutils_user.supersede_user(mongo_service, entry, "username")
    res = await mongo_service.user_data_collection.find_one({"_id": entry["_id"]})
    assert res["superseded_at"] == "ts"
