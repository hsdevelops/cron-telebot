from unittest import mock
import pytest

from bot.replies import replies
from bot.convos.config_chat import *


@pytest.fixture
def mock_chat():
    return {
        "chat_id": 1,
        "chat_title": "test_group",
        "chat_type": "group",
        "tz_offset": 8,
        "utc_tz": 8,
        "created_by": 1,
        "telegram_ts": 1,
        "restriction": "",
        "user_bot_token": 1,
    }


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


@mock.patch("telegram.Message.reply_text")
def test_choose_chat_no_chat(reply, simple_update):
    res = choose_chat(simple_update, None)
    assert res == state0
    reply.assert_called_once_with(replies.error_message)


@mock.patch("telegram.Message.reply_text")
def test_choose_chat_no_user_token(
    reply, mongo_service, mock_chat, simple_update, simple_context
):
    del mock_chat["user_bot_token"]
    mongo_service.insert_new_chat(mock_chat)

    simple_update.message.text = "test_group"
    res = choose_chat(simple_update, simple_context)
    assert res == state1
    expected_reply = replies.prompt_user_bot_message
    reply.assert_called_once_with(expected_reply, reply_markup=mock.ANY)


@mock.patch("telegram.Message.reply_text")
def test_choose_chat_none_user_token(
    reply, mongo_service, mock_chat, simple_update, simple_context
):
    mock_chat["user_bot_token"] = None
    mongo_service.insert_new_chat(mock_chat)

    simple_update.message.text = "test_group"
    res = choose_chat(simple_update, simple_context)
    assert res == state1
    expected_reply = replies.prompt_user_bot_message
    reply.assert_called_once_with(expected_reply, reply_markup=mock.ANY)


@mock.patch("telegram.Message.reply_text")
def test_choose_chat_existing_user_token(
    reply, mongo_service, mock_chat, mock_job, mock_job2, simple_update, simple_context
):
    mock_chat["user_bot_token"] = 1
    mock_job["user_bot_token"] = 1
    mongo_service.insert_new_chat(mock_chat)
    mongo_service.insert_new_entry(mock_job)
    mongo_service.insert_new_entry(mock_job2)

    simple_update.message.text = "test_group"
    res = choose_chat(simple_update, simple_context)
    assert res == ConversationHandler.END

    expected_reply = replies.sender_reset_success_message
    reply.assert_called_once_with(expected_reply, reply_markup=mock.ANY)

    res = mongo_service.find_one_chat_entry({"chat_id": 1})
    assert res["user_bot_token"] is None

    res = mongo_service.find_entries({"chat_id": 1})
    assert len(res) == 2
    assert res[0]["user_bot_token"] is None
    assert res[1]["user_bot_token"] is None


"""
State 1
"""


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@mock.patch("telegram.Message.reply_text")
def test_update_sender_invalid_bot(reply, simple_update, simple_context):
    simple_update.message.text = "some_token"
    res = update_sender(simple_update, simple_context)
    assert res == state1
    reply.assert_called_once_with(replies.error_message)


@mock.patch("telegram.Message.reply_text")
def test_update_sender_valid_bot(
    reply,
    mocker,
    mongo_service,
    simple_update,
    simple_context,
    mock_chat,
    mock_job,
    mock_job2,
):
    mock_resp = MockResponse({"result": {"id": 1, "username": "test_bot"}}, 200)
    mocker.patch("bot.convos.config_chat.get_bot_details", return_value=mock_resp)

    mongo_service.insert_new_chat(mock_chat)
    mongo_service.insert_new_entry(mock_job)
    mongo_service.insert_new_entry(mock_job2)

    simple_update.message.text = "some_token"
    simple_context.user_data["chat_id"] = mock_chat["chat_id"]
    simple_context.user_data["chat_title"] = mock_chat["chat_title"]
    res = update_sender(simple_update, simple_context)
    assert res == ConversationHandler.END

    res = mongo_service.find_one_bot({"id": 1})
    assert res is not None
    assert res["token"] == "some_token"

    res = mongo_service.find_one_chat_entry({"chat_id": mock_chat["chat_id"]})
    assert res["user_bot_token"] == "some_token"

    res = mongo_service.find_entries({"chat_id": mock_chat["chat_id"]})
    assert len(res) == 2
    assert res[0]["user_bot_token"] == "some_token"
    assert res[1]["user_bot_token"] == "some_token"

    reply.assert_called_once()
