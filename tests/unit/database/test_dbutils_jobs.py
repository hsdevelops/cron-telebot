from unittest import mock
import pytest
from database.dbutils import dbutils_job


@pytest.fixture
def mock_jobs():
    return [
        {
            "_id": 1,
            "chat_id": 1,
            "jobname": "test_job_1",
            "created_by": 1,
            "created_ts": 2,
            "removed_ts": "",
            "nextrun_ts": "2012-02-11 08:22:00",
        },
        {
            "_id": 2,
            "chat_id": 1,
            "jobname": "test_job_2",
            "created_by": 1,
            "created_ts": 3,
            "crontab": "* * * * *",
            "removed_ts": "",
            "nextrun_ts": "2012-02-11 08:22:00",
        },
        {
            "_id": 3,
            "chat_id": 1,
            "jobname": "test_job_3",
            "created_by": 1,
            "created_ts": 1,
            "removed_ts": "",
            "nextrun_ts": "2012-02-11 08:22:00",
            "pending_ts": "2012-12-10 23:59:00",
        },
        {
            "_id": 4,
            "chat_id": 1,
            "jobname": "test_job_4",
            "created_by": 1,
            "created_ts": 1,
            "removed_ts": "2012-02-11 08:22:00",
            "nextrun_ts": "2012-02-11 08:22:00",
        },
        {
            "_id": 5,
            "chat_id": 1,
            "jobname": "test_job_5",
            "created_by": 1,
            "created_ts": 1,
            "paused_ts": "2012-02-11 08:22:00",
            "removed_ts": "",
            "nextrun_ts": "2012-02-11 08:22:00",
            "errors": [],
        },
        {
            "_id": 6,
            "chat_id": 1,
            "jobname": "test_job_5",
            "created_by": 1,
            "created_ts": 1,
            "removed_ts": "2012-02-11 08:22:00",
            "nextrun_ts": "2012-02-11 08:22:00",
            "errors": [{"error": "Error 400", "timestamp": ""}],
        },
        {
            "_id": 7,
            "chat_id": 3,
            "jobname": "test_job_6",
            "created_by": 3,
            "created_ts": 1,
            "removed_ts": "",
            "nextrun_ts": "2012-02-11 08:22:00",
            "errors": [],
            "pending_ts": "2012-12-11 00:00:10",
        },
    ]


"""
Getters
"""


def test_find_latest_entry(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    res = dbutils_job.find_latest_entry(mongo_service, chat_id=1)
    assert res["chat_id"] == 1
    assert res["jobname"] == "test_job_2"
    assert res["created_ts"] == 3
    assert res["removed_ts"] == ""


def test_find_entry_by_jobname(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    res = dbutils_job.find_entry_by_jobname(mongo_service, 1, "test_job_4", True)
    assert res is not None

    res = dbutils_job.find_entry_by_jobname(mongo_service, 1, "test_job_4", False)
    assert res is None


def test_find_entries_removed_between(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    res = dbutils_job.find_entries_removed_between(
        mongo_service, "2012-02-10", "2012-02-12"
    )
    assert len(res) == 2

    res = dbutils_job.find_entries_removed_between(
        mongo_service, "2012-02-10", "2012-02-12", 400
    )
    assert len(res) == 1

    res = dbutils_job.find_entries_removed_between(
        mongo_service, "2012-02-12", "2012-02-13"
    )
    assert len(res) == 0


@mock.patch("common.utils.now", mock.MagicMock(return_value="2012-12-11 00:00:00"))
def test_find_entries_by_nextrun(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)
    res = dbutils_job.find_entries_by_nextrun(mongo_service, "2013-12-11 00:00:00")
    ids = [entry["_id"] for entry in res]
    assert set(ids) == set([1, 2, 3])
    assert len(res) == 3


def test_find_entries_by_chatid(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    # should only find active entries
    res = dbutils_job.find_entries_by_chatid(mongo_service, 1)
    assert len(res) == 4

    res = dbutils_job.find_entries_by_chatid(mongo_service, "1")
    assert len(res) == 4

    res = dbutils_job.find_entries_by_chatid(mongo_service, 2)
    assert len(res) == 0


def test_count_entries_by_userid(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    res = dbutils_job.count_entries_by_userid(mongo_service, 1)
    assert res == 4

    res = dbutils_job.count_entries_by_userid(mongo_service, 2)
    assert res == 0


@pytest.mark.parametrize("chat_id, expected", [(2, False), (1, True), ("1", True)])
def test_entry_exists(mongo_service, mock_jobs, chat_id, expected):
    mongo_service.main_collection.insert_many(mock_jobs)
    res = dbutils_job.entry_exists(mongo_service, chat_id, "test_job_1")
    assert res is expected


"""
Setters
"""


def test_add_new_entry(mongo_service):
    dbutils_job.add_new_entry(mongo_service, chat_id=1, jobname="test_job", user_id=2)
    res = mongo_service.find_one_entry({"chat_id": 1})
    assert res is not None
    assert res["created_ts"] is not None
    assert res["last_update_ts"] is not None
    assert res["created_by"] == 2
    assert res["last_updated_by"] == 2
    assert res["chat_id"] == 1
    assert res["channel_id"] == ""
    assert res["jobname"] == "test_job"
    assert res["crontab"] == ""
    assert res["content"] == ""
    assert res["content_type"] == ""
    assert res["photo_id"] == ""
    assert res["photo_group_id"] == ""
    assert res["previous_message_id"] == ""
    assert res["option_delete_previous"] == ""
    assert res["nextrun_ts"] == ""
    assert res["user_nextrun_ts"] == ""
    assert res["removed_ts"] == ""
    assert res["remarks"] == ""
    assert res["user_bot_token"] is None
    assert res["errors"] == []


def test_remove_entries_by_chat(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)
    dbutils_job.remove_entries_by_chat(mongo_service, 1)
    result = dbutils_job.find_entries_by_chatid(mongo_service, 1)
    assert len(result) == 0


def test_update_entry_by_jobname(mongo_service, mock_jobs):
    mongo_service.main_collection.insert_many(mock_jobs)

    q = {"jobname": "test_job_1", "chat_id": 1, "created_ts": 2}
    update = {"created_ts": 4}
    dbutils_job.update_entry_by_jobname(mongo_service, q, update)

    res = mongo_service.find_one_entry({"_id": 1})
    assert res is not None
    assert res["created_ts"] == 4
