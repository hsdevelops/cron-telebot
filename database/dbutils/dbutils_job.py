from pymongo import ASCENDING, DESCENDING
from common import utils, log
from common.enums import ContentType
from database.dbutils.dbutils_empty import empty_update_result
from database.mongo import MongoService
from typing import List, Optional, Dict, Any
from pymongo.results import UpdateResult, InsertOneResult
from pymongo.errors import PyMongoError


"""
Queries
"""


def make_due_jobs_query(ts: str):
    base_q = {"nextrun_ts": {"$lte": ts}, "removed_ts": "", "crontab": {"$ne": ""}}
    # Only return messages that are not pending, or pending for more than 5 mins.
    base_q["$or"] = [{"pending_ts": None}, {"pending_ts": {"$lte": utils.now(-5)}}]
    return {
        "$or": [
            {"paused_ts": "", **base_q},
            {"paused_ts": {"$exists": False}, **base_q},
        ]
    }


"""
Getters
"""


async def find_latest_entry(db_service: MongoService, chat_id: int) -> Optional[Any]:
    q = {"chat_id": float(chat_id), "removed_ts": ""}
    try:
        result = await db_service.find_entries(q, [("created_ts", DESCENDING)])
        if len(result) <= 0:
            return None
        return result[0]
    except PyMongoError as e:
        log.logger.warning(f"[DB] find_latest_entry failed: {type(e).__name__} - {e}")
        return None


async def find_entry_by_jobname(
    db_service: MongoService, chat_id: int, jobname: str, include_removed: bool = False
) -> Optional[Any]:
    q = {"chat_id": float(chat_id), "jobname": jobname}
    if not include_removed:
        q["removed_ts"] = ""
    try:
        return await db_service.find_one_entry(q)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] find_entry_by_jobname failed: {type(e).__name__} - {e}"
        )
        return None


async def find_entries_removed_between(
    db_service: MongoService,
    start_ts: str,
    end_ts: str,
    err_status: Optional[int] = None,
) -> List[Optional[Any]]:
    q = {"removed_ts": {"$gte": start_ts, "$lte": end_ts}}
    if err_status is not None:
        q["errors.error"] = {"$regex": f"^Error {err_status}"}
    try:
        return await db_service.find_entries(q)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] find_entries_removed_between failed: {type(e).__name__} - {e}"
        )
        return []


async def find_entries_by_nextrun(
    db_service: MongoService, ts: str
) -> List[Optional[Any]]:
    q = make_due_jobs_query(ts)
    try:
        return await db_service.find_entries(q, [("created_at", ASCENDING)])
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] find_entries_by_nextrun failed: {type(e).__name__} - {e}"
        )
        return []


async def find_entries_by_content_type(
    db_service: MongoService, chat_id: int, content_type: str = ContentType.PHOTO.value
) -> List[Optional[Any]]:
    q = {
        "$or": [{"chat_id": chat_id}, {"channel_id": chat_id}],
        "removed_ts": "",
        "content_type": content_type,
    }
    try:
        return await db_service.find_entries(q)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] find_entries_by_content_type failed: {type(e).__name__} - {e}"
        )
        return []


async def find_entries_by_chatid(
    db_service: MongoService, chat_id: int
) -> List[Optional[Any]]:
    q = {"chat_id": float(chat_id), "removed_ts": ""}
    try:
        return await db_service.find_entries(q)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] find_entries_by_chatid failed: {type(e).__name__} - {e}"
        )
        return []


async def count_entries_by_userid(db_service: MongoService, user_id: int) -> int:
    q = {"created_by": user_id, "removed_ts": ""}
    try:
        return await db_service.count_entries(q)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] count_entries_by_userid failed: {type(e).__name__} - {e}"
        )
        return 0


async def entry_exists(db_service: MongoService, chat_id: int, jobname: str) -> bool:
    try:
        return await find_entry_by_jobname(db_service, chat_id, jobname) is not None
    except PyMongoError as e:
        log.logger.warning(f"[DB] entry_exists failed: {type(e).__name__} - {e}")
        return False


"""
Setters
"""


async def add_new_entry(
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
) -> Optional[InsertOneResult]:
    result = None
    try:
        result = await db_service.insert_new_entry(
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
                "pending_ts": None,
                "removed_ts": "",
                "remarks": "",
                "user_bot_token": user_bot_token,
                "message_thread_id": message_thread_id,
                "errors": errors,
            }
        )
        log.logger.info(f'[DB] Created new job, jobname="{jobname}", chat_id={chat_id}')
    except PyMongoError as e:
        log.logger.warning(f"[DB] add_new_entry failed: {type(e).__name__} - {e}")

    return result


async def update_entry_by_jobname(
    db_service: MongoService, entry: Optional[Any], update: Optional[Any], q: Dict = {}
) -> UpdateResult:
    if entry is None:
        log.logger.warning("[DB] update_entry_by_jobname called with empty entry")
        return empty_update_result()

    created_ts = entry.get("created_ts")
    chat_id = entry.get("chat_id")
    jobname = entry.get("jobname")
    if created_ts is None or chat_id is None or jobname is None:
        log.logger.warning(
            "[DB] update_entry_by_jobname missing required fields on entry"
        )
        return empty_update_result()

    try:
        q = {
            **q,
            "created_ts": created_ts,
            "chat_id": chat_id,
            "jobname": jobname,
            "removed_ts": "",
        }
        return await db_service.update_entry(q, update)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] update_entry_by_jobname failed: {type(e).__name__} - {e}"
        )
        return empty_update_result()


async def update_entry_by_jobid(
    db_service: MongoService,
    entry_id: int,
    update: Optional[Any],
    include_removed: bool = False,
) -> UpdateResult:
    q: Dict[str, Any] = {"_id": entry_id}
    if not include_removed:
        q["removed_ts"] = ""
    try:
        return await db_service.update_entry(q, update)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] update_entry_by_jobid failed: {type(e).__name__} - {e}"
        )
        return empty_update_result()


async def remove_entries_by_chat(
    db_service: MongoService, chat_id: int
) -> UpdateResult:
    q = {"chat_id": float(chat_id)}
    payload = {"removed_ts": utils.now()}
    try:
        return await db_service.update_multiple_entries(q, payload)
    except PyMongoError as e:
        log.logger.warning(
            f"[DB] remove_entries_by_chat failed: {type(e).__name__} - {e}"
        )
        return empty_update_result()
