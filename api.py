import asyncio
import gc
import time
import aiohttp
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
from fastapi import FastAPI, Request, Response
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Any, Optional

import config
from bot.ptb import lifespan

app = FastAPI(lifespan=lifespan)
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

    log.logger.info(
        f"[PROMETHEUS] Updated Prometheus, cpu_usage={cpu_percent}, memory_usage={memory_percent}"
    )

    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/api")
@app.post("/api")
async def run(request: Request) -> Response:
    db_service = request.app.state.mongo
    http_session = request.app.state.http_session

    now = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
    parsed_time = utils.parse_time_mins(now)
    entries = await dbutils.find_entries_by_nextrun(db_service, parsed_time)

    entry_count = len(entries)
    log.logger.info(
        f"[TELEGRAM API] Processing {entry_count} message(s) to send this time..."
    )

    if entry_count < 1:
        gc.collect()
        return Response(status_code=HTTPStatus.OK)

    # schedule all jobs with concurrency limit
    start_time = time.perf_counter()
    sem = asyncio.Semaphore(config.BATCH_SIZE)  # concurrency limiter
    tasks = [
        bounded_process_job(db_service, http_session, entry, sem) for entry in entries
    ]
    # gather all tasks, exceptions are handled individually inside bounded_process_job
    await asyncio.gather(*tasks)
    end_time = time.perf_counter()

    gc.collect()  # https://github.com/googleapis/google-api-python-client/issues/535

    if config.INFLUXDB_TOKEN:
        dbutils.save_msg_count(entry_count)

    log.logger.info(
        f"[TELEGRAM API] Finished processing {entry_count} messages in {end_time - start_time:.2f} seconds"
    )

    return Response(status_code=HTTPStatus.OK)


async def bounded_process_job(
    db_service: mongo.MongoService,
    http_session: aiohttp.ClientSession,
    entry: Optional[Any],
    sem: asyncio.Semaphore,
):
    try:
        # Acquire semaphore safely
        async with sem:
            await process_job(db_service, http_session, entry)
    except Exception as e:
        log.logger.error(
            f"[TELEGRAM API] job {entry.get('_id')} failed: {type(e).__name__} - {repr(e)}"
        )


async def process_job(
    db_service: mongo.MongoService,
    http_session: aiohttp.ClientSession,
    entry: Optional[Any],
) -> None:
    now = utils.now()

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

    payload = {"pending_ts": now}
    res = await dbutils.update_entry_by_jobname(
        db_service, entry, payload, q=dbutils.make_due_jobs_query(now)
    )
    if res.modified_count <= 0:
        log.logger.info(
            f'[TELEGRAM API] Job likely being processed by another worker, job_id="{job_id}", chat_id={chat_id}'
        )
        return

    bot_message_id, status, err = await send_message(
        http_session,
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
        await teleapi.delete_message(
            http_session, chat_id, previous_message_id, user_bot_token
        )

    # calculate and update next run time
    chat_entry = await dbutils.find_chat_by_chatid(db_service, chat_id) or {}
    user_tz_offset = chat_entry.get("tz_offset", config.TZ_OFFSET)
    user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)
    errors = [] if err is None else [*errors, {"error": err, "timestamp": now}]

    payload = {
        "pending_ts": None,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "previous_message_id": str(bot_message_id),
        "removed_ts": now if len(errors) > config.RETRIES else "",
        "errors": errors,
    }
    await dbutils.update_entry_by_jobname(db_service, entry, payload)


async def send_message(
    http_session: aiohttp.ClientSession,
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
        resp = await teleapi.send_media_group(
            http_session, chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif photo_id != "":  # single photo
        resp = await teleapi.send_single_photo(
            http_session, chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif content_type == ContentType.POLL.value:
        resp = await teleapi.send_poll(
            http_session, chat_id, content, user_bot_token, message_thread_id
        )
    else:  # text message
        resp = await teleapi.send_text(
            http_session, chat_id, content, user_bot_token, message_thread_id
        )

    log.logger.info(
        f'[TELEGRAM API] Sent message, job_id="{job_id}", chat_id={chat_id}, response_status={resp.get("status")}'
    )

    json = resp.get("json", {})

    if resp.get("status") != 200:
        err_msg = "Error {}: {}".format(resp.get("status"), json["description"])
        return "", resp.get("status"), err_msg

    if photo_group_id != "":
        msg_ids = [str(message["message_id"]) for message in json.get("result", [])]
        return ";".join(msg_ids), resp.get("status"), None

    return json.get("result", {}).get("message_id", ""), resp.get("status"), None


# Run api only
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log.log_config)
