from unittest.mock import Mock
import pytest

from telegram import Chat, Update, User, Message


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
    obj = {}
    context = Mock()
    context.user_data.__setitem__ = Mock()
    context.user_data.__getitem__ = Mock()
    context.user_data.__setitem__.side_effect = obj.__setitem__
    context.user_data.__getitem__.side_effect = obj.__getitem__
    yield context
