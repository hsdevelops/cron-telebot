from database.mongo import MongoService
from telegram import Update

from email import utils
from common import log, utils
from database.consts import COLLECTION_TYPE
from typing import Any


"""
Getters
"""


def retrieve_user_data(db_service: MongoService, user_id: int) -> COLLECTION_TYPE:
    q = {"user_id": float(user_id), "superseded_at": ""}
    return db_service.find_one_user(q)


"""
Setters
"""


def add_user(db_service: MongoService, user_id: int, username: str, first_name: str) -> None:
    new_doc = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "superseded_at": "",
        "field_changed": "",
    }
    db_service.insert_new_user(new_doc)
    log.log_new_user(user_id, username)


def supersede_user(db_service: MongoService, entry: COLLECTION_TYPE, field_changed: Any) -> None:
    # update previous entry
    q = {"_id": entry["_id"]}
    payload = {"superseded_at": utils.now(), "field_changed": field_changed}
    db_service.update_one_user(q, payload)
    log.log_user_updated(entry)


def refresh_user(db_service: MongoService, entry: COLLECTION_TYPE) -> None:
    q = {"_id": entry["_id"]}
    payload = {"last_used_at": utils.now()}
    db_service.update_one_user(q, payload)


def sync_user_data(db_service: MongoService, update: Update) -> None:
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
        return log.log_username_updated(update)

    # check that firstname hasn't changed
    if update.message.from_user.first_name != str(user.get("first_name", "")):
        supersede_user(db_service, user, "first_name")
        add_user(db_service, user_id, username, first_name)
        return log.log_firstname_updated(update)

    refresh_user(db_service, user)
