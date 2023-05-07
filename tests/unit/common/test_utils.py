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
