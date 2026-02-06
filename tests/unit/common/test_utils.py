from datetime import datetime, timezone

import pytest
from common import utils


@pytest.mark.parametrize(
    "string, exp_tz, exp_offset, exp_err",
    [
        ("+08:00", "UTC", 8, None),
        ("-14:00", "UTC", -14, "invalid offset -14.0"),
        ("-12:00", "UTC", -12, None),
        ("+0:00", "UTC", 0, None),
        ("0", "UTC", 0, None),
        ("-2", "UTC", -2, None),
        ("+14:00", "UTC", 14, None),
        ("UTC+14:30", "UTC", 14.5, "invalid offset 14.5"),
        ("UTC+3:30", "UTC", 3.5, None),
        ("UTC-04:00", "UTC", -4, None),
        ("UTC-0:30", "UTC", -0.5, None),
        ("UTC-12:30", "UTC", -12.5, "invalid offset -12.5"),
        ("UTC+00:30", "UTC", 0.5, None),
        ("UTC+05:45", "UTC", 5.75, None),
        ("UTC+9:15", "UTC", 9.25, None),
        ("UTC+13", "UTC", 13, None),
        ("8", "UTC", 8, None),
        ("8:00", "UTC", 8, None),
        ("09:30", "UTC", 9.5, None),
        ("+5:30", "UTC", 5.5, None),
        ("UTC+3:5", "UTC", 0, "no match"),
        ("15:00", "UTC", 0, "no match"),
        ("GMT+3", "UTC", 0, "no match"),
        ("Asia/Singapore", "Asia/Singapore", 0, None),
        ("Europe/London", "Europe/London", 0, None),
        ("Etc/UTC", "Etc/UTC", 0, None),
        ("UTC", "UTC", 0, None),
    ],
)
def test_extract_timezone(string, exp_tz, exp_offset, exp_err):
    utc_tz, tz_offset, err = utils.extract_timezone(string)
    assert utc_tz == exp_tz
    assert tz_offset == exp_offset
    assert err == exp_err


def test_extract_timezone_weird_string():
    utc_tz, tz_offset, err = utils.extract_timezone("weird!!!")
    assert utc_tz == "UTC"
    assert tz_offset == 0
    assert err == "no match"


def test_extract_jobs():
    text = """
    30 8 * * 1 Normal job
    30 8 * 2 Error
    30 8 * * 2,4,5 Multiple days
    Dummy
    * * * * * Every minute
    """

    res = utils.extract_jobs(text)
    assert len(res) == 5

    crontab, content = res[0]
    assert crontab == "30 8 * * 1"
    assert content == "Normal job"

    crontab, content = res[1]
    assert crontab == "30 8 * 2 Error"
    assert content == ""

    crontab, content = res[2]
    assert crontab == "30 8 * * 2,4,5"
    assert content == "Multiple days"

    crontab, content = res[3]
    assert crontab == "Dummy"
    assert content == ""

    crontab, content = res[4]
    assert crontab == "* * * * *"
    assert content == "Every minute"


@pytest.mark.parametrize(
    "crontab,user_timezone,user_tz_offset,exp_user_ts,exp_db_ts",
    [
        ("0 3 * * *", "UTC", 2, "2025-01-01 03:00", "2025-01-01 09:00"),
        ("* * * * *", "UTC", 0, "2025-01-01 00:31", "2025-01-01 08:31"),
    ],
)
def test_calc_next_run(
    monkeypatch, crontab, user_timezone, user_tz_offset, exp_user_ts, exp_db_ts
):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    monkeypatch.setattr(utils.config, "TZ_OFFSET", 8.0)

    user_ts, db_ts = utils.calc_next_run(crontab, user_timezone, user_tz_offset)

    assert user_ts == exp_user_ts
    assert db_ts == exp_db_ts


@pytest.mark.parametrize("crontab", ["* * * * * ? *"])
def test_calc_next_run_invalid_crontab(monkeypatch, crontab):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    monkeypatch.setattr(utils.config, "TZ_OFFSET", 8.0)

    with pytest.raises(Exception):
        utils.calc_next_run(crontab, "UTC", 0)


@pytest.mark.parametrize(
    "fixed_utc,timezone,crontab,exp_user_ts,exp_db_ts",
    [
        (
            datetime(2025, 6, 1, 0, 30, tzinfo=timezone.utc),
            "Europe/London",
            "0 3 * * *",
            "2025-06-01 03:00",
            "2025-06-01 10:00",
        ),
    ],
)
def test_calc_next_run_dst(
    monkeypatch, fixed_utc, timezone, crontab, exp_user_ts, exp_db_ts
):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_utc.replace(tzinfo=None)
            return fixed_utc.astimezone(tz)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    monkeypatch.setattr(utils.config, "TZ_OFFSET", 8.0)

    user_ts, db_ts = utils.calc_next_run(crontab, timezone, 0)

    assert user_ts == exp_user_ts
    assert db_ts == exp_db_ts


@pytest.mark.parametrize(
    "timezone_str, tz_offset, exp_format",
    [
        ("UTC", 5.5, "UTC+05:30"),
        ("Invalid/Zone", -3, "UTC-03:00"),
        ("Asia/Singapore", 0, "Asia/Singapore"),
        ("Europe/London", 0, "Europe/London"),
    ],
)
def test_format_timezone(timezone_str, tz_offset, exp_format):
    res = utils.format_timezone(timezone_str, tz_offset)
    assert res == exp_format
