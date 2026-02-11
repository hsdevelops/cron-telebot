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
from typing import Any, Optional, Tuple

import config
from bot.ptb import lifespan

app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)
cpu_usage = Gauge("cpu_usage", "CPU Usage")
memory_usage = Gauge("memory_usage", "Memory Usage")
IGNORED_ERRORS = {"Error 504: TimeoutError - TimeoutError()"}


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
    influx_db = request.app.state.influx

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
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        log.logger.error(f"[API] Job processing failed: {type(e).__name__} - {e}")
        return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    end_time = time.perf_counter()

    gc.collect()  # https://github.com/googleapis/google-api-python-client/issues/535

    if config.INFLUXDB_TOKEN:
        dbutils.save_msg_count(influx_db, entry_count)

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
            f"[TELEGRAM API] Job {entry.get('_id')} failed: {type(e).__name__} - {repr(e)}"
        )


async def process_job(
    db_service: mongo.MongoService,
    http_session: aiohttp.ClientSession,
    entry: Optional[Any],
) -> None:
    if entry is None:
        log.logger.warning("[TELEGRAM API] Skipping empty entry")
        return

    now = utils.now()

    job_id = entry["_id"]
    channel_id = entry.get("channel_id") or ""
    chat_id = entry.get("chat_id") or ""
    if channel_id is not None and channel_id != "":
        chat_id = channel_id
    content = entry.get("content") or ""
    content_type = entry.get("content_type") or ""
    photo_id = entry.get("photo_id") or ""
    photo_group_id = str(entry.get("photo_group_id") or "")
    crontab = entry.get("crontab") or ""
    previous_message_id = str(entry.get("previous_message_id") or "")
    message_thread_id = entry.get("message_thread_id", None)
    db_nextrun_ts = entry.get("nextrun_ts") or ""
    user_nextrun_ts = entry.get("user_nextrun_ts") or ""
    errors = entry.get("errors", [])
    option_delete_previous = entry.get("option_delete_previous") or ""

    user_bot_token = entry.get("user_bot_token")
    if user_bot_token is None:
        user_bot_token = config.TELEGRAM_BOT_TOKEN

    payload = {"pending_ts": now}
    res = await dbutils.update_entry_by_jobname(
        db_service, entry, payload, q=dbutils.make_due_jobs_query(now)
    )

    if getattr(res, "modified_count", 0) <= 0:
        log.logger.info(
            f'[TELEGRAM API] Job likely being processed by another worker, job_id="{job_id}", chat_id={chat_id}'
        )
        return

    # process messages
    bot_message_id, err = await send_message(
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

    if err is None:
        if option_delete_previous != "" and previous_message_id != "":
            await teleapi.delete_message(
                http_session, chat_id, previous_message_id, user_bot_token
            )

        # calculate and update next run time
        chat_entry = await dbutils.find_chat_by_chatid(db_service, chat_id) or {}
        user_tz_offset = chat_entry.get("tz_offset", config.TZ_OFFSET)
        user_timezone = chat_entry.get("utc_tz")
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, user_timezone, user_tz_offset
        )
        errors = []
    else:
        if err not in IGNORED_ERRORS:
            errors = [*errors, {"error": err, "timestamp": now}]
        bot_message_id = previous_message_id

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
) -> Tuple[str, Optional[str]]:
    err = None

    if photo_group_id != "":  # media group
        resp, err = await teleapi.send_media_group(
            http_session, chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif photo_id != "":  # single photo
        resp, err = await teleapi.send_single_photo(
            http_session, chat_id, photo_id, content, user_bot_token, message_thread_id
        )
    elif content_type == ContentType.POLL.value:
        resp, err = await teleapi.send_poll(
            http_session, chat_id, content, user_bot_token, message_thread_id
        )
    else:  # text message
        resp, err = await teleapi.send_text(
            http_session, chat_id, content, user_bot_token, message_thread_id
        )

    if err is not None or resp.status != 200:
        if err is None:
            err = resp.json.get("description") or "Unknown error"
        err = f"Error {resp.status}: {err}"
        log.logger.warning(
            f'[TELEGRAM API] Failed to send message, job_id="{job_id}", chat_id={chat_id}, status={resp.status}, err={err}'
        )
        return "", err

    log.logger.info(
        f'[TELEGRAM API] Sent message, job_id="{job_id}", chat_id={chat_id}, response_status={resp.status}'
    )

    if photo_group_id != "":
        msg_ids = [
            str(message.get("message_id"))
            for message in resp.json.get("result", [])
            if isinstance(message, dict) and message.get("message_id") is not None
        ]
        return ";".join(msg_ids), None

    message_id = resp.json.get("result", {}).get("message_id") or ""
    return message_id, None


# Run api only
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log.log_config)
