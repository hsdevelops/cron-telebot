import json
import os

from aiohttp import ClientResponse, ClientSession
from common import log
from urllib.parse import urlencode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_BASE_URL
from database.dbutils import dbutils
from typing import Optional, Any, Dict, Tuple
from database import mongo
from teleapi.requests import request


async def get_bot_details(
    http_session: ClientSession, user_bot_token: str
) -> ClientResponse:
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/getMe"
    return await request(http_session, endpoint)


async def send_media_group(
    http_session: ClientSession,
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> ClientResponse:
    media, files = await prepare_photos(http_session, photo_id, content)
    query = {
        "chat_id": chat_id,
        "media": media,
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = (
        f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendMediaGroup?{query_string}"
    )
    return await request(http_session, endpoint, method="POST", files=files)


async def send_single_photo(
    http_session: ClientSession,
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> ClientResponse:
    query = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendPhoto?{query_string}"
    return await request(http_session, endpoint)


async def send_single_photo_local(
    http_session: ClientSession,
    new_token: Optional[str],
    chat_id: int,
    content: str = "",
    photo: Optional[str] = None,
    remote_photo_id: Optional[str] = None,
    prev_token: Optional[str] = None,
) -> ClientResponse:
    if photo is None and remote_photo_id is None:
        raise ValueError("Either photo or remote_photo_id must be specified")
    if remote_photo_id is not None and prev_token is None:
        prev_token = TELEGRAM_BOT_TOKEN
    if new_token is None:
        new_token = TELEGRAM_BOT_TOKEN
    if remote_photo_id is not None:
        files = await download_photo(http_session, {}, remote_photo_id, prev_token)
        photo = files[remote_photo_id]
    query_string = urlencode({"chat_id": chat_id, "caption": content})
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{new_token}/sendPhoto?{query_string}"
    return await request(http_session, endpoint, method="POST", files={"photo": photo})


async def send_poll(
    http_session: ClientSession,
    chat_id: int,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> ClientResponse:
    poll_content = json.loads(content)
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
    return await request(http_session, endpoint, data=parameters)


async def send_text(
    http_session: ClientSession,
    chat_id: int,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> ClientResponse:
    query = {
        "chat_id": chat_id,
        "text": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/sendMessage?{query_string}"
    return await request(http_session, endpoint)


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
    for message_id in message_ids:
        endpoint = f"{TELEGRAM_API_BASE_URL}/bot{user_bot_token}/deleteMessage?chat_id={chat_id}&message_id={message_id}"
        response = await request(http_session, endpoint)
        json = response.get("json")
        log.logger.info(
            f'[TELEGRAM API] Deleted previous message, response_status={response.get("status")}, chat_id={chat_id}, message_id={message_id}'
        )
    return json["ok"]


async def prepare_photos(
    http_session: ClientSession, photo_id: str, content: str
) -> Tuple[str, Dict[str, Any]]:
    photo_ids = photo_id.split(";")
    media, files = [], {}
    for i, photo_id in enumerate(photo_ids):
        files = await download_photo(http_session, files, photo_id)
        media.append(
            {
                "type": "photo",
                "media": "attach://%s" % photo_id,
                "caption": content if i <= 0 else "",
            }
        )
    return json.dumps(media), files


async def download_photo(
    http_session: ClientSession,
    files: Dict[str, Any],
    photo_id: str,
    bot_token: Optional[str] = TELEGRAM_BOT_TOKEN,
) -> Dict[str, Any]:
    file_details_endpoint = (
        f"{TELEGRAM_API_BASE_URL}/bot{bot_token}/getFile?file_id={photo_id}"
    )
    file_details_response = await request(http_session, file_details_endpoint)
    json = file_details_response.get("json")
    file_path = json["result"]["file_path"]
    file_url = f"{TELEGRAM_API_BASE_URL}/file/bot{bot_token}/{file_path}"
    file_response = await request(http_session, file_url)
    open(photo_id, "wb").write(file_response.get("content"))
    files[photo_id] = open(photo_id, "rb")
    os.remove(photo_id)
    return files


async def transfer_photo_between_bots(
    http_session: ClientSession,
    db_service: mongo.MongoService,
    new_token: Optional[str],
    prev_token: Optional[str],
    chat_id: int,
    entry: Optional[Any],
) -> Tuple[ClientResponse, Optional[str]]:
    resp = await send_single_photo_local(
        http_session,
        new_token=new_token,
        chat_id=chat_id,
        content="Transferring photo between bots...",
        remote_photo_id=entry["photo_id"],
        prev_token=prev_token,
    )
    new_photo_id = None
    if resp.get("status") == 200:
        json = resp.get("json")
        new_photo_id = json["result"]["photo"][-1]["file_id"]
        q = {"photo_id": new_photo_id}
        await dbutils.update_entry_by_jobid(db_service, entry["_id"], q)
        await delete_message(
            http_session, chat_id, str(json["result"]["message_id"]), new_token
        )
    return resp, new_photo_id
