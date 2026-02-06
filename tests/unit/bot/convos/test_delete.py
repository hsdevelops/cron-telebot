from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.delete import command, remove_job
from tests.unit.conftest import mock_update


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=False))
@mock.patch("bot.replies.text")
async def test_delete_command_unauthorized(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_not_called()


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_delete_command_no_entries(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.simple_prompt_message)


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_delete_command_success(
    send_msg, simple_update, simple_context, mock_group
):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
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
@mock.patch("bot.replies.text")
async def test_delete_remove_missing(send_msg, simple_context):
    update = mock_update(text="missing")
    res = await remove_job(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(
        update, replies.missing_job_error_message % "missing"
    )


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_delete_remove_success(send_msg, simple_context):
    await simple_context.application.bot_data["mongo"].insert_new_entry(
        {
            "chat_id": 1,
            "jobname": "job",
            "created_by": 1,
            "created_ts": 1,
            "removed_ts": "",
        }
    )
    update = mock_update(text="job")
    res = await remove_job(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(update, replies.delete_success_message)
