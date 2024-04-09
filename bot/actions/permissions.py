from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from bot.replies import replies
from common.enums import Restriction
from database import mongo
from database.dbutils import dbutils
from common import utils
from typing import Optional


async def restrict_to_admins(update: Update, db_service: mongo.MongoService) -> None:
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    db_service = mongo.MongoService(update)
    entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    current_restriction = entry.get("restriction", "")

    if current_restriction == Restriction.ADMIN.value:
        dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return await replies.send_restrict_success_message(update, "everyone")

    if current_restriction == Restriction.OWNER.value:
        return await replies.send_wrong_restriction_message(
            update, "the current bot user"
        )

    payload = {"restriction": Restriction.ADMIN.value}
    dbutils.update_chat_entry(db_service, chat_id, payload)
    return await replies.send_restrict_success_message(update, "only group admins")


async def check_rights(update: Update, context: ContextTypes.DEFAULT_TYPE, db_service: mongo.MongoService, must_be_admin: bool = False):
    user_id = utils.get_user_id_from_update(update)
    if user_id is None:
        return False

    group_id = await get_chat_id(update, context)
    if group_id is None:
        return False

    entry = dbutils.find_chat_by_chatid(db_service, group_id)
    if entry is None:
        await replies.send_start_message(update)
        return False

    current_restriction = entry.get("restriction")
    is_creator = str(user_id) == str(entry.get("created_by", ""))
    if current_restriction == Restriction.OWNER.value and not is_creator:
        await replies.send_user_unauthorized_error_message(
            update, "the current bot user"
        )
        return False

    admin_roles = [Restriction.ADMIN.value, Restriction.OWNER.value]
    chat_member = await context.bot.get_chat_member(group_id, user_id)
    is_admin = chat_member.status in admin_roles
    must_be_admin = must_be_admin or current_restriction == Restriction.ADMIN.value
    if must_be_admin and not is_admin:
        await replies.send_user_unauthorized_error_message(update, "group admins")
        return False

    return True


async def restrict_to_user(update: Update, db_service: mongo.MongoService):
    # user running this command must be creator
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    user_id = utils.get_user_id_from_update(update)
    if user_id is None:
        return

    if str(user_id) != str(entry.get("created_by", "")):
        await replies.send_user_unauthorized_error_message(
            update, "the current bot user"
        )
        return

    current_restriction = entry.get("restriction", "")
    if current_restriction == Restriction.ADMIN.value:
        return await replies.send_wrong_restriction_message(update, "group admins")

    if current_restriction == Restriction.OWNER.value:
        dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return await replies.send_restrict_success_message(update, "everyone")

    dbutils.update_chat_entry(
        db_service, chat_id, {"restriction": Restriction.OWNER.value}
    )
    return await replies.send_restrict_success_message(update, "only you")


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    chat_id = -1
    if update.message is not None:  # text message
        return update.message.chat.id

    if update.callback_query is not None:  # callback message
        return utils.get_chat_id_from_update(update)

    if update.poll is not None:  # answer in Poll
        return context.bot_data[update.poll.id]

    return chat_id
