from unittest import mock

import pytest

from bot import replies
from common.enums import ContentType


def test_keyboard_from_dict_pairs():
    entries = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    keyboard = replies.keyboard_from_dict(entries, "name")
    assert [b.text for b in keyboard.keyboard[0]] == ["a", "b"]
    assert [b.text for b in keyboard.keyboard[1]] == ["c"]


def test_format_job_detail_poll():
    entry = {
        "jobname": "j",
        "crontab": "* * * * *",
        "content": '{"question":"q"}',
        "content_type": ContentType.POLL.value,
        "photo_id": "",
        "channel_id": "",
        "user_nextrun_ts": "t",
        "option_delete_previous": "",
    }
    text = replies.format_job_detail(entry, "@bot")
    assert "(Poll) q" in text


def test_format_exceed_limit_reply_variants():
    msg = replies.format_exceed_limit_reply(replies.JOB_LIMIT_PER_PERSON)
    assert "Recurring Messages currently only supports" in msg

    msg_blacklisted = replies.format_exceed_limit_reply(
        replies.JOB_LIMIT_PER_PERSON - 1
    )
    assert "blacklisted" in msg_blacklisted

    msg_increased = replies.format_exceed_limit_reply(replies.JOB_LIMIT_PER_PERSON + 1)
    assert "increased your limit" in msg_increased


def test_format_deleted_job_message_includes_core_job_details():
    message = replies.format_deleted_job_message(
        entry={
            "jobname": "daily-report",
            "chat_id": 123,
            "channel_id": "",
            "crontab": "0 9 * * *",
            "content": "send status update",
            "content_type": "text",
            "photo_id": "",
            "photo_group_id": "",
            "message_thread_id": 77,
            "option_delete_previous": True,
        },
        retry_count=1,
        errors=[{"error": "Error 400: bad request", "timestamp": "now"}],
    )

    assert "failed more than 1 time(s)" in message
    assert "daily-report" in message
    assert "0 9 * * *" in message
    assert "send status update" in message
    assert "message_thread_id: 77" in message
    assert "latest_error: Error 400: bad request" in message
    assert message.startswith("<pre>")
    assert message.endswith("</pre>")


def test_format_deleted_job_message_escapes_html_content():
    message = replies.format_deleted_job_message(
        entry={
            "jobname": "job",
            "chat_id": 1,
            "crontab": "* * * * *",
            "content": "<b>danger</b>",
            "content_type": "text",
        },
        retry_count=2,
        errors=[],
    )

    assert "<b>danger</b>" not in message
    assert "&lt;b&gt;danger&lt;/b&gt;" in message


@pytest.mark.asyncio
async def test_text_handles_exception(simple_update, monkeypatch):
    async def boom(*_, **__):
        raise Exception("boom")

    monkeypatch.setattr(type(simple_update.effective_message), "reply_text", boom)
    res = await replies.text(simple_update, "hi")
    assert res is None


@pytest.mark.asyncio
async def test_text_no_effective_message():
    update = mock.Mock()
    update.effective_message = None
    res = await replies.text(update, "hi")
    assert res is None
