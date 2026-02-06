from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.reset import command, reset


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=False))
@mock.patch("bot.replies.text")
async def test_reset_command_unauthorized(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_not_called()


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_reset_command_no_entries(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.simple_prompt_message)


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_reset_command_success(send_msg, simple_update, simple_context):
    await simple_context.application.bot_data["mongo"].insert_new_entry(
        {
            "chat_id": 1,
            "jobname": "job",
            "created_by": 1,
            "created_ts": 1,
            "removed_ts": "",
        }
    )
    res = await command(simple_update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once()


@pytest.mark.asyncio
async def test_reset_confirm(simple_context):
    query = mock.Mock()
    query.data = "1"
    query.from_user.id = 1
    query.message.chat_id = 1
    query.message.message_id = 10
    update = mock.Mock()
    update.callback_query = query

    simple_context.chat_data[1] = {"message_thread_id": None}
    simple_context.bot.editMessageReplyMarkup = mock.AsyncMock()
    query.answer = mock.AsyncMock()

    with mock.patch("teleapi.endpoints.send_text", mock.AsyncMock()) as send_text:
        res = await reset(update, simple_context)
    assert res == ConversationHandler.END
    send_text.assert_called_once()
