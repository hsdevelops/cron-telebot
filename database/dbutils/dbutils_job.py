from pymongo import ASCENDING, DESCENDING
from common import utils
from common.enums import ContentType
from database.mongo import MongoService
from common import log, utils
from typing import List, Optional
from database.consts import QUERY_TYPE, COLLECTION_TYPE, Any, Dict


"""
Getters
"""


def find_latest_entry(db_service: MongoService, chat_id: int) -> COLLECTION_TYPE:
    q = {"chat_id": float(chat_id), "removed_ts": ""}
    result = db_service.find_entries(q, [("created_ts", DESCENDING)])
    if len(result) <= 0:
        return None
    return result[0]


def find_entry_by_jobname(
    db_service: MongoService, chat_id: int, jobname: str, include_removed: bool = False
) -> COLLECTION_TYPE:
    q = {"chat_id": float(chat_id), "jobname": jobname}
    if not include_removed:
        q["removed_ts"] = ""
    return db_service.find_one_entry(q)


def find_entries_removed_between(
    db_service: MongoService, start_ts: str, end_ts: str, err_status: Optional[int] = None
) -> List[QUERY_TYPE]:
    q = {"removed_ts": {"$gte": start_ts, "$lte": end_ts}}
    if err_status is not None:
        q["errors.error"] = {"$regex": f"^Error {err_status}"}
    return db_service.find_entries(q)


def find_entries_by_nextrun(db_service: MongoService, ts: str) -> List[COLLECTION_TYPE]:
    base_q = {"nextrun_ts": {"$lte": ts},
              "removed_ts": "", "crontab": {"$ne": ""}}
    q = {
        "$or": [
            {"paused_ts": "", **base_q},
            {"paused_ts": {"$exists": False}, **base_q},
        ]
    }
    return db_service.find_entries(q, [("created_at", ASCENDING)])


def find_entries_by_content_type(
    db_service: MongoService, chat_id: int, content_type: str = ContentType.PHOTO.value
) -> List[COLLECTION_TYPE]:
    q = {
        "$or": [{"chat_id": chat_id}, {"channel_id": chat_id}],
        "removed_ts": "",
        "content_type": content_type,
    }
    return db_service.find_entries(q)


def find_entries_by_chatid(db_service: MongoService, chat_id: int) -> List[COLLECTION_TYPE]:
    q = {"chat_id": float(chat_id), "removed_ts": ""}
    return db_service.find_entries(q)


def count_entries_by_userid(db_service: MongoService, user_id: int) -> int:
    q = {"created_by": user_id, "removed_ts": ""}
    return db_service.count_entries(q)


def entry_exists(db_service: MongoService, chat_id: int, jobname: str) -> bool:
    return find_entry_by_jobname(db_service, chat_id, jobname) is not None


"""
Setters
"""


def add_new_entry(
    db_service: MongoService,
    chat_id: int,
    jobname: str,  # must have jobname for /delete
    user_id: int,
    channel_id: str = "",
    crontab: str = "",
    content: str = "",
    content_type: str = "",
    photo_id: str = "",
    photo_group_id: str = "",
    nextrun_ts: str = "",
    user_nextrun_ts: str = "",
    user_bot_token: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    errors: List[Exception] = [],
) -> None:
    db_service.insert_new_entry(
        {
            "created_by": user_id,
            "last_updated_by": user_id,
            "chat_id": chat_id,
            "channel_id": channel_id,
            "jobname": jobname,
            "crontab": crontab,
            "content": content,
            "content_type": content_type,
            "photo_id": photo_id,
            "photo_group_id": photo_group_id,
            "previous_message_id": "",
            "option_delete_previous": "",
            "nextrun_ts": nextrun_ts,
            "user_nextrun_ts": user_nextrun_ts,
            "removed_ts": "",
            "remarks": "",
            "user_bot_token": user_bot_token,
            "message_thread_id": message_thread_id,
            "errors": errors,
        }
    )

    log.log_new_entry(jobname, chat_id)


def update_entry_by_jobname(db_service: MongoService, entry: COLLECTION_TYPE, update: QUERY_TYPE):
    q = {
        "created_ts": entry["created_ts"],
        "chat_id": entry["chat_id"],
        "jobname": entry["jobname"],
        "removed_ts": "",
    }
    return db_service.update_entry(q, update)


def update_entry_by_jobid(
    db_service: MongoService, entry_id: int, update: QUERY_TYPE, include_removed: bool = False
) -> Any:
    q: Dict[str, Any] = {"_id": entry_id}
    if not include_removed:
        q["removed_ts"] = ""
    return db_service.update_entry(q, update)


def remove_entries_by_chat(db_service: MongoService, chat_id: int) -> None:
    q = {"chat_id": float(chat_id)}
    payload = {"removed_ts": utils.now()}
    db_service.update_multiple_entries(q, payload)
