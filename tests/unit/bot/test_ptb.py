from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from bot import ptb


class FakeBot:
    def __init__(self):
        self.deleted = False
        self.webhook_set = None

    async def deleteWebhook(self, drop_pending_updates=False):
        self.deleted = True

    async def setWebhook(self, url):
        self.webhook_set = url


class FakeUpdater:
    async def start_polling(self, drop_pending_updates=False):
        return None

    async def stop(self):
        return None


class FakePTB:
    def __init__(self):
        self.bot = FakeBot()
        self.bot_data = {}
        self.updater = FakeUpdater()
        self.handlers = []
        self.error_handlers = []
        self.started = False
        self.stopped = False
        self.shutdown_called = False

    async def initialize(self):
        return None

    def add_handler(self, handler):
        self.handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def shutdown(self):
        self.shutdown_called = True


class FakeBuilder:
    def token(self, _):
        return self

    def read_timeout(self, _):
        return self

    def get_updates_read_timeout(self, _):
        return self

    def build(self):
        return FakePTB()


class FakeSession:
    def __init__(self, *_, **__):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeInflux:
    def __init__(self, *_, **__):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_lifespan_webhook_path(monkeypatch):
    monkeypatch.setattr(ptb, "InfluxDBClient3", FakeInflux)
    monkeypatch.setattr(
        ptb,
        "aiohttp",
        SimpleNamespace(ClientSession=FakeSession, ClientTimeout=lambda total: None),
    )
    monkeypatch.setattr(
        ptb, "Application", SimpleNamespace(builder=lambda: FakeBuilder())
    )
    monkeypatch.setattr(
        ptb.mongo, "MongoService", lambda *_: SimpleNamespace(disconnect=lambda: None)
    )
    monkeypatch.setattr(ptb.config, "BOTHOST", "https://example.com")

    app = FastAPI()
    async with ptb.lifespan(app):
        assert app.state.ptb.bot.deleted is True
        assert app.state.ptb.bot.webhook_set == "https://example.com"

    assert app.state.ptb.shutdown_called is True
