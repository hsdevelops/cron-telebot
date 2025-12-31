from common import log, utils
from database.mongo import MongoService
from typing import Any, Optional
from datetime import datetime
from telegram import Update

"""
Getters
"""


async def find_chat_by_chatid(db_service: MongoService, chat_id: int) -> Optional[Any]:
    q = {"chat_id": float(chat_id)}
    return await db_service.find_one_chat_entry(q)


async def find_chat_by_title(
    db_service: MongoService, user_id: int, chat_title: str
) -> Optional[Any]:
    q = {"created_by": user_id, "chat_title": chat_title}
    return await db_service.find_one_chat_entry(q)


async def chat_exists(db_service: MongoService, chat_id: int) -> bool:
    return await find_chat_by_chatid(db_service, chat_id) is not None


async def find_groups_created_by(
    db_service: MongoService, user_id: int
) -> Optional[Any]:
    q = {
        "created_by": user_id,
        "chat_type": {"$nin": ["private", "channel"]},
    }
    return await db_service.find_chat_entries(q)


"""
Setters
"""


async def add_chat_data(
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
    await db_service.insert_new_chat(new_doc)
    log.logger.info(
        f"[DB] Created new chat entry, chat_id={chat_id}, chat_title={chat_title}"
    )


async def update_chats_tz_by_type(
    db_service: MongoService,
    user_id: int,
    tz_offset: float,
    chat_type: str,
    utc_tz: str = "",
) -> None:
    payload = {"tz_offset": tz_offset, "utc_tz": utc_tz, "updated_ts": utils.now()}
    q = {"created_by": user_id, "chat_type": chat_type}
    mongo_response = await db_service.update_chat_entries(q, payload)
    modified_count = mongo_response.modified_count
    log.logger.info(
        f"[DB] Bulk updated timezone for {modified_count} chats, chat_type={chat_type}, user_id={user_id}, new tz_offset={tz_offset}"
    )


async def update_chat_entry(
    db_service: MongoService,
    chat_id: int,
    update: Update,
    updated_field: str = "restriction",
) -> None:
    q = {"chat_id": chat_id}
    await db_service.update_one_chat_entry(q, update)
    log.logger.info(
        f'[DB] Updated chat {updated_field} to "{update[updated_field]}", chat_id={chat_id}'
    )
