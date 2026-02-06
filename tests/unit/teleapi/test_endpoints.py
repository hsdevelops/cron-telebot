import pytest

from teleapi import endpoints


@pytest.mark.asyncio
async def test_send_text_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return {"status": 200, "json": {"result": {"message_id": 1}}}

    monkeypatch.setattr(endpoints, "request", fake_request)

    await endpoints.send_text(
        http_session=None,
        chat_id=1,
        content="hi",
        user_bot_token="token",
        message_thread_id=None,
    )

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_send_single_photo_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return {"status": 200, "json": {"result": {"message_id": 1}}}

    monkeypatch.setattr(endpoints, "request", fake_request)

    await endpoints.send_single_photo(
        http_session=None,
        chat_id=1,
        photo_id="photo",
        content="cap",
        user_bot_token="token",
        message_thread_id=None,
    )

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_send_poll_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_request(session, url, **kwargs):
        seen["data"] = kwargs.get("data")
        return {"status": 200, "json": {"result": {"message_id": 1}}}

    monkeypatch.setattr(endpoints, "request", fake_request)

    await endpoints.send_poll(
        http_session=None,
        chat_id=1,
        content='{"question":"q","options":[{"text":"a"}]}',
        user_bot_token="token",
        message_thread_id=None,
    )

    assert "reply_to_message_id" not in seen["data"]


@pytest.mark.asyncio
async def test_send_media_group_omits_reply_to_message_id_when_none(monkeypatch):
    seen = {}

    async def fake_prepare_photos(session, photo_id, content):
        return "[]", {}, None

    async def fake_request(session, url, **kwargs):
        seen["url"] = url
        return {"status": 200, "json": {"result": []}}

    monkeypatch.setattr(endpoints, "prepare_photos", fake_prepare_photos)
    monkeypatch.setattr(endpoints, "request", fake_request)

    await endpoints.send_media_group(
        http_session=None,
        chat_id=1,
        photo_id="photo",
        content="cap",
        user_bot_token="token",
        message_thread_id=None,
    )

    assert "reply_to_message_id=" not in seen["url"]


@pytest.mark.asyncio
async def test_download_photo_handles_non_200(monkeypatch):
    async def fake_request(session, url, **kwargs):
        return {"status": 500, "json": None, "content": None}

    monkeypatch.setattr(endpoints, "request", fake_request)

    files, err = await endpoints.download_photo(
        http_session=None, files={}, photo_id="pid", bot_token="token"
    )
    assert files == {}
    assert err is not None
