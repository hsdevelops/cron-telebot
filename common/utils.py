from datetime import datetime, timezone, timedelta
from croniter import croniter
import config


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


def get_value(entry, key):
    return entry.iloc[0][key]


def parse_time_mins(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%d %H:%M")


def parse_time_millis(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
