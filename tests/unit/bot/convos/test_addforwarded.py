from unittest import mock
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.addforwarded import add_job
from common.enums import ContentType


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_forwarded_missing_forward(send_msg, simple_context):
    update = mock.Mock()
    update.message = mock.Mock()
    update.message.forward_from_chat = None
    update.message.chat.type = "private"
    res = await add_job(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_not_called()


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_forwarded_missing_timezone(send_msg, simple_context):
    update = mock.Mock()
    update.message = mock.Mock()
    update.message.forward_from_chat = SimpleNamespace(
        id=2, title="chan", type="channel"
    )
    update.message.chat.type = "private"
    update.message.chat.id = 1
    update.message.from_user.id = 1
    res = await add_job(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(update, replies.prompt_start_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_forwarded_success(
    send_msg, mongo_service, simple_context, mock_private
):
    await mongo_service.insert_new_chat(mock_private)
    update = mock.Mock()
    update.message = mock.Mock()
    update.message.forward_from_chat = SimpleNamespace(
        id=2, title="chan", type="channel"
    )
    update.message.chat.type = "private"
    update.message.chat.id = 1
    update.message.from_user.id = 1
    update.message.date = datetime.now(timezone.utc)
    update.message.poll = None
    update.message.photo = None
    update.message.text = "hello"
    update.message.text_html = "hello"
    with mock.patch(
        "database.dbutils.dbutils.get_user_limit", mock.AsyncMock(return_value=(0, 10))
    ), mock.patch(
        "bot.convos.addforwarded.generate_jobname",
        mock.AsyncMock(return_value="chan (1)"),
    ):
        res = await add_job(update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once()
    payload = simple_context.chat_data[1]
    assert payload["content_type"] == ContentType.TEXT.value
