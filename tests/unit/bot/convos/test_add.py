from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.add import command, add_jobname, add_content, add_crontab
from common.enums import ContentType
from tests.unit.conftest import mock_update


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_command_missing_chat(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.prompt_start_message)


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_add_command_exceeds_limit(
    send_msg, simple_update, simple_context, mock_group
):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
    with mock.patch(
        "database.dbutils.dbutils.get_user_limit", mock.AsyncMock(return_value=(5, 5))
    ):
        res = await command(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_add_command_success(send_msg, simple_update, simple_context, mock_group):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
    with mock.patch(
        "database.dbutils.dbutils.get_user_limit", mock.AsyncMock(return_value=(0, 10))
    ):
        res = await command(simple_update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once_with(
        simple_update, replies.request_jobname_message, reply_markup=replies.force_reply
    )


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_jobname_duplicate(
    send_msg, simple_update, simple_context, mock_group
):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {"user_id": user_id}
    await simple_context.application.bot_data["mongo"].insert_new_entry(
        {
            "chat_id": simple_update.message.chat.id,
            "jobname": "dup",
            "created_by": user_id,
            "created_ts": 1,
            "removed_ts": "",
        }
    )
    update = mock_update(text="dup")
    res = await add_jobname(update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(update, replies.invalid_new_job_message)


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_content_text(send_msg, simple_update, simple_context):
    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {}
    update = mock_update(text="hello")
    res = await add_content(update, simple_context)
    assert res == convo.states.s2
    payload = simple_context.chat_data[user_id]
    assert payload["content_type"] == ContentType.TEXT.value
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_crontab_invalid(send_msg, simple_update, simple_context):
    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {
        "user_id": user_id,
        "jobname": "job",
        "content": "hi",
        "content_type": ContentType.TEXT.value,
        "utc_tz": "UTC",
        "tz_offset": 0,
    }
    with mock.patch("bot.convos.add.get_description", side_effect=Exception("bad")):
        res = await add_crontab(mock_update(text="bad"), simple_context)
    assert res is None
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_add_crontab_success(send_msg, simple_update, simple_context):
    user_id = simple_update.message.from_user.id
    simple_context.chat_data[user_id] = {
        "user_id": user_id,
        "jobname": "job",
        "content": "hi",
        "content_type": ContentType.TEXT.value,
        "utc_tz": "UTC",
        "tz_offset": 0,
    }
    with mock.patch(
        "bot.convos.add.get_description", return_value="every minute"
    ), mock.patch("common.utils.calc_next_run", return_value=("u", "d")), mock.patch(
        "database.dbutils.dbutils.add_new_entry",
        mock.AsyncMock(return_value=mock.Mock(inserted_id=1)),
    ):
        res = await add_crontab(mock_update(text="* * * * *"), simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once()
