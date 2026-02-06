from unittest import mock

import pytest
from telegram.ext import ConversationHandler

from bot import replies
from bot.convos import convo
from bot.convos.addmultiple import command, add_jobs
from common.enums import ContentType


@pytest.mark.asyncio
@mock.patch("bot.replies.text")
async def test_addmultiple_command(send_msg, simple_update, simple_context):
    res = await command(simple_update, simple_context)
    assert res == convo.states.s0
    send_msg.assert_called_once_with(
        simple_update, replies.request_jobs_message, reply_markup=replies.force_reply
    )


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=False))
@mock.patch("bot.replies.text")
async def test_addmultiple_unauthorized(send_msg, simple_update, simple_context):
    res = await add_jobs(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_not_called()


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_addmultiple_success(
    send_msg, simple_update, simple_context, mongo_service, mock_group
):
    await mongo_service.insert_new_chat(mock_group)
    jobs = [("0 * * * *", "hi"), ("5 * * * *", "yo")]
    with mock.patch("common.utils.extract_jobs", return_value=jobs), mock.patch(
        "common.utils.calc_next_run", return_value=("u", "d")
    ), mock.patch(
        "bot.convos.addforwarded.generate_jobname",
        mock.AsyncMock(side_effect=["job1", "job2"]),
    ), mock.patch(
        "database.dbutils.dbutils.add_new_entry",
        mock.AsyncMock(return_value=mock.Mock(inserted_id=1)),
    ):
        res = await add_jobs(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once()


@pytest.mark.asyncio
@mock.patch("bot.convos.permissions.check_rights", mock.AsyncMock(return_value=True))
@mock.patch("bot.replies.text")
async def test_addmultiple_none_created(
    send_msg, simple_update, simple_context, mock_group
):
    await simple_context.application.bot_data["mongo"].insert_new_chat(mock_group)
    jobs = [("0 * * * *", "hi")]
    with mock.patch("common.utils.extract_jobs", return_value=jobs), mock.patch(
        "common.utils.calc_next_run", side_effect=Exception("bad")
    ):
        res = await add_jobs(simple_update, simple_context)
    assert res == ConversationHandler.END
    send_msg.assert_called_once_with(simple_update, replies.error_message)
