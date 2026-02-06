from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.list import command, show_job_details
from tests.unit.conftest import mock_update


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_list_command_no_entries(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.simple_prompt_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_list_command_success(send_msg, simple_update, simple_context):
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
async def test_list_missing_job(send_msg, simple_context):
    update = mock_update(text="missing")
    res = await show_job_details(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(
        update, replies.missing_job_error_message % "missing"
    )


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_list_show_job_details(send_msg, simple_context):
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
    res = await show_job_details(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once()
