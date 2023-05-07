import pytest
from bot.commands import change_tz
from unittest import mock


@pytest.mark.usefixtures("mongo_service")
@mock.patch("bot.replies.replies.send_start_message")
def test_change_tz_missing_chat(send_msg, simple_update, simple_context):
    change_tz(simple_update, simple_context)
    send_msg.assert_called_once()


@mock.patch("telegram.Message.reply_text")
@mock.patch("bot.actions.permissions.check_rights", mock.MagicMock(return_value=False))
def test_change_tz_unauthorized(
    reply, mongo_service, simple_update, simple_context, mock_group
):
    mongo_service.insert_new_chat(mock_group)
    change_tz(simple_update, simple_context)
    assert not reply.called


@mock.patch("bot.replies.replies.send_change_timezone_message")
@mock.patch("bot.actions.permissions.check_rights", mock.MagicMock(return_value=True))
def test_change_tz(send_msg, mongo_service, simple_update, simple_context, mock_group):
    mongo_service.insert_new_chat(mock_group)
    change_tz(simple_update, simple_context)
    send_msg.assert_called_once()
