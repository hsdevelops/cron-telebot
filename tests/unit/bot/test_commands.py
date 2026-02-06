from unittest import mock

import pytest
from telegram import Update

from bot import commands


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_commands_handle_no_message(send_msg, simple_context):
    update = Update(update_id=1, message=None)

    await commands.help(update, simple_context)
    await commands.list_options(update, simple_context)
    await commands.option_restrict_to_admins(update, simple_context)
    await commands.option_restrict_to_user(update, simple_context)

    send_msg.assert_not_called()
