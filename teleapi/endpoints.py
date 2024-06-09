import json
import os
import requests
from common import log
from urllib.parse import urlencode
from config import TELEGRAM_BOT_TOKEN
from database.dbutils import dbutils
from typing import Optional, Any, Dict, Tuple
from database import mongo


def get_bot_details(user_bot_token: str) -> requests.Response:
    endpoint = "https://api.telegram.org/bot{}/getMe".format(user_bot_token)
    return requests.get(endpoint)


def send_media_group(
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> requests.Response:
    media, files = prepare_photos(photo_id, content)
    query = {
        "chat_id": chat_id,
        "media": media,
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = "https://api.telegram.org/bot{}/sendMediaGroup?{}".format(
        user_bot_token, query_string
    )
    return requests.post(endpoint, files=files)


def send_single_photo(
    chat_id: int,
    photo_id: str,
    content: str,
    user_bot_token: str,
    message_thread_id: int,
) -> requests.Response:
    query = {
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = "https://api.telegram.org/bot{}/sendPhoto?{}".format(
        user_bot_token, query_string
    )
    return requests.get(endpoint)


def send_single_photo_local(
    new_token: Optional[str],
    chat_id: int,
    content: str = "",
    photo: Optional[str] = None,
    remote_photo_id: Optional[str] = None,
    prev_token: Optional[str] = None,
) -> requests.Response:
    if photo is None and remote_photo_id is None:
        raise ValueError("Either photo or remote_photo_id must be specified")
    if remote_photo_id is not None and prev_token is None:
        prev_token = TELEGRAM_BOT_TOKEN
    if new_token is None:
        new_token = TELEGRAM_BOT_TOKEN
    if remote_photo_id is not None:
        files = download_photo({}, remote_photo_id, prev_token)
        photo = files[remote_photo_id]
    query_string = urlencode({"chat_id": chat_id, "caption": content})
    endpoint = "https://api.telegram.org/bot{}/sendPhoto?{}".format(
        new_token, query_string
    )
    return requests.post(endpoint, files={"photo": photo})


def send_poll(
    chat_id: int, content: str, user_bot_token: str, message_thread_id: int
) -> requests.Response:
    poll_content = json.loads(content)
    endpoint = "https://api.telegram.org/bot{}/sendPoll".format(user_bot_token)
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
    return requests.get(endpoint, data=parameters)


def send_text(
    chat_id: int, content: str, user_bot_token: str, message_thread_id: int
) -> requests.Response:
    query = {
        "chat_id": chat_id,
        "text": content,
        "parse_mode": "html",
        "reply_to_message_id": message_thread_id,
    }
    query_string = urlencode(query)
    endpoint = "https://api.telegram.org/bot{}/sendMessage?{}".format(
        user_bot_token, query_string
    )
    return requests.get(endpoint)


def delete_message(
    chat_id: int, previous_message_id: str, user_bot_token: Optional[str] = None
) -> Any:
    if user_bot_token is None:
        user_bot_token = TELEGRAM_BOT_TOKEN
    for message_id in str(previous_message_id).split(";"):
        endpoint = "https://api.telegram.org/bot{}/deleteMessage?chat_id={}&message_id={}".format(
            user_bot_token, chat_id, message_id
        )
        response = requests.get(endpoint)
        log.log_api_previous_message_deletion(chat_id, message_id, response.status_code)
    return response.json()["ok"]


def prepare_photos(photo_id: str, content: str) -> Tuple[str, Dict[str, Any]]:
    photo_ids = photo_id.split(";")
    media, files = [], {}
    for i, photo_id in enumerate(photo_ids):
        files = download_photo(files, photo_id)
        media.append(
            {
                "type": "photo",
                "media": "attach://%s" % photo_id,
                "caption": content if i <= 0 else "",
            }
        )
    return json.dumps(media), files


def download_photo(
    files: Dict[str, Any], photo_id: str, bot_token: Optional[str] = TELEGRAM_BOT_TOKEN
) -> Dict[str, Any]:
    file_details_endpoint = "https://api.telegram.org/bot{}/getFile?file_id={}".format(
        bot_token, photo_id
    )
    file_details_response = requests.get(file_details_endpoint)
    file_path = file_details_response.json()["result"]["file_path"]
    file_url = "https://api.telegram.org/file/bot{}/{}".format(bot_token, file_path)
    file_response = requests.get(file_url)
    open(photo_id, "wb").write(file_response.content)
    files[photo_id] = open(photo_id, "rb")
    os.remove(photo_id)
    return files


def transfer_photo_between_bots(
    db_service: mongo.MongoService,
    new_token: Optional[str],
    prev_token: Optional[str],
    chat_id: int,
    entry: Optional[Any],
) -> Tuple[requests.Response, Optional[str]]:
    resp = send_single_photo_local(
        new_token=new_token,
        chat_id=chat_id,
        content="Transferring photo between bots...",
        remote_photo_id=entry["photo_id"],
        prev_token=prev_token,
    )
    new_photo_id = None
    if resp.status_code == 200:
        new_photo_id = resp.json()["result"]["photo"][-1]["file_id"]
        q = {"photo_id": new_photo_id}
        dbutils.update_entry_by_jobid(db_service, entry["_id"], q)
        delete_message(chat_id, str(resp.json()["result"]["message_id"]), new_token)
    return resp, new_photo_id
