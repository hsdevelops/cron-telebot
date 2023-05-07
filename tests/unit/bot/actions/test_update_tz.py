from unittest import mock

import pytest
from bot.actions.actions import update_timezone


@pytest.fixture
def mock_job():
    return {
        "chat_id": 1,
        "jobname": "test_job_1",
        "created_by": 1,
        "created_ts": 1,
        "removed_ts": "",
        "crontab": "0 * * * *",
        "nextrun_ts": 2,
    }


@pytest.fixture
def mock_job2():
    return {
        "chat_id": 1,
        "channel_id": 2,
        "jobname": "test_job_2",
        "created_by": 1,
        "created_ts": 1,
        "removed_ts": "",
        "crontab": "0 * * * *",
        "nextrun_ts": 2,
    }


@pytest.mark.usefixtures("mongo_service")
@mock.patch("telegram.Message.reply_text")
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=False))
def test_update_tz_unauthorized(reply, simple_update, simple_context):
    update_timezone(simple_update, simple_context)
    reply.assert_not_called()


@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_error_message")
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=False))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_missing_tz(send_msg, simple_update, simple_context):
    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()


@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_error_message")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+16:00", 16)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_invalid_tz(send_msg, simple_update, simple_context):
    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()


@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_start_message")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+8:00", 8)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_missing_chat(send_msg, simple_update, simple_context):
    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()


@mock.patch("bot.replies.replies.send_timezone_nochange_error_message")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+8:00", 8)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_no_change(
    send_msg, simple_update, simple_context, mongo_service, mock_group
):
    mongo_service.insert_new_chat(mock_group)
    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()


@mock.patch("bot.replies.replies.send_timezone_change_success_message")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+9:00", 9)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_group(
    send_msg, mocker, simple_update, simple_context, mongo_service, mock_group, mock_job
):
    mock_resp = ("2023-05-07 01:00", "2023-05-07 02:00")
    test_user_nextrun, test_nextrun = mock_resp
    mocker.patch("common.utils.calc_next_run", return_value=mock_resp)

    mongo_service.insert_new_chat(mock_group)
    mongo_service.insert_new_entry(mock_job)

    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()

    res_group = mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res_group is not None
    assert res_group["utc_tz"] == "+9:00"
    assert res_group["tz_offset"] == 9

    res_jobs = mongo_service.find_entries({"created_by": 1})
    assert len(res_jobs) == 1
    assert res_jobs[0]["nextrun_ts"] == test_nextrun
    assert res_jobs[0]["user_nextrun_ts"] == test_user_nextrun


@mock.patch("bot.replies.replies.send_timezone_change_success_message")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+9:00", 9)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.actions.actions.check_rights", mock.MagicMock(return_value=True))
def test_update_tz_private(
    send_msg,
    mocker,
    simple_update,
    simple_context,
    mongo_service,
    mock_private,
    mock_channel,
    mock_job,
    mock_job2,
):
    mock_resp = ("2023-05-07 01:00", "2023-05-07 02:00")
    test_user_nextrun, test_nextrun = mock_resp
    mocker.patch("common.utils.calc_next_run", return_value=mock_resp)

    mongo_service.insert_new_chat(mock_private)
    mongo_service.insert_new_chat(mock_channel)
    mongo_service.insert_new_entry(mock_job)
    mongo_service.insert_new_entry(mock_job2)

    update_timezone(simple_update, simple_context)
    send_msg.assert_called_once()

    res_private = mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res_private is not None
    assert res_private["utc_tz"] == "+9:00"
    assert res_private["tz_offset"] == 9

    res_channel = mongo_service.find_one_chat_entry({"chat_id": 2})
    assert res_channel is not None
    assert res_channel["utc_tz"] == ""
    assert res_channel["tz_offset"] == 9

    res_jobs = mongo_service.find_entries({"created_by": 1})
    assert len(res_jobs) == 2
    assert res_jobs[0]["nextrun_ts"] == test_nextrun
    assert res_jobs[0]["user_nextrun_ts"] == test_user_nextrun
    assert res_jobs[1]["nextrun_ts"] == test_nextrun
    assert res_jobs[1]["user_nextrun_ts"] == test_user_nextrun
