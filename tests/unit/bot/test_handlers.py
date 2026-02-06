from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import handlers


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_fallback_ends_conversation(send_msg, simple_update):
    res = await handlers.fallback(simple_update, mock.Mock())
    assert res == ConversationHandler.END
    send_msg.assert_called_once()
