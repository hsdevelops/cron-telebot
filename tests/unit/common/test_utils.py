import pytest
from common import utils


@pytest.mark.parametrize("string", ["8:00", "1", "+15:00", "-15:00"])
def test_extract_tz_values_invalid(string):
    res = utils.extract_tz_values(string)
    assert res is None


@pytest.mark.parametrize(
    "string, exp_tz, exp_offset",
    [
        ("+08:00", "+08:00", 8),
        ("-14:00", "-14:00", -14),
        ("+0:00", "+0:00", 0),
        ("-2", "-2", -2),
        ("UTC+3:30", "+3:30", 3.5),
        ("UTC-04:00", "-04:00", -4),
        ("UTC+13", "+13", 13),
    ],
)
def test_calc_tz(string, exp_tz, exp_offset):
    res = utils.extract_tz_values(string)
    assert res is not None

    utc_tz, tz_offset = utils.calc_tz(res)
    assert utc_tz == exp_tz
    assert tz_offset == exp_offset


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
