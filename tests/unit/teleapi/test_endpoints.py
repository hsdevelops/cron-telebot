import pytest

from teleapi import endpoints
from teleapi.requests import RequestResponse
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_send_text_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return RequestResponse(status=200, json={"result": {"message_id": 1}})

    monkeypatch.setattr(endpoints, "request", fake_request)

    resp, err = await endpoints.send_text(
        http_session=None,
        chat_id=1,
        content="hi",
        user_bot_token="token",
        message_thread_id=None,
    )
    assert err is None

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_send_single_photo_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return RequestResponse(status=200, json={"result": {"message_id": 1}})

    monkeypatch.setattr(endpoints, "request", fake_request)

    resp, err = await endpoints.send_single_photo(
        http_session=None,
        chat_id=1,
        photo_id="photo",
        content="cap",
        user_bot_token="token",
        message_thread_id=None,
    )
    assert err is None

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_send_poll_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["data"] = kwargs.get("data")
        return RequestResponse(status=200, json={"result": {"message_id": 1}})

    monkeypatch.setattr(endpoints, "request", fake_request)

    resp, err = await endpoints.send_poll(
        http_session=None,
        chat_id=1,
        content='{"question":"q","options":[{"text":"a"}]}',
        user_bot_token="token",
        message_thread_id=None,
    )
    assert err is None

    assert "reply_to_message_id" not in seen["data"]


@pytest.mark.asyncio
async def test_send_media_group_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_prepare_photos(session, photo_id, content):
        return "[]", {}, None

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return RequestResponse(status=200, json={"result": []})

    monkeypatch.setattr(endpoints, "prepare_photos", fake_prepare_photos)
    monkeypatch.setattr(endpoints, "request", fake_request)

    resp, err = await endpoints.send_media_group(
        http_session=None,
        chat_id=1,
        photo_id="photo",
        content="cap",
        user_bot_token="token",
        message_thread_id=None,
    )
    assert err is None

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_download_photo_handles_non_200(monkeypatch):
    async def fake_request(session, url, **kwargs):
        return RequestResponse(status=500, json=None, content=None)

    monkeypatch.setattr(endpoints, "request", fake_request)

    files, err = await endpoints.download_photo(
        http_session=None, files={}, photo_id="pid", bot_token="token"
    )
    assert files == {}
    assert err is not None


@pytest.mark.asyncio
async def test_transfer_photo_between_bots_success(monkeypatch):
    async def fake_send_single_photo_local(*_args, **_kwargs):
        return (
            RequestResponse(
                status=200,
                json={"result": {"photo": [{"file_id": "new"}], "message_id": 1}},
            ),
            None,
        )

    async def fake_update_entry_by_jobid(*_args, **_kwargs):
        return SimpleNamespace(modified_count=1)

    async def fake_delete_message(*_args, **_kwargs):
        return True

    monkeypatch.setattr(
        endpoints, "send_single_photo_local", fake_send_single_photo_local
    )
    monkeypatch.setattr(
        endpoints.dbutils, "update_entry_by_jobid", fake_update_entry_by_jobid
    )
    monkeypatch.setattr(endpoints, "delete_message", fake_delete_message)

    new_photo_id, err = await endpoints.transfer_photo_between_bots(
        http_session=None,
        db_service=None,
        new_token="t",
        prev_token="p",
        chat_id=1,
        photo_id="old",
        job_id="job",
    )
    assert err is None
    assert new_photo_id == "new"


@pytest.mark.asyncio
async def test_transfer_photo_between_bots_error(monkeypatch):
    async def fake_send_single_photo_local(*_args, **_kwargs):
        return RequestResponse(status=None), "boom"

    monkeypatch.setattr(
        endpoints, "send_single_photo_local", fake_send_single_photo_local
    )

    new_photo_id, err = await endpoints.transfer_photo_between_bots(
        http_session=None,
        db_service=None,
        new_token="t",
        prev_token="p",
        chat_id=1,
        photo_id="old",
        job_id="job",
    )
    assert new_photo_id is None
    assert err == "boom"
