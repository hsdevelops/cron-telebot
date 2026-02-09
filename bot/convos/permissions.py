from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from telegram.error import Forbidden, TelegramError
from bot import replies
from common import log
from common.enums import Restriction
from database import mongo
from database.dbutils import dbutils
from typing import Optional


async def check_rights(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_service: mongo.MongoService,
    must_be_admin: bool = False,
) -> bool:
    message = update.effective_message
    if message is None:
        return False

    user_id = message.from_user.id
    group_id = await get_chat_id(update, context)
    if group_id == -1:
        log.logger.warning("[BOT] Failed to resolve chat_id for permissions check")
        return False

    entry = await dbutils.find_chat_by_chatid(db_service, group_id)
    if entry is None:
        await replies.text(update, replies.prompt_start_message)
        return False

    current_restriction = entry.get("restriction") or ""

    # owner check
    is_creator = str(user_id) == str(entry.get("created_by", ""))
    if current_restriction == Restriction.OWNER.value:
        if is_creator:
            return True
        await replies.text(
            update, replies.user_unauthorized_error_message % "the current bot user"
        )
        return False

    must_be_admin = must_be_admin or current_restriction == Restriction.ADMIN.value
    if not must_be_admin:
        return True

    # admin check
    admin_roles = [Restriction.ADMIN.value, Restriction.OWNER.value]
    try:
        chat_member = await context.bot.get_chat_member(group_id, user_id)
    except Forbidden as e:
        log.logger.warning(
            f"[BOT] Admin required for permissions check, chat_id={group_id}, user_id={user_id}, err={e}"
        )
        await replies.text(update, replies.chat_admin_required_message)
        return False
    except TelegramError as e:
        log.logger.warning(
            f"[BOT] Telegram error during permissions check, chat_id={group_id}, user_id={user_id}, err={e}"
        )
        await replies.text(update, replies.internal_failure_message)
        return False

    is_admin = chat_member.status in admin_roles
    if is_admin:
        return True  # is admin

    await replies.text(update, replies.user_unauthorized_error_message % "group admins")
    return False


async def get_chat_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    chat_id = -1
    if update.message is not None:  # text message
        return update.message.chat.id
    elif update.callback_query is not None:  # callback message
        return update.callback_query.message.chat.id
    elif update.poll is not None:  # answer in Poll
        return context.bot_data[update.poll.id]
    return chat_id
