import re
import config
from croniter import croniter
from datetime import datetime, timezone, timedelta


def calc_next_run(crontab, user_tz_offset):
    user_tz = timezone(timedelta(hours=user_tz_offset))
    user_now = datetime.now(user_tz)
    user_iter = croniter(crontab, user_now)
    user_nextrun_datetime = user_iter.get_next(datetime)
    user_nextrun_ts = parse_time_mins(user_nextrun_datetime)

    db_tz = timezone(timedelta(hours=config.TZ_OFFSET))
    db_nextrun_datetime = user_nextrun_datetime.astimezone(tz=db_tz)
    db_nextrun_ts = parse_time_mins(db_nextrun_datetime)

    return (user_nextrun_ts, db_nextrun_ts)


def extract_tz_values(text):
    return re.match("^(?:UTC)?(([+-])(1[0-4]|0[0-9]|[0-9])(?::([0-5][0-9]))?)$", text)


def extract_jobs(text):
    rx_seq = re.compile(
        r"""(
            (?:\*|[0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])\s    # Year
            (?:\*|[0-9]|1[0-9]|2[0-3])\s                         # Month
            (?:\*|[1-9]|1[0-9]|2[0-9]|3[0-1])\s                  # Day
            (?:\*|[1-9]|1[0-2])\s                                # Hour
            (?:\*|[0-6](?:,\s*[0-6])*)                           # Weekday
        )\s(.*)(?:\n)?""",
        re.MULTILINE | re.VERBOSE,
    )
    return re.findall(rx_seq, text)


def calc_tz(tz_values):
    match_groups = tz_values.groups()
    utc_tz = str(match_groups[0])
    sign = match_groups[1]
    hour = int(match_groups[2])
    mins = 0 if match_groups[3] is None else int(match_groups[3])

    tz_offset = float("%s%.2f" % (sign, hour + mins / 60))
    return (utc_tz, tz_offset)


def parse_time_mins(datetime_obj: datetime) -> str:
    return datetime_obj.strftime("%Y-%m-%d %H:%M")


def parse_time_millis(datetime_obj: datetime) -> str:
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")


def now():
    return parse_time_millis(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
