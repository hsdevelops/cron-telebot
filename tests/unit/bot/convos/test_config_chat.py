from unittest import mock
import pytest

from bot.replies import replies
from bot.convos.config_chat import *
from tests.unit.conftest import mock_update


@pytest.fixture
def mock_job():
    return {
        "chat_id": 1,
        "jobname": "test_job_1",
        "created_by": 1,
        "created_ts": 1,
        "removed_ts": "",
        "nextrun_ts": 2,
    }


@pytest.fixture
def mock_job2():
    return {
        "chat_id": 1,
        "jobname": "test_job_1",
        "created_by": 2,
        "created_ts": 1,
        "removed_ts": "",
        "nextrun_ts": 2,
    }


"""
State 0
"""


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_error_message")
async def test_choose_chat_no_chat(send_msg, simple_update, simple_context):
    res = await choose_chat(simple_update, simple_context)
    assert res == state0
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_prompt_user_bot_message")
async def test_choose_chat_no_user_token(
    send_msg, mongo_service, mock_group, simple_context
):
    await mongo_service.insert_new_chat(mock_group)

    simple_update = mock_update(text="test_group")
    res = await choose_chat(simple_update, simple_context)
    assert res == state1
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_prompt_user_bot_message")
async def test_choose_chat_none_user_token(
    send_msg, mongo_service, mock_group, simple_context
):
    mock_group["user_bot_token"] = None
    await mongo_service.insert_new_chat(mock_group)

    simple_update = mock_update(text="test_group")
    res = await choose_chat(simple_update, simple_context)
    assert res == state1
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_sender_reset_success_message")
async def test_choose_chat_existing_user_token(
    send_msg,
    mongo_service,
    mock_group,
    mock_job,
    mock_job2,
    simple_context,
):
    mock_group["user_bot_token"] = 1
    mock_job["user_bot_token"] = 1
    await mongo_service.insert_new_chat(mock_group)
    await mongo_service.insert_new_entry(mock_job)
    await mongo_service.insert_new_entry(mock_job2)

    simple_update = mock_update(text="test_group")
    res = await choose_chat(simple_update, simple_context)
    assert res == ConversationHandler.END

    send_msg.assert_called_once()

    res = await mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res["user_bot_token"] is None

    res = await mongo_service.find_entries({"chat_id": 1})
    assert len(res) == 2
    assert res[0]["user_bot_token"] is None
    assert res[1]["user_bot_token"] is None


"""
State 1
"""


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_error_message")
async def test_update_sender_invalid_bot(send_msg, mocker, simple_context):
    mock_resp = {"status": 500}
    mocker.patch(
        "bot.convos.config_chat.teleapi.get_bot_details", return_value=mock_resp
    )

    simple_update = mock_update(text="some_token")
    res = await update_sender(simple_update, simple_context)
    assert res == state1
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_sender_change_success_message")
async def test_update_sender_valid_bot(
    send_msg,
    mocker,
    mongo_service,
    simple_update,
    simple_context,
    mock_group,
    mock_job,
    mock_job2,
):
    mock_resp = {"json": {"result": {"id": 1, "username": "test_bot"}}, "status": 200}
    mocker.patch(
        "bot.convos.config_chat.teleapi.get_bot_details", return_value=mock_resp
    )

    mock_group["user_bot_token"] = 1
    await mongo_service.insert_new_chat(mock_group)
    await mongo_service.insert_new_entry(mock_job)
    await mongo_service.insert_new_entry(mock_job2)

    simple_update = mock_update(text="some_token")
    simple_context.user_data["chat_id"] = mock_group["chat_id"]
    simple_context.user_data["chat_title"] = mock_group["chat_title"]
    res = await update_sender(simple_update, simple_context)
    assert res == ConversationHandler.END

    res = await mongo_service.find_one_bot({"id": 1})
    assert res is not None
    assert res["token"] == "some_token"

    res = await mongo_service.find_one_chat_entry({"chat_id": mock_group["chat_id"]})
    assert res["user_bot_token"] == "some_token"

    res = await mongo_service.find_entries({"chat_id": mock_group["chat_id"]})
    assert len(res) == 2
    assert res[0]["user_bot_token"] == "some_token"
    assert res[1]["user_bot_token"] == "some_token"

    send_msg.assert_called_once()
