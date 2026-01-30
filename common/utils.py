import re
import config
from croniter import croniter
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def calc_next_run(
    crontab: str, user_timezone: str, user_tz_offset: float
) -> Tuple[str, str]:
    user_tz = None
    if user_timezone:
        try:
            user_tz = ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            user_tz = None

    if user_tz is None or (user_timezone == "UTC" and user_tz_offset != 0):
        user_tz = timezone(timedelta(hours=user_tz_offset))

    user_now = datetime.now(user_tz)
    user_iter = croniter(crontab, user_now)
    user_nextrun_datetime = user_iter.get_next(datetime)
    if user_nextrun_datetime.tzinfo is None:
        user_nextrun_datetime = user_nextrun_datetime.replace(tzinfo=user_tz)
    user_nextrun_ts = parse_time_mins(user_nextrun_datetime)

    db_tz = timezone(timedelta(hours=config.TZ_OFFSET))
    db_nextrun_datetime = user_nextrun_datetime.astimezone(tz=db_tz)
    db_nextrun_ts = parse_time_mins(db_nextrun_datetime)

    return (user_nextrun_ts, db_nextrun_ts)


def format_timezone(timezone: str, display_offset: float) -> str:
    if timezone != "UTC":
        try:
            tzinfo = ZoneInfo(timezone)
            return tzinfo.key
        except ZoneInfoNotFoundError:
            pass

    sign = "+" if display_offset >= 0 else "-"
    offset_abs = abs(display_offset)
    hours = int(offset_abs)
    mins = int(round((offset_abs - hours) * 60))
    if mins == 60:
        hours += 1
        mins = 0
    return f"UTC{sign}{hours:02d}:{mins:02d}"


def extract_jobs(text: str) -> List[Tuple[str, str]]:
    lines = text.split("\n")
    res = []
    for line in lines:
        words = line.strip().split()
        if len(words) == 0:
            continue
        crontab = " ".join(words[:5])
        content = " ".join(words[5:])
        res.append((crontab, content))
    return res


def extract_timezone(text: str) -> Tuple[str, float, Optional[str]]:
    try:
        tzinfo = ZoneInfo(text)
        return (tzinfo.key, 0, None)
    except ZoneInfoNotFoundError:
        pass

    tz_values = re.match(
        "^(?:UTC)?(([+-])?(1[0-4]|0[0-9]|[0-9])(?::([0-5][0-9]))?)$", text
    )
    if not tz_values:
        return ("UTC", 0, "no match")

    match_groups = tz_values.groups()
    sign = match_groups[1]
    if sign is None:
        sign = "+"
    hour = int(match_groups[2])
    mins = 0 if match_groups[3] is None else int(match_groups[3])
    offset = float("%s%.2f" % (sign, hour + mins / 60))

    if offset < -12 or offset > 14:
        return ("UTC", offset, f"invalid offset {offset}")

    return ("UTC", offset, None)


def parse_time_mins(datetime_obj: datetime) -> str:
    return datetime_obj.strftime("%Y-%m-%d %H:%M")


def parse_time_millis(datetime_obj: datetime) -> str:
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")


def now(offset: int = 0) -> str:
    now_ts = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    return parse_time_millis(now_ts + timedelta(minutes=offset))
