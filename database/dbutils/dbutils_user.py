from telegram import Update

from email import utils
from common import log, utils
from typing import Any, Optional


MongoService = (
    Any  # Placeholder for the actual MongoService class due to cyclic imports
)


"""
Getters
"""


async def retrieve_user_data(db_service: MongoService, user_id: int) -> Optional[Any]:
    q = {"user_id": float(user_id), "superseded_at": ""}
    return await db_service.find_one_user(q)


"""
Setters
"""


async def add_user(
    db_service: MongoService, user_id: int, username: str, first_name: str
) -> None:
    new_doc = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "superseded_at": "",
        "field_changed": "",
    }
    await db_service.insert_new_user(new_doc)
    log.logger.info(f'[DB] Created new user, user_id={user_id}, username="{username}"')


async def supersede_user(
    db_service: MongoService, entry: Optional[Any], field_changed: Any
) -> None:
    # update previous entry
    q = {"_id": entry["_id"]}
    payload = {"superseded_at": utils.now(), "field_changed": field_changed}
    await db_service.update_one_user(q, payload)
    log.logger.info(
        f'[DB] Superseded user, user_id={entry.get("user_id")}, field_changed="{entry.get("field_changed")}"'
    )


async def refresh_user(db_service: MongoService, entry: Optional[Any]) -> None:
    q = {"_id": entry["_id"]}
    payload = {"last_used_at": utils.now()}
    await db_service.update_one_user(q, payload)


async def sync_user_data(db_service: MongoService, update: Update) -> None:
    if update.message is None:
        return
    user = retrieve_user_data(db_service, update.message.from_user.id)

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name

    if user is None:
        # user is new, add to db
        return add_user(db_service, user_id, username, first_name)

    # check that username hasn't changed
    previous_username = (
        None if user.get("username", "") == "" else user.get("username", "")
    )  # username could be None
    if update.message.from_user.username != previous_username:
        supersede_user(db_service, user, "username")
        add_user(db_service, user_id, username, user.get("first_name", ""))
        sync_user_data(db_service, update)
        log.logger.info(
            f"[DB] Superseded username, new username={update.message.from_user.username}, user_id={update.message.from_user.id}"
        )
        return

    # check that firstname hasn't changed
    if update.message.from_user.first_name != str(user.get("first_name", "")):
        supersede_user(db_service, user, "first_name")
        add_user(db_service, user_id, username, first_name)
        log.logger.info(
            f"[DB] Superseded first_name, new first_name={update.message.from_user.first_name}, username={update.message.from_user.username}, user_id={update.message.from_user.id}"
        )
        return

    refresh_user(db_service, user)
