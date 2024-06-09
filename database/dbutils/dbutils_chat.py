from common import log, utils
from database.mongo import MongoService
from typing import Any, Optional
from datetime import datetime
from telegram import Update

"""
Getters
"""


def find_chat_by_chatid(db_service: MongoService, chat_id: int) -> Optional[Any]:
    q = {"chat_id": float(chat_id)}
    return db_service.find_one_chat_entry(q)


def find_chat_by_title(
    db_service: MongoService, user_id: int, chat_title: str
) -> Optional[Any]:
    q = {"created_by": user_id, "chat_title": chat_title}
    return db_service.find_one_chat_entry(q)


def chat_exists(db_service: MongoService, chat_id: int) -> bool:
    return find_chat_by_chatid(db_service, chat_id) is not None


def find_groups_created_by(db_service: MongoService, user_id: int) -> Optional[Any]:
    q = {
        "created_by": user_id,
        "chat_type": {"$nin": ["private", "channel"]},
    }
    return db_service.find_chat_entries(q)


"""
Setters
"""


def add_chat_data(
    db_service: MongoService,
    chat_id: int,
    chat_title: str,
    chat_type: str,
    tz_offset: float,
    utc_tz: str,
    created_by: int,
    telegram_ts: datetime,
) -> None:
    new_doc = {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "chat_type": chat_type,
        "tz_offset": tz_offset,
        "utc_tz": utc_tz,
        "created_by": created_by,
        "telegram_ts": utils.parse_time_millis(telegram_ts),
        "restriction": "",
        "user_bot_token": None,
    }
    db_service.insert_new_chat(new_doc)
    log.log_new_chat(chat_id, chat_title)


def update_chats_tz_by_type(
    db_service: MongoService,
    user_id: int,
    tz_offset: float,
    chat_type: str,
    utc_tz: str = "",
) -> None:
    payload = {"tz_offset": tz_offset, "utc_tz": utc_tz, "updated_ts": utils.now()}
    q = {"created_by": user_id, "chat_type": chat_type}
    mongo_response = db_service.update_chat_entries(q, payload)
    modified_count = mongo_response.modified_count
    log.log_chats_tz_updated_by_type(modified_count, user_id, chat_type, tz_offset)


def update_chat_entry(
    db_service: MongoService,
    chat_id: int,
    update: Update,
    updated_field: str = "restriction",
) -> None:
    q = {"chat_id": chat_id}
    db_service.update_one_chat_entry(q, update)
    log.log_chat_entry_updated(chat_id, updated_field, update[updated_field])
