import asyncio
from unittest import mock
import pytest
from telegram import CallbackQuery, Chat, Poll, User, Message, Update
from bot.actions.actions import *
from bot.actions.permissions import *
from tests.unit.conftest import mock_update


class Member:
    def __init__(self, restriction):
        self.status = restriction


@pytest.fixture
def mock_update_cb():
    chat = Chat(id=2, type="private")
    usr = User(id=1, first_name="hs", is_bot=False)
    msg = Message(date=1, chat=chat, message_id=1, from_user=usr)
    cb = CallbackQuery(id=1, from_user=usr, chat_instance="", message=msg)
    update = Update(message=None, callback_query=cb, update_id=1)
    yield update


@pytest.fixture
def mock_update_poll():
    poll = Poll(
        id=1,
        question="",
        options=list(),
        total_voter_count=0,
        is_closed=False,
        is_anonymous=False,
        type="REGULAR",
        allows_multiple_answers=True,
    )
    update = Update(message=None, update_id=1, poll=poll)
    yield update


@pytest.fixture
def mock_context_poll(simple_context):
    simple_context.bot_data[1] = 3
    yield simple_context


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_fix, context_fix, exp_chat_id",
    [
        ("simple_update", "simple_context", 1),
        ("mock_update_cb", "simple_context", 2),
        ("mock_update_poll", "mock_context_poll", 3),
    ],
)
async def test_get_chat_id(update_fix, context_fix, exp_chat_id, request):
    update = request.getfixturevalue(update_fix)
    context = request.getfixturevalue(context_fix)
    res = await get_chat_id(update, context)
    assert res == exp_chat_id


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_start_message")
@mock.patch("bot.actions.permissions.get_chat_id", mock.AsyncMock(return_value=1))
async def test_check_rights_missing_entry(
    send_msg, simple_update, simple_context, mongo_service
):
    await check_rights(simple_update, simple_context, mongo_service)
    res = send_msg.assert_called_once()
    assert res is None


@pytest.mark.asyncio
@mock.patch("bot.actions.permissions.get_chat_id", mock.AsyncMock(return_value=1))
async def test_check_rights_no_retrictions(
    simple_update, simple_context, mongo_service, mock_group
):
    mongo_service.insert_new_chat(mock_group)
    res = await check_rights(simple_update, simple_context, mongo_service)
    assert res is True


@pytest.mark.asyncio
@mock.patch("bot.replies.replies.send_user_unauthorized_error_message")
@mock.patch("bot.actions.permissions.get_chat_id", mock.AsyncMock(return_value=1))
async def test_check_rights_creator(
    send_401, simple_update, simple_context, mongo_service, mock_group
):
    mock_group["restriction"] = Restriction.OWNER.value
    mongo_service.insert_new_chat(mock_group)

    res = await check_rights(simple_update, simple_context, mongo_service)
    assert res is True

    res = await check_rights(mock_update(id=2), simple_context, mongo_service)
    assert res is False
    send_401.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "restriction, exp",
    [
        (Restriction.ADMIN.value, True),
        (Restriction.OWNER.value, True),
        ("", False),
    ],
)
@mock.patch("bot.replies.replies.send_user_unauthorized_error_message")
@mock.patch("bot.actions.permissions.get_chat_id", mock.AsyncMock(return_value=1))
async def test_check_rights_admin(
    send_401, restriction, exp, simple_update, simple_context, mongo_service, mock_group
):
    mock_group["restriction"] = Restriction.ADMIN.value
    mongo_service.insert_new_chat(mock_group)

    m = Member(restriction)
    simple_context.bot.get_chat_member = mock.AsyncMock(return_value=m)
    res = await check_rights(simple_update, simple_context, mongo_service)
    assert res is exp

    if res is False:
        send_401.assert_called_once()
