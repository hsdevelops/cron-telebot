from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import api
from teleapi.requests import RequestResponse


def test_home():
    assert api.home() == "Hello world!"


def test_prom_endpoint():
    res = api.prom_endpoint()
    assert res.media_type == "text/plain"


@pytest.mark.asyncio
async def test_run_no_entries(monkeypatch):
    async def fake_find_entries(*_):
        return []

    monkeypatch.setattr(api.dbutils, "find_entries_by_nextrun", fake_find_entries)
    monkeypatch.setattr(api.config, "INFLUXDB_TOKEN", "")

    dummy_state = SimpleNamespace(mongo=None, http_session=None, influx=None)
    dummy_app = SimpleNamespace(state=dummy_state)
    dummy_request = SimpleNamespace(app=dummy_app)

    res = await api.run(dummy_request)
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_process_job_error_path(monkeypatch):
    updates = []
    notify = AsyncMock()

    async def fake_update_entry_by_jobname(db, entry, payload, q=None):
        updates.append(payload)
        return SimpleNamespace(modified_count=1)

    async def fake_send_message(*_):
        return "", "boom"

    monkeypatch.setattr(
        api.dbutils, "update_entry_by_jobname", fake_update_entry_by_jobname
    )
    monkeypatch.setattr(api, "send_message", fake_send_message)
    monkeypatch.setattr(api, "notify_job_deleted", notify)
    monkeypatch.setattr(api.utils, "now", lambda *_, **__: "now")
    monkeypatch.setattr(api.config, "RETRIES", 1)

    entry = {
        "_id": 1,
        "chat_id": 1,
        "content": "c",
        "content_type": "text",
        "photo_id": "",
        "photo_group_id": "",
        "crontab": "* * * * *",
        "previous_message_id": "123",
        "message_thread_id": None,
        "nextrun_ts": "",
        "user_nextrun_ts": "",
        "errors": [],
        "option_delete_previous": "",
        "user_bot_token": "t",
    }

    await api.process_job(db_service=None, http_session=None, entry=entry)

    assert len(updates) == 2
    final_payload = updates[-1]
    assert final_payload["previous_message_id"] == "123"
    assert len(final_payload["errors"]) == 1
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_job_notifies_creator_when_deleted(monkeypatch):
    updates = []
    notify = AsyncMock()

    async def fake_update_entry_by_jobname(db, entry, payload, q=None):
        updates.append(payload)
        return SimpleNamespace(modified_count=1)

    async def fake_send_message(*_):
        return "", "boom"

    monkeypatch.setattr(
        api.dbutils, "update_entry_by_jobname", fake_update_entry_by_jobname
    )
    monkeypatch.setattr(api, "send_message", fake_send_message)
    monkeypatch.setattr(api, "notify_job_deleted", notify)
    monkeypatch.setattr(api.utils, "now", lambda *_, **__: "now")
    monkeypatch.setattr(api.config, "RETRIES", 1)

    entry = {
        "_id": 1,
        "chat_id": 1,
        "created_by": 99,
        "jobname": "job",
        "content": "c",
        "content_type": "text",
        "photo_id": "",
        "photo_group_id": "",
        "crontab": "* * * * *",
        "previous_message_id": "123",
        "message_thread_id": None,
        "nextrun_ts": "",
        "user_nextrun_ts": "",
        "errors": [{"error": "earlier", "timestamp": "before"}],
        "option_delete_previous": "",
        "user_bot_token": "t",
    }

    await api.process_job(db_service=None, http_session=None, entry=entry)

    assert len(updates) == 2
    final_payload = updates[-1]
    assert final_payload["removed_ts"] == "now"
    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_job_deleted_logs_but_does_not_raise(monkeypatch):
    warnings = []

    async def fake_send_text(*_):
        return (
            RequestResponse(status=500, json=None, content=None, error="dm failed"),
            "dm failed",
        )

    monkeypatch.setattr(api.teleapi, "send_text", fake_send_text)
    monkeypatch.setattr(api.log.logger, "warning", lambda msg: warnings.append(msg))

    await api.notify_job_deleted(
        http_session=None,
        entry={"_id": 1, "created_by": 7, "jobname": "job", "chat_id": 1},
        errors=[{"error": "boom", "timestamp": "now"}],
        user_bot_token="token",
    )

    assert any(
        "Failed to notify deleted job creator" in warning for warning in warnings
    )


@pytest.mark.asyncio
async def test_notify_job_deleted_sends_dm_to_creator(monkeypatch):
    captured = {}

    async def fake_send_text(
        http_session, chat_id, content, user_bot_token, message_thread_id
    ):
        captured["chat_id"] = chat_id
        captured["content"] = content
        captured["user_bot_token"] = user_bot_token
        captured["message_thread_id"] = message_thread_id
        return RequestResponse(status=200, json={"ok": True}), None

    monkeypatch.setattr(api.teleapi, "send_text", fake_send_text)

    await api.notify_job_deleted(
        http_session=None,
        entry={
            "_id": 1,
            "created_by": 42,
            "jobname": "job",
            "chat_id": 9,
            "crontab": "* * * * *",
            "content": "hello",
            "content_type": "text",
        },
        errors=[{"error": "boom", "timestamp": "now"}],
        user_bot_token="token",
    )

    assert captured["chat_id"] == 42
    assert "jobname: job" in captured["content"]
    assert "crontab: * * * * *" in captured["content"]
    assert "content:\nhello" in captured["content"]
    assert captured["user_bot_token"] == "token"
    assert captured["message_thread_id"] is None


@pytest.mark.asyncio
async def test_notify_job_deleted_missing_creator_logs_warning(monkeypatch):
    warnings = []
    send_text = AsyncMock()

    monkeypatch.setattr(api.teleapi, "send_text", send_text)
    monkeypatch.setattr(api.log.logger, "warning", lambda msg: warnings.append(msg))

    await api.notify_job_deleted(
        http_session=None,
        entry={"_id": 1, "jobname": "job", "chat_id": 1},
        errors=[],
        user_bot_token="token",
    )

    send_text.assert_not_awaited()
    assert any("missing created_by" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_send_message_non_200_returns_error(monkeypatch):
    async def fake_send_text(*_):
        return RequestResponse(status=400, json={"description": "bad"}), None

    monkeypatch.setattr(api.teleapi, "send_text", fake_send_text)

    message_id, err = await api.send_message(
        http_session=None,
        job_id=1,
        chat_id=1,
        content="c",
        content_type="text",
        photo_id="",
        photo_group_id="",
        user_bot_token="t",
        message_thread_id=None,
    )

    assert message_id == ""
    assert "Error 400: bad" == err
