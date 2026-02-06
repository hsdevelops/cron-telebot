from unittest import mock

import pytest

from database.mongo import MongoService


@pytest.mark.asyncio
async def test_insert_new_entry_sets_timestamps(mongo_service):
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.insert_new_entry(mongo_service, {"a": 1})
    res = await mongo_service.find_one_entry({"a": 1})
    assert res["created_ts"] == "ts"
    assert res["last_update_ts"] == "ts"


@pytest.mark.asyncio
async def test_update_entry_sets_last_update_ts(mongo_service):
    await mongo_service.main_collection.insert_one({"a": 1})
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.update_entry(mongo_service, {"a": 1}, {"b": 2})
    res = await mongo_service.find_one_entry({"a": 1})
    assert res["last_update_ts"] == "ts"


def test_get_collection():
    svc = MongoService.__new__(MongoService)
    svc.db = mock.Mock(col="value")
    assert svc.get_collection("col") == "value"


def test_disconnect_calls_client_close():
    svc = MongoService.__new__(MongoService)
    svc.client = mock.Mock()
    svc.disconnect()
    svc.client.close.assert_called_once()


@pytest.mark.asyncio
async def test_find_entries_with_sort(mongo_service):
    await mongo_service.main_collection.insert_many([{"x": 2}, {"x": 1}])
    res = await MongoService.find_entries(mongo_service, {}, [("x", 1)])
    assert [r["x"] for r in res] == [1, 2]


@pytest.mark.asyncio
async def test_find_one_entry(mongo_service):
    await mongo_service.main_collection.insert_one({"a": 1})
    res = await MongoService.find_one_entry(mongo_service, {"a": 1})
    assert res is not None


@pytest.mark.asyncio
async def test_update_multiple_entries_sets_last_update_ts_and_filters_removed(
    mongo_service,
):
    await mongo_service.main_collection.insert_many(
        [
            {"a": 1, "removed_ts": ""},
            {"a": 1, "removed_ts": "x"},
        ]
    )
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        res = await MongoService.update_multiple_entries(
            mongo_service, {"a": 1}, {"b": 2}
        )
    assert res.modified_count == 1
    updated = await mongo_service.main_collection.find_one({"a": 1, "removed_ts": ""})
    assert updated["b"] == 2
    assert updated["last_update_ts"] == "ts"


@pytest.mark.asyncio
async def test_count_entries(mongo_service):
    await mongo_service.main_collection.insert_many([{"a": 1}, {"a": 1}, {"a": 2}])
    res = await MongoService.count_entries(mongo_service, {"a": 1})
    assert res == 2


@pytest.mark.asyncio
async def test_insert_new_chat_sets_updated_ts(mongo_service):
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.insert_new_chat(mongo_service, {"chat_id": 1})
    res = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res["updated_ts"] == "ts"


@pytest.mark.asyncio
async def test_find_chat_entries(mongo_service):
    await mongo_service.chat_data_collection.insert_many(
        [{"chat_id": 1}, {"chat_id": 2}]
    )
    res = await MongoService.find_chat_entries(mongo_service, {})
    assert len(res) == 2


@pytest.mark.asyncio
async def test_update_chat_entries_sets_updated_ts(mongo_service):
    await mongo_service.chat_data_collection.insert_many(
        [{"chat_id": 1}, {"chat_id": 2}]
    )
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        res = await MongoService.update_chat_entries(mongo_service, {}, {"x": 1})
    assert res.modified_count == 2
    one = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert one["updated_ts"] == "ts"


@pytest.mark.asyncio
async def test_update_one_chat_entry_sets_updated_ts(mongo_service):
    await mongo_service.chat_data_collection.insert_one({"chat_id": 1})
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.update_one_chat_entry(
            mongo_service, {"chat_id": 1}, {"x": 1}
        )
    res = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res["updated_ts"] == "ts"


@pytest.mark.asyncio
async def test_insert_new_user_sets_timestamps(mongo_service):
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.insert_new_user(mongo_service, {"user_id": 1})
    res = await MongoService.find_one_user(mongo_service, {"user_id": 1})
    assert res["created_at"] == "ts"
    assert res["last_used_at"] == "ts"


@pytest.mark.asyncio
async def test_update_one_user(mongo_service):
    await mongo_service.user_data_collection.insert_one({"user_id": 1})
    await MongoService.update_one_user(mongo_service, {"user_id": 1}, {"x": 1})
    res = await MongoService.find_one_user(mongo_service, {"user_id": 1})
    assert res["x"] == 1


@pytest.mark.asyncio
async def test_update_one_bot_sets_updated_at(mongo_service):
    with mock.patch("common.utils.now", mock.MagicMock(return_value="ts")):
        await MongoService.update_one_bot(mongo_service, {"id": 1}, {"name": "b"})
    res = await MongoService.find_one_bot(mongo_service, {"id": 1})
    assert res["updated_at"] == "ts"


@pytest.mark.asyncio
async def test_find_one_whitelist(mongo_service):
    await mongo_service.user_whitelist_collection.insert_one({"user_id": 1})
    res = await MongoService.find_one_whitelist(mongo_service, {"user_id": 1})
    assert res is not None
