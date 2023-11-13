import gc, psutil
from prometheus_client import Gauge, generate_latest
from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from flask import Flask, Response
from datetime import datetime, timedelta, timezone
from teleapi import endpoints as teleapi
from threading import Thread
from prometheus_flask_exporter import PrometheusMetrics

import config

app = Flask(__name__)
metrics = PrometheusMetrics(app)
cpu_usage = Gauge("cpu_usage", "CPU Usage")
memory_usage = Gauge("memory_usage", "Memory Usage")


@app.route("/metricz")
def prom_endpoint():
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent

    cpu_usage.set(cpu_percent)
    memory_usage.set(memory_percent)

    log.log_update_prometheus("cpu_usage", cpu_percent)
    log.log_update_prometheus("memory_usage", memory_percent)

    return Response(generate_latest(), mimetype="text/plain")


@app.route("/api", methods=["GET", "POST"])
def run():
    db_service = mongo.MongoService()

    now = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    parsed_time = utils.parse_time_mins(now)
    entries = dbutils.find_entries_by_nextrun(db_service, parsed_time)

    entry_count = len(entries)
    log.log_entry_count(entry_count)

    if entry_count < 1:
        log.log_completion(0)
        gc.collect()
        return Response(status=200)

    q = []
    for entry in entries:
        args = (
            db_service,
            entry,
            parsed_time,
        )
        t = Thread(target=process_job, args=args, daemon=True)
        t.start()
        q.append(t)

    for t in q:
        t.join()

    gc.collect()  # https://github.com/googleapis/google-api-python-client/issues/535
    dbutils.save_msg_count(entry_count)
    log.log_completion(entry_count)
    return Response(status=200)


def process_job(db_service: mongo.MongoService, entry, parsed_time):
    job_id = entry["_id"]
    channel_id = entry.get("channel_id", "")
    chat_id = entry.get("chat_id", "")
    if channel_id != "":
        chat_id = channel_id
    content = entry.get("content", "")
    content_type = entry.get("content_type", "")
    photo_id = entry.get("photo_id", "")
    photo_group_id = str(entry.get("photo_group_id", ""))
    crontab = entry.get("crontab", "")
    previous_message_id = str(entry.get("previous_message_id", ""))
    message_thread_id = entry.get("message_thread_id", None)

    user_bot_token = entry.get("user_bot_token")
    if user_bot_token is None:
        user_bot_token = config.TELEGRAM_BOT_TOKEN

    bot_message_id, status, err = send_message(
        job_id,
        chat_id,
        content,
        content_type,
        photo_id,
        photo_group_id,
        user_bot_token,
        message_thread_id,
    )
    if status == 429:  # try again in one minute
        return

    if entry.get("option_delete_previous", "") != "" and previous_message_id != "":
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
    dbutils.update_entry_by_jobname(db_service, entry, payload)


def send_message(
    job_id,
    chat_id,
    content,
    content_type,
    photo_id,
    photo_group_id,
    user_bot_token,
    message_thread_id,
):
    if photo_group_id != "":  # media group
        resp = teleapi.send_media_group(
            chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif photo_id != "":  # single photo
        resp = teleapi.send_single_photo(
            chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif content_type == ContentType.POLL.value:
        resp = teleapi.send_poll(chat_id, content, user_bot_token, message_thread_id)
    else:  # text message
        resp = teleapi.send_text(chat_id, content, user_bot_token, message_thread_id)

    log.log_api_send_message(job_id, chat_id, resp.status_code)

    if resp.status_code == 429:
        return "", resp.status_code, None
    elif resp.status_code != 200:
        err_msg = "Error {}: {}".format(resp.status_code, resp.json()["description"])
        return "", resp.status_code, err_msg

    if photo_group_id != "":
        msg_ids = [str(message["message_id"]) for message in resp.json()["result"]]
        return ";".join(msg_ids), resp.status_code, None

    return resp.json()["result"]["message_id"], resp.status_code, None


if __name__ == "__main__":
    app.run(debug=True)
