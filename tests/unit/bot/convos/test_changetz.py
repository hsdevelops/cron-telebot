from unittest import mock

import pytest
from bot import replies
from bot.convos.changetz import command, update_timezone
from telegram.ext import ConversationHandler


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


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.text")
async def test_update_tz_missing_chat(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    send_msg.assert_called_once_with(simple_update, replies.prompt_start_message)
    assert res == ConversationHandler.END


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("telegram.Message.reply_text")
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=False))
async def test_update_tz_unauthorized(reply, simple_update, simple_context):
    res = await update_timezone(simple_update, simple_context)
    reply.assert_not_called()
    assert res == ConversationHandler.END


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.text")
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=False))
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
async def test_update_tz_missing_tz(send_msg, simple_update, simple_context):
    res = await update_timezone(simple_update, simple_context)
    send_msg.assert_called_once_with(
        simple_update, replies.error_message, reply_markup=replies.force_reply
    )
    assert res == ConversationHandler.END


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.text")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+16:00", 16)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
async def test_update_tz_invalid_tz(send_msg, simple_update, simple_context):
    res = await update_timezone(simple_update, simple_context)
    send_msg.assert_called_once_with(simple_update, replies.error_message)
    assert res == ConversationHandler.END


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+8:00", 8)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
async def test_update_tz_no_change(
    send_msg, simple_update, simple_context, mongo_service, mock_group
):

    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {"tz_offset": 8}  # from previous state

    await mongo_service.insert_new_chat(mock_group)
    res = await update_timezone(simple_update, simple_context)
    send_msg.assert_called_once_with(
        simple_update, replies.timezone_nochange_error_message
    )
    assert res == ConversationHandler.END


@pytest.mark.asyncio
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+9:00", 9)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
async def test_update_tz_group(
    mocker, simple_update, simple_context, mongo_service, mock_group, mock_job
):
    send_msg = mocker.patch("bot.replies.text")

    mock_resp = ("2023-05-07 01:00", "2023-05-07 02:00")
    test_user_nextrun, test_nextrun = mock_resp
    mocker.patch("common.utils.calc_next_run", return_value=mock_resp)

    await mongo_service.insert_new_chat(mock_group)
    await mongo_service.insert_new_entry(mock_job)

    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {"tz_offset": 8}  # from previous state

    res = await update_timezone(simple_update, simple_context)
    send_msg.assert_called_once_with(
        simple_update, "Yipee! Your timezone has been updated to UTC+9:00."
    )
    assert res == ConversationHandler.END

    res_group = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res_group is not None
    assert res_group["utc_tz"] == "+9:00"
    assert res_group["tz_offset"] == 9

    res_jobs = await mongo_service.find_entries({"created_by": 1})
    assert len(res_jobs) == 1
    assert res_jobs[0]["nextrun_ts"] == test_nextrun
    assert res_jobs[0]["user_nextrun_ts"] == test_user_nextrun


@pytest.mark.asyncio
@mock.patch("common.utils.calc_tz", mock.MagicMock(return_value=("+9:00", 9)))
@mock.patch("common.utils.extract_tz_values", mock.MagicMock(return_value=True))
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
async def test_update_tz_private(
    mocker,
    simple_update,
    simple_context,
    mongo_service,
    mock_private,
    mock_channel,
    mock_job,
    mock_job2,
):
    send_msg = mocker.patch("bot.replies.text")

    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {"tz_offset": 8}  # from previous state

    mock_resp = ("2023-05-07 01:00", "2023-05-07 02:00")
    test_user_nextrun, test_nextrun = mock_resp
    mocker.patch("common.utils.calc_next_run", return_value=mock_resp)

    await mongo_service.insert_new_chat(mock_private)
    await mongo_service.insert_new_chat(mock_channel)
    await mongo_service.insert_new_entry(mock_job)
    await mongo_service.insert_new_entry(mock_job2)

    res = await update_timezone(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(
        simple_update, "Yipee! Your timezone has been updated to UTC+9:00."
    )

    res_private = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res_private is not None
    assert res_private["utc_tz"] == "+9:00"
    assert res_private["tz_offset"] == 9

    res_channel = await mongo_service.find_one_chat_entry({"chat_id": 2})
    assert res_channel is not None
    assert res_channel["utc_tz"] == ""
    assert res_channel["tz_offset"] == 9

    res_jobs = await mongo_service.find_entries({"created_by": 1})
    assert len(res_jobs) == 2
    assert res_jobs[0]["nextrun_ts"] == test_nextrun
    assert res_jobs[0]["user_nextrun_ts"] == test_user_nextrun
    assert res_jobs[1]["nextrun_ts"] == test_nextrun
    assert res_jobs[1]["user_nextrun_ts"] == test_user_nextrun
