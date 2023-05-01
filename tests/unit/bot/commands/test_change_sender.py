from unittest import mock
import pytest
from telegram import Message

from bot.commands import change_sender
from bot.replies import replies
import config
from bot.convos import config_chat


@pytest.fixture
def mock_chat():
    return {
        "chat_id": 1,
        "chat_title": 1,
        "chat_type": "group",
        "tz_offset": 8,
        "utc_tz": 8,
        "created_by": 1,
        "telegram_ts": 1,
        "restriction": "",
    }


@mock.patch("telegram.Message.reply_text")
def test_change_sender(reply, mongo_service, simple_update, mock_chat):
    mongo_service.insert_new_chat(mock_chat)

    res = change_sender(simple_update, None)
    assert res == config_chat.state0
    reply.assert_called_with(replies.choose_chat_message, reply_markup=mock.ANY)


@pytest.mark.usefixtures("mongo_service")
@mock.patch("telegram.Message.reply_text")
def test_invalid_chat_type(reply, simple_group_update):
    res = change_sender(simple_group_update, None)
    assert res is None
    reply.assert_called_with(replies.private_only_error_message % config.BOT_NAME)


@pytest.mark.usefixtures("mongo_service")
@mock.patch("telegram.Message.reply_text")
def test_missing_chat(reply: Message.reply_text, simple_update):
    res = change_sender(simple_update, None)
    assert res is None
    reply.assert_called_with(replies.missing_chats_error_message % config.BOT_NAME)
