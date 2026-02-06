from telegram import Update

from email import utils
from common import log, utils
from typing import Any, Optional

from database.dbutils.dbutils_empty import empty_update_result
from database.mongo import MongoService
from pymongo.results import UpdateResult, InsertOneResult
from pymongo.errors import PyMongoError


"""
Getters
"""


async def retrieve_user_data(db_service: MongoService, user_id: int) -> Optional[Any]:
    q = {"user_id": float(user_id), "superseded_at": ""}
    try:
        return await db_service.find_one_user(q)
    except PyMongoError as e:
        log.logger.warning(f"[DB] retrieve_user_data failed: {type(e).__name__} - {e}")
        return None


"""
Setters
"""


async def add_user(
    db_service: MongoService, user_id: int, username: str, first_name: str
) -> InsertOneResult:
    new_doc = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "superseded_at": "",
        "field_changed": "",
    }
    try:
        res = await db_service.insert_new_user(new_doc)
        log.logger.info(
            f'[DB] Created new user, user_id={user_id}, username="{username}"'
        )
        return res
    except PyMongoError as e:
        log.logger.warning(f"[DB] add_user failed: {type(e).__name__} - {e}")
        return None


async def supersede_user(
    db_service: MongoService, entry: Optional[Any], field_changed: Any
) -> UpdateResult:
    if entry is None:
        log.logger.warning("[DB] supersede_user called with empty entry")
        return empty_update_result()

    if entry.get("_id") is None:
        log.logger.warning("[DB] supersede_user missing _id on entry")
        return empty_update_result()

    # update previous entry
    q = {"_id": entry["_id"]}
    payload = {"superseded_at": utils.now(), "field_changed": field_changed}

    try:
        res = await db_service.update_one_user(q, payload)
        log.logger.info(
            f'[DB] Superseded user, user_id={entry.get("user_id")}, field_changed="{entry.get("field_changed")}"'
        )
        return res
    except PyMongoError as e:
        log.logger.warning(f"[DB] supersede_user failed: {type(e).__name__} - {e}")
        return empty_update_result()


async def refresh_user(db_service: MongoService, entry: Optional[Any]) -> UpdateResult:
    if entry is None:
        log.logger.warning("[DB] refresh_user called with empty entry")
        return empty_update_result()

    if entry.get("_id") is None:
        log.logger.warning("[DB] refresh_user missing _id on entry")
        return empty_update_result()

    q = {"_id": entry["_id"]}
    payload = {"last_used_at": utils.now()}
    try:
        return await db_service.update_one_user(q, payload)
    except PyMongoError as e:
        log.logger.warning(f"[DB] refresh_user failed: {type(e).__name__} - {e}")
        return empty_update_result()


async def sync_user_data(db_service: MongoService, update: Update) -> None:
    if update.message is None:
        return
    try:
        user = await retrieve_user_data(db_service, update.message.from_user.id)
    except Exception as e:
        log.logger.warning(f"[DB] sync_user_data load failed: {type(e).__name__} - {e}")
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name

    if user is None:
        # user is new, add to db
        await add_user(db_service, user_id, username, first_name)
        return

    # check that username hasn't changed
    previous_username = (
        None if user.get("username", "") == "" else user.get("username", "")
    )  # username could be None
    if update.message.from_user.username != previous_username:
        await supersede_user(db_service, user, "username")
        await add_user(db_service, user_id, username, user.get("first_name", ""))
        await sync_user_data(db_service, update)
        log.logger.info(
            f"[DB] Superseded username, new username={update.message.from_user.username}, user_id={update.message.from_user.id}"
        )
        return

    # check that firstname hasn't changed
    if update.message.from_user.first_name != str(user.get("first_name", "")):
        await supersede_user(db_service, user, "first_name")
        await add_user(db_service, user_id, username, first_name)
        log.logger.info(
            f"[DB] Superseded first_name, new first_name={update.message.from_user.first_name}, username={update.message.from_user.username}, user_id={update.message.from_user.id}"
        )
        return

    await refresh_user(db_service, user)
