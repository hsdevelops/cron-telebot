from unittest import mock
import pytest

from telegram import Chat, Update, User, Message


@pytest.fixture
def mock_private():
    return {
        "chat_id": 1,
        "chat_title": "",
        "chat_type": "private",
        "tz_offset": 8,
        "utc_tz": 8,
        "created_by": 1,
        "telegram_ts": 1,
        "restriction": "",
    }


@pytest.fixture
def mock_group():
    return {
        "chat_id": 1,
        "chat_title": "test_group",
        "chat_type": "group",
        "tz_offset": 8,
        "utc_tz": 8,
        "created_by": 1,
        "telegram_ts": 1,
        "restriction": "",
    }


@pytest.fixture
def mock_channel():
    return {
        "chat_id": 2,
        "chat_title": "test_channel",
        "chat_type": "channel",
        "tz_offset": 8,
        "utc_tz": 8,
        "created_by": 1,
        "telegram_ts": 1,
        "restriction": "",
    }


def mock_update(text=None, id=1):
    chat = Chat(id=1, type="private")
    usr = User(id=id, first_name="hs", is_bot=False)
    msg = Message(date=id, chat=chat, message_id=id, from_user=usr, text=text)
    update = Update(message=msg, update_id=id)
    return update


@pytest.fixture
def simple_update():
    yield mock_update()


@pytest.fixture
def simple_group_update():
    chat = Chat(id=1, type="group")
    usr = User(id=1, first_name="hs", is_bot=False)
    msg = Message(date=1, chat=chat, message_id=1, from_user=usr)
    update = Update(message=msg, update_id=1)
    yield update


@pytest.fixture
def simple_context():
    obj1, obj2 = {}, {}
    context = mock.Mock()
    context.bot_data.__setitem__ = mock.Mock()
    context.bot_data.__getitem__ = mock.Mock()
    context.bot_data.__setitem__.side_effect = obj1.__setitem__
    context.bot_data.__getitem__.side_effect = obj1.__getitem__
    context.user_data.__setitem__ = mock.Mock()
    context.user_data.__getitem__ = mock.Mock()
    context.user_data.__setitem__.side_effect = obj2.__setitem__
    context.user_data.__getitem__.side_effect = obj2.__getitem__
    context.bot.get_chat_member = mock.AsyncMock()
    yield context
