from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.edit import (
    command,
    choose_job,
    choose_attribute,
    handle_edit_content,
    attr_jobname,
)
from tests.unit.conftest import mock_update


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_edit_command_no_entries(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.simple_prompt_message)


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_edit_command_success(send_msg, simple_update, simple_context):
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
async def test_edit_choose_job_invalid(send_msg, simple_context):
    update = mock_update(text="missing")
    res = await choose_job(update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once_with(update, replies.error_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_edit_choose_attribute_invalid(send_msg, simple_update, simple_context):
    simple_context.user_data["attribute"] = "bad"
    res = await choose_attribute(simple_update, simple_context)
    assert res == convo.states.s1
    send_msg.assert_called_once_with(simple_update, replies.error_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_edit_handle_edit_content_jobname_duplicate(
    send_msg, simple_context, mock_group
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
    await simple_context.application.bot_data["mongo"].insert_new_entry(
        {
            "chat_id": 1,
            "jobname": "dup",
            "created_by": 1,
            "created_ts": 2,
            "removed_ts": "",
        }
    )
    simple_context.user_data["jobname"] = "job"
    simple_context.user_data["attribute"] = attr_jobname
    update = mock_update(text="dup")
    res = await handle_edit_content(update, simple_context)
    assert res == convo.states.s2
    send_msg.assert_called_once_with(
        update, replies.invalid_new_jobname_message, reply_markup=replies.force_reply
    )
