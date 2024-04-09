import re
import config
from croniter import croniter
from datetime import datetime, timezone, timedelta
from telegram import Update, Message, MaybeInaccessibleMessage
from typing import Optional, Union


def get_user_id_from_update(update: Update) -> Optional[int]:
    message = update.message
    if message is None:
        return None

    from_user = message.from_user
    if from_user is None:
        return None
    return from_user.id


def get_chat_id_from_update(update: Update) -> Optional[int]:
    message = update.message
    if message is None:
        return None

    return message.chat.id


def get_msg_text_from_update(update: Update) -> Optional[str]:
    message = update.message
    if message is None:
        return None

    return message.text


def get_chat_type_from_update(update: Update) -> Optional[str]:
    message = update.message
    if message is None:
        return None

    return message.chat.type


def get_text_html_from_update(update: Update) -> Optional[str]:
    message = update.message
    if message is None:
        return None

    return message.text_html


def get_poll_type_from_update(update: Update) -> Optional[str]:
    message = update.message
    if message is None:
        return None

    poll = message.poll
    if poll is None:
        return None

    return poll.type


def get_message_from_update(update: Update) -> Optional[MaybeInaccessibleMessage]:
    if update.callback_query is None:
        return None
    return update.callback_query.message


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


def extract_tz_values(text: Optional[str]):
    if text is None:
        return None
    return re.match("^(?:UTC)?(([+-])(1[0-4]|0[0-9]|[0-9])(?::([0-5][0-9]))?)$", text)


def extract_jobs(text: str):
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
