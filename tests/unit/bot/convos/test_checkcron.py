from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.checkcron import command, decrypt_cron
from tests.unit.conftest import mock_update


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_checkcron_command(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once_with(
        simple_update, replies.checkcron_message, reply_markup=replies.force_reply
    )


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_checkcron_invalid(send_msg, simple_update):
    with mock.patch(
        "bot.convos.checkcron.get_description", side_effect=Exception("bad")
    ):
        res = await decrypt_cron(mock_update(text="bad"), simple_update)
    assert res is None
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_checkcron_valid(send_msg, simple_update):
    with mock.patch(
        "bot.convos.checkcron.get_description", return_value="every minute"
    ):
        res = await decrypt_cron(mock_update(text="* * * * *"), simple_update)
    assert res == ConversationHandler.END
    send_msg.assert_called_once()
