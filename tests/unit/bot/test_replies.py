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


@pytest.mark.asyncio
async def test_text_handles_exception(simple_update, monkeypatch):
    async def boom(*_, **__):
        raise Exception("boom")

    monkeypatch.setattr(type(simple_update.message), "reply_text", boom)
    res = await replies.text(simple_update, "hi")
    assert res is None
