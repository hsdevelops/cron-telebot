from mongomock_motor import AsyncMongoMockClient
import pytest

import config
from database.mongo import MongoService


@pytest.fixture
def mongo_service():
    client = AsyncMongoMockClient()
    db = client[config.MONGODB_DB]

    svc = MongoService.__new__(MongoService)
    svc.main_collection = db[config.MONGODB_JOB_DATA_COLLECTION]
    svc.chat_data_collection = db[config.MONGODB_CHAT_DATA_COLLECTION]
    svc.user_data_collection = db[config.MONGODB_USER_DATA_COLLECTION]
    svc.bot_data_collection = db[config.MONGODB_BOT_DATA_COLLECTION]
    svc.user_whitelist_collection = db[config.MONGODB_USER_WHITELIST_COLLECTION]

    return svc
