from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from flask import Flask, Response
from datetime import datetime, timedelta, timezone
from teleapi import endpoints as teleapi
from threading import Thread
import config

app = Flask(__name__)


@app.route("/api", methods=["GET", "POST"])
def run():
    db_service = mongo.MongoService()

    now = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    parsed_time = utils.parse_time_mins(now)
    entries = dbutils.find_entries_by_nextrun(db_service, parsed_time)

    log.log_entry_count(len(entries))

    if len(entries) < 1:
        log.log_completion(0)
        return Response(status=200)

    q = []
    for row in entries:
        # process_job(db_service, row, parsed_time)
        args = (
            db_service,
            row,
            parsed_time,
        )
        t = Thread(target=process_job, args=args)
        t.daemon = True
        t.start()
        q.append(t)

    for t in q:
        t.join()

    log.log_completion(len(entries))
    return Response(status=200)


def process_job(db_service: mongo.MongoService, row, parsed_time):
    channel_id = row.get("channel_id", "")
    chat_id = row.get("chat_id", "")
    if channel_id != "":
        chat_id = channel_id
    content = row.get("content", "")
    content_type = row.get("content_type", "")
    photo_id = row.get("photo_id", "")
    photo_group_id = str(row.get("photo_group_id", ""))
    crontab = row.get("crontab", "")
    previous_message_id = str(row.get("previous_message_id", ""))

    user_bot_token = row.get("user_bot_token")
    if user_bot_token is None:
        user_bot_token = config.TELEGRAM_BOT_TOKEN

    bot_message_id, err = send_message(
        chat_id, content, content_type, photo_id, photo_group_id, user_bot_token
    )
    if row.get("option_delete_previous", "") != "" and previous_message_id != "":
        teleapi.delete_message(chat_id, previous_message_id, user_bot_token)

    # calculate and update next run time
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    user_tz_offset = chat_entry.get("tz_offset")
    user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)

    payload = {
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "previous_message_id": str(bot_message_id),
        "remarks": "" if err is None else err,
        "removed_ts": "" if err is None else parsed_time,
    }
    dbutils.update_entry_by_jobname(db_service, row, payload)


def send_message(
    chat_id, content, content_type, photo_id, photo_group_id, user_bot_token
):
    if photo_group_id != "":  # media group
        resp = teleapi.send_media_group(chat_id, photo_id, content, user_bot_token)
    elif photo_id != "":  # single photo
        resp = teleapi.send_single_photo(chat_id, photo_id, content, user_bot_token)
    elif content_type == ContentType.POLL.value:
        resp = teleapi.send_poll(chat_id, content, user_bot_token)
    else:  # text message
        resp = teleapi.send_text(chat_id, content, user_bot_token)

    log.log_api_send_message(chat_id, content, resp.status_code)

    if resp.status_code != 200:
        return "", "Error {}: {}".format(resp.status_code, resp.json()["description"])

    if photo_group_id != "":
        msg_ids = [str(message["message_id"]) for message in resp.json()["result"]]
        return ";".join(msg_ids), None

    return resp.json()["result"]["message_id"], None


if __name__ == "__main__":
    app.run(debug=True)
