import mongomock
import pytest

from database.mongo import MongoService

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mongo_service(mocker):
    client = mongomock.MongoClient()
    mocker.patch("database.mongo.MongoClient", return_value=client)
    yield MongoService()
