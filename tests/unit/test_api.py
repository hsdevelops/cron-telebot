from types import SimpleNamespace

import pytest

import api


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

    async def fake_update_entry_by_jobname(db, entry, payload, q=None):
        updates.append(payload)
        return SimpleNamespace(modified_count=1)

    async def fake_send_message(*_):
        return "", "boom"

    monkeypatch.setattr(
        api.dbutils, "update_entry_by_jobname", fake_update_entry_by_jobname
    )
    monkeypatch.setattr(api, "send_message", fake_send_message)
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


@pytest.mark.asyncio
async def test_send_message_non_200_returns_error(monkeypatch):
    async def fake_send_text(*_):
        return {"status": 400, "json": {"description": "bad"}}

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
