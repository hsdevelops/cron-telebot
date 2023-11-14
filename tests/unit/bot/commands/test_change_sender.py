from unittest import mock
import pytest

from bot.commands import change_sender
from bot.convos import config_chat


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_choose_chat_message")
async def test_change_sender(send_msg, mongo_service, simple_update, mock_group):
    mongo_service.insert_new_chat(mock_group)
    res = await change_sender(simple_update, None)
    assert res == config_chat.state0
    send_msg.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_private_only_error_message")
async def test_invalid_chat_type(send_msg, simple_group_update):
    await change_sender(simple_group_update, None)
    send_msg.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_missing_chats_error_message")
async def test_missing_chat(send_msg, simple_update):
    await change_sender(simple_update, None)
    send_msg.assert_called_once()
