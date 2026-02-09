import aiohttp
from telegram.ext import ConversationHandler
from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from bot.convos import convo
from bot import replies
from config import BOT_NAME
from database import mongo
from database.dbutils import dbutils
from common import log, utils
import teleapi.endpoints as teleapi
from typing import Any, Optional


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Send a message when the command /changesender is issued."""
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    # find groups/private/channel created by user
    user_id = update.message.from_user.id
    chat_type = update.message.chat.type

    if chat_type != "private":
        await replies.text(update, replies.private_only_error_message % BOT_NAME)
        return ConversationHandler.END

    chat_entries = await dbutils.find_groups_created_by(db_service, user_id)
    if len(chat_entries) <= 0:
        await replies.text(update, replies.missing_chats_error_message % BOT_NAME)
        return ConversationHandler.END

    await replies.text(
        update,
        replies.choose_chat_message,
        reply_markup=replies.keyboard_from_dict(chat_entries, "chat_title"),
    )
    return convo.states.s0


# state 0
async def choose_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]
    http_session: aiohttp.ClientSession = context.application.bot_data["http_session"]

    chat_title = str(update.message.text)
    user_id = update.message.from_user.id
    chat_entry = await dbutils.find_chat_by_title(db_service, user_id, chat_title)

    if chat_entry is None:
        await replies.text(update, replies.error_message)
        return convo.states.s0

    prev_token = chat_entry.get("user_bot_token")
    if prev_token is None:
        context.user_data["chat_id"] = chat_entry["chat_id"]
        context.user_data["chat_title"] = chat_entry["chat_title"]
        await replies.text(update, replies.prompt_user_bot_message)
        return convo.states.s1

    # Revert back to default — both chat and jobs
    has_err = await reset_sender(
        db_service, http_session, chat_entry["chat_id"], user_id, None, prev_token
    )
    if has_err:
        await replies.text(update, replies.missing_bot_in_group_message)
        return ConversationHandler.END
    await replies.text(update, replies.sender_reset_success_message)
    return ConversationHandler.END


# state 1
async def update_sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    new_token = str(update.message.text)
    user_id = update.message.from_user.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]
    http_session: aiohttp.ClientSession = context.application.bot_data["http_session"]

    # check if bot exists
    resp = await teleapi.get_bot_details(http_session, new_token)
    if resp.get("status") != 200:
        await replies.text(update, replies.error_message)
        return convo.states.s1

    bot_data = {
        **resp.get("json")["result"],
        "token": new_token,
        "created_by": user_id,
        "updated_at": utils.now(),
    }
    await dbutils.upsert_new_bot(db_service, user_id, bot_data)

    chat_id, chat_title = context.user_data["chat_id"], context.user_data["chat_title"]
    has_err = await reset_sender(
        db_service, http_session, chat_id, user_id, new_token, None
    )
    if has_err:
        await replies.text(update, replies.missing_bot_in_group_message)
        return ConversationHandler.END

    reply = replies.sender_change_success_message % (
        chat_title,
        bot_data["username"],
        bot_data["username"],
    )
    await replies.text(update, reply)
    return ConversationHandler.END


async def reset_sender(
    db_service: mongo.MongoService,
    http_session: aiohttp.ClientSession,
    chat_id: int,
    user_id: int,
    new_token: Optional[str],
    prev_token: Optional[Any] = None,
) -> bool:
    # special case — single photos can only be sent from the same bot
    single_photo_entries = await dbutils.find_entries_by_content_type(
        db_service, chat_id
    )
    for entry in single_photo_entries:
        resp, new_photo_id = await teleapi.transfer_photo_between_bots(
            http_session,
            db_service,
            new_token,
            prev_token,
            chat_id,
            entry["photo_id"],
            entry["_id"],
        )
        status = resp.get("status")
        if status != 200:
            return True
        log.logger.info(
            f'[BOT] User "{user_id}" transferred photo "{new_photo_id}", chat_id="{chat_id}", status={status}'
        )

    # jobs
    q = {"$or": [{"chat_id": chat_id}, {"channel_id": chat_id}]}
    payload = {"last_updated_by": user_id, "user_bot_token": new_token}
    await db_service.update_multiple_entries(q, payload)

    # chat
    field = "user_bot_token"
    payload = {"user_bot_token": new_token}
    await dbutils.update_chat_entry(db_service, chat_id, payload, updated_field=field)

    log.logger.info(
        f'[BOT] User "{user_id}" updated sender from "{prev_token}" to "{new_token}", chat_id={chat_id}'
    )
    return False
