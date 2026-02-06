import json
import os

from aiohttp import ClientSession
from common import log
from urllib.parse import urlencode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_BASE_URL
from database.dbutils import dbutils
from typing import Optional, Any, Dict, Tuple
from database import mongo
from teleapi.requests import RequestResponse, request


async def get_bot_details(
    http_session: ClientSession, user_bot_token: str
) -> RequestResponse:
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/getMe"
    return await request(http_session, endpoint)


async def send_media_group(
    http_session: ClientSession,
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> Tuple[RequestResponse, Optional[str]]:
    media, files, err = await prepare_photos(http_session, photo_id, content)
    if err is not None:
        return RequestResponse(), err

    query = {
        "chat_id": chat_id,
        "media": media,
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = (
        f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendMediaGroup?{query_string}"
    )
    resp = await request(http_session, endpoint, method="POST", files=files)
    return resp, None


async def send_single_photo(
    http_session: ClientSession,
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> RequestResponse:
    query = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendPhoto?{query_string}"
    resp = await request(http_session, endpoint)
    return resp


async def send_single_photo_local(
    http_session: ClientSession,
    new_token: Optional[str],
    chat_id: int,
    content: str = "",
    photo: Optional[str] = None,
    remote_photo_id: Optional[str] = None,
    prev_token: Optional[str] = None,
) -> Tuple[RequestResponse, Optional[str]]:
    err = None

    if photo is None and remote_photo_id is None:
        raise ValueError("Either photo or remote_photo_id must be specified")
    if remote_photo_id is not None and prev_token is None:
        prev_token = TELEGRAM_BOT_TOKEN
    if new_token is None:
        new_token = TELEGRAM_BOT_TOKEN
    if remote_photo_id is not None:
        files, err = await download_photo(http_session, {}, remote_photo_id, prev_token)
        photo = files[remote_photo_id]

    if err is not None:
        return RequestResponse(), err

    query_string = urlencode({"chat_id": chat_id, "caption": content})
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{new_token}/sendPhoto?{query_string}"
    resp = await request(http_session, endpoint, method="POST", files={"photo": photo})
    return resp, None


async def send_poll(
    http_session: ClientSession,
    chat_id: int,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> RequestResponse:
    try:
        poll_content = json.loads(content)
    except Exception as e:
        log.logger.warning(
            f"[TELEGRAM API] Invalid poll content: {type(e).__name__} - {e}"
        )
        return {"status": 0, "json": None, "content": None, "error": str(e)}

    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendPoll"
    parameters = {
        "chat_id": chat_id,
        "question": poll_content.get("question"),
        "options": json.dumps(
            [option.get("text") for option in poll_content.get("options")]
        ),
        "type": poll_content.get("type"),
        "is_anonymous": poll_content.get("is_anonymous"),
        "allows_multiple_answers": poll_content.get("allows_multiple_answers"),
        "correct_option_id": poll_content.get("correct_option_id"),
        "explanation": poll_content.get("explanation"),
        "explanation_parse_mode": "html",
        "is_closed": poll_content.get("is_closed"),
        "close_date": poll_content.get("close_date"),
        "reply_to_message_id": message_thread_id,
    }
    resp = await request(http_session, endpoint, data=parameters)
    return resp


async def send_text(
    http_session: ClientSession,
    chat_id: int,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> RequestResponse:
    query = {
        "chat_id": chat_id,
        "text": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendMessage?{query_string}"
    resp = await request(http_session, endpoint)
    return resp


async def delete_message(
    http_session: ClientSession,
    chat_id: int,
    previous_message_id: str,
    user_bot_token: Optional[str] = None,
) -> Any:
    if user_bot_token is None:
        user_bot_token = TELEGRAM_BOT_TOKEN
    message_ids = str(previous_message_id).split(";")
    if len(message_ids) <= 0:
        return
    last_ok = None
    for message_id in message_ids:
        try:
            endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/deleteMessage?chat_id={chat_id}&message_id={message_id}"
            response = await request(http_session, endpoint)
            json_resp = response.get("json") or {}
            log.logger.info(
                f'[TELEGRAM API] Deleted previous message, response_status={response.get("status")}, chat_id={chat_id}, message_id={message_id}'
            )
            last_ok = json_resp.get("ok")
        except Exception as e:
            log.logger.warning(
                f"[TELEGRAM API] delete_message failed: {type(e).__name__} - {e}"
            )
            last_ok = None
    return last_ok


async def prepare_photos(
    http_session: ClientSession, photo_id: str, content: str
) -> Tuple[str, Dict[str, Any], Optional[str]]:
    photo_ids = photo_id.split(";")
    media, files = [], {}
    for i, photo_id in enumerate(photo_ids):
        files, err = await download_photo(http_session, files, photo_id)
        if err is not None:
            return json.dumps(media), files, err

        media.append(
            {
                "type": "photo",
                "media": "attach://%s" % photo_id,
                "caption": content if i <= 0 else "",
            }
        )
    return json.dumps(media), files, None


async def download_photo(
    http_session: ClientSession,
    files: Dict[str, Any],
    photo_id: str,
    bot_token: Optional[str] = TELEGRAM_BOT_TOKEN,
) -> Tuple[Dict[str, Any], Optional[str]]:
    file_details_endpoint = (
        f"{TELEGRAM_API_BASE_URL}/bot{bot_token}/getFile?file_id={photo_id}"
    )
    try:
        file_details_response = await request(http_session, file_details_endpoint)
        if file_details_response.get("status") != 200:
            err = f'Failed to get file details, bot_token = {bot_token}, photo_id = {photo_id}, status = {file_details_response.get("status")}'
            log.logger.warning(f"[TELEGRAM API] {err}")
            return files, err

        json_resp = file_details_response.get("json") or {}
        file_path = (
            json_resp.get("result", {}).get("file_path")
            if isinstance(json_resp, dict)
            else None
        )
        if not file_path:
            err = f"Failed to resolve file_path, bot_token = {bot_token}, photo_id = {photo_id}"
            log.logger.warning(f"[TELEGRAM API] {err}")
            return files, err

        file_url = f"{TELEGRAM_API_BASE_URL}/file/bot{bot_token}/{file_path}"
        file_response = await request(http_session, file_url)

        if file_response.get("status") != 200:
            err = f'Failed to get file, bot_token = {bot_token}, photo_id = {photo_id}, status = {file_response.get("status")}'
            log.logger.warning(f"[TELEGRAM API] {err}")
            return files, err

        content = file_response.get("content")
        if content is None:
            err = f"Empty file content, bot_token = {bot_token}, photo_id = {photo_id}"
            log.logger.warning(f"[TELEGRAM API] {err}")
            return files, err

        open(photo_id, "wb").write(content)
        files[photo_id] = open(photo_id, "rb")
        os.remove(photo_id)
        return files, None

    except Exception as e:
        log.logger.warning(
            f"[TELEGRAM API] download_photo failed: {type(e).__name__} - {e}"
        )
        try:
            if os.path.exists(photo_id):
                os.remove(photo_id)
        except Exception:
            pass
        return files, str(e)


async def transfer_photo_between_bots(
    http_session: ClientSession,
    db_service: mongo.MongoService,
    new_token: Optional[str],
    prev_token: Optional[str],
    chat_id: int,
    photo_id: str,
    job_id: str,
) -> Tuple[RequestResponse, Optional[str]]:
    resp, err = await send_single_photo_local(
        http_session,
        new_token=new_token,
        chat_id=chat_id,
        content="Transferring photo between bots...",
        remote_photo_id=photo_id,
        prev_token=prev_token,
    )

    if err is not None:
        log.logger.warning(
            f"[TELEGRAM API] failed to transfer photo between bots, err={err}"
        )
        return resp, err

    if resp.get("status") != 200:
        log.logger.warning(
            f'[TELEGRAM API] failed to transfer photo between bots, status={resp.get("status")}'
        )
        return resp, None

    json_resp = resp.get("json") or {}
    new_photo_id = (
        json_resp.get("result", {}).get("photo", [{}])[-1].get("file_id")
        if isinstance(json_resp, dict)
        else None
    )
    if not new_photo_id:
        log.logger.warning("[TELEGRAM API] failed to parse new photo id from response")
        return resp, None

    q = {"photo_id": new_photo_id}
    await dbutils.update_entry_by_jobid(db_service, job_id, q)

    message_id = json_resp.get("result", {}).get("message_id")
    if message_id is not None:
        await delete_message(http_session, chat_id, str(message_id), new_token)
    return resp, new_photo_id
