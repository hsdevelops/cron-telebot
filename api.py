import gc
import psutil
from http import HTTPStatus
from prometheus_client import Gauge, generate_latest
import uvicorn
from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from datetime import datetime, timedelta, timezone
from teleapi import endpoints as teleapi
from threading import Thread
from fastapi import FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Any, Optional

import config
from bot.ptb import lifespan


app = FastAPI(lifespan=lifespan) if config.ENV else FastAPI()
Instrumentator().instrument(app).expose(app)
cpu_usage = Gauge("cpu_usage", "CPU Usage")
memory_usage = Gauge("memory_usage", "Memory Usage")


@app.get("/")
def home() -> str:
    return "Hello world!"


@app.get("/metricz")
def prom_endpoint() -> Response:
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent

    cpu_usage.set(cpu_percent)
    memory_usage.set(memory_percent)

    log.log_update_prometheus("cpu_usage", cpu_percent)
    log.log_update_prometheus("memory_usage", memory_percent)

    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/api")
@app.post("/api")
def run() -> Response:
    db_service = mongo.MongoService()

    now = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    parsed_time = utils.parse_time_mins(now)
    entries = dbutils.find_entries_by_nextrun(db_service, parsed_time)

    entry_count = len(entries)
    log.log_entry_count(entry_count)

    if entry_count < 1:
        log.log_completion(0)
        gc.collect()
        return Response(status_code=HTTPStatus.OK)

    for i in range(0, len(entries), config.BATCH_SIZE):
        batch = entries[i : i + config.BATCH_SIZE]
        batch_jobs(db_service, batch, parsed_time)

    gc.collect()  # https://github.com/googleapis/google-api-python-client/issues/535
    if config.INFLUXDB_TOKEN:
        dbutils.save_msg_count(entry_count)
    log.log_completion(entry_count)
    return Response(status_code=HTTPStatus.OK)


def batch_jobs(db_service: mongo.MongoService, entries: list, parsed_time: str) -> None:
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


def process_job(
    db_service: mongo.MongoService, entry: Optional[Any], parsed_time: str
) -> None:
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
    errors = entry.get("errors", [])

    user_bot_token = entry.get("user_bot_token")
    if user_bot_token is None:
        user_bot_token = config.TELEGRAM_BOT_TOKEN

    payload = {"pending_ts": utils.now()}
    dbutils.update_entry_by_jobname(db_service, entry, payload)

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

    if entry.get("option_delete_previous", "") != "" and previous_message_id != "":
        teleapi.delete_message(chat_id, previous_message_id, user_bot_token)

    # calculate and update next run time
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id) or {}
    user_tz_offset = chat_entry.get("tz_offset", config.TZ_OFFSET)
    user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)
    errors = [] if err is None else [*errors, {"error": err, "timestamp": parsed_time}]

    payload = {
        "pending_ts": None,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "previous_message_id": str(bot_message_id),
        "removed_ts": parsed_time if len(errors) > config.RETRIES else "",
        "errors": errors,
    }
    dbutils.update_entry_by_jobname(db_service, entry, payload)


def send_message(
    job_id: int,
    chat_id: int,
    content: str,
    content_type: str,
    photo_id: str,
    photo_group_id: str,
    user_bot_token: str,
    message_thread_id: int,
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

    if resp.status_code != 200:
        err_msg = "Error {}: {}".format(resp.status_code, resp.json()["description"])
        return "", resp.status_code, err_msg

    if photo_group_id != "":
        msg_ids = [str(message["message_id"]) for message in resp.json()["result"]]
        return ";".join(msg_ids), resp.status_code, None

    return resp.json()["result"]["message_id"], resp.status_code, None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
