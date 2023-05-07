from unittest.mock import Mock
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


@pytest.fixture
def simple_update():
    chat = Chat(id=1, type="private")
    usr = User(id=1, first_name="hs", is_bot=False)
    msg = Message(date=1, chat=chat, message_id=1, from_user=usr)
    update = Update(message=msg, update_id=1)
    yield update


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
    context = Mock()
    context.bot_data.__setitem__ = Mock()
    context.bot_data.__getitem__ = Mock()
    context.bot_data.__setitem__.side_effect = obj1.__setitem__
    context.bot_data.__getitem__.side_effect = obj1.__getitem__
    context.user_data.__setitem__ = Mock()
    context.user_data.__getitem__ = Mock()
    context.user_data.__setitem__.side_effect = obj2.__setitem__
    context.user_data.__getitem__.side_effect = obj2.__getitem__
    yield context
