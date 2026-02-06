from unittest import mock
from datetime import datetime, timezone

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.start import command, add_timezone
from tests.unit.conftest import mock_update
from telegram import Chat, Update, User, Message


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_start_command_existing_chat(
    send_msg, simple_update, simple_context, mock_group
):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.simple_prompt_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_start_command_new(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once_with(
        simple_update, replies.start_message, reply_markup=replies.force_reply
    )


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_start_add_timezone_invalid(send_msg, simple_context):
    update = mock_update(text="bad")
    with mock.patch("common.utils.extract_timezone", return_value=("", 0, "err")):
        res = await add_timezone(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(update, replies.invalid_timezone_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_start_add_timezone_success(send_msg, simple_context):
    chat = Chat(id=1, type="private")
    usr = User(id=1, first_name="hs", is_bot=False)
    msg = Message(
        date=datetime.now(timezone.utc),
        chat=chat,
        message_id=1,
        from_user=usr,
        text="UTC",
    )
    update = Update(message=msg, update_id=1)
    with mock.patch("common.utils.extract_timezone", return_value=("UTC", 0, None)):
        res = await add_timezone(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(update, replies.help_message)
