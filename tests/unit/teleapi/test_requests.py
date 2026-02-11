from unittest import mock

import pytest

from teleapi import requests as tele_requests


class DummyResponse:
    def __init__(self):
        self.status = 200
        self.headers = {"Content-Type": "application/json"}

    async def json(self):
        return {"ok": True}

    async def read(self):
        return b"data"


class DummyRequestCtx:
    async def __aenter__(self):
        return DummyResponse()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def request(self, method, url, **kwargs):
        return DummyRequestCtx()


@pytest.mark.asyncio
async def test_request_closes_files():
    file_obj = mock.Mock()
    file_obj.name = "x"
    session = DummySession()

    await tele_requests.request(session, "http://example.com", files={"f": file_obj})

    file_obj.close.assert_called_once()


class DummyError(Exception):
    def __init__(self, status):
        super().__init__("boom")
        self.status = status


class DummyErrorCtx:
    async def __aenter__(self):
        raise DummyError(418)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyErrorSession:
    def request(self, method, url, **kwargs):
        return DummyErrorCtx()


@pytest.mark.asyncio
async def test_request_includes_status_in_error():
    session = DummyErrorSession()

    resp = await tele_requests.request(session, "http://example.com")

    assert resp.error is not None
    assert "DummyError" in resp.error
    assert resp.status == 418
