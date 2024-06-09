import re
import config
from croniter import croniter
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List


def calc_next_run(crontab: str, user_tz_offset: float) -> Tuple[str, str]:
    user_tz = timezone(timedelta(hours=user_tz_offset))
    user_now = datetime.now(user_tz)
    user_iter = croniter(crontab, user_now)
    user_nextrun_datetime = user_iter.get_next(datetime)
    user_nextrun_ts = parse_time_mins(user_nextrun_datetime)

    db_tz = timezone(timedelta(hours=config.TZ_OFFSET))
    db_nextrun_datetime = user_nextrun_datetime.astimezone(tz=db_tz)
    db_nextrun_ts = parse_time_mins(db_nextrun_datetime)

    return (user_nextrun_ts, db_nextrun_ts)


def extract_tz_values(text: str) -> Optional[re.Match[str]]:
    return re.match("^(?:UTC)?(([+-])(1[0-4]|0[0-9]|[0-9])(?::([0-5][0-9]))?)$", text)


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


def calc_tz(tz_values: re.Match) -> Tuple[str, float]:
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


def now(offset: int = 0) -> str:
    now_ts = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    return parse_time_millis(now_ts + timedelta(minutes=offset))
