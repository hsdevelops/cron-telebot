import aiohttp
from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot.convos import permissions
from bot.convos import convo
from bot import replies
from config import TELEGRAM_BOT_TOKEN
from database import mongo
from database.dbutils import dbutils
from telegram.ext import ConversationHandler
from bot.convos import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from common import log
from teleapi import endpoints as teleapi


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /reset is issued."""
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    entries = await dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:  # there must be at least one job available
        await replies.text(update, replies.simple_prompt_message)
        return ConversationHandler.END

    payload = {"message_thread_id": update.message.message_thread_id}
    user_id = update.message.from_user.id
    context.chat_data[user_id] = payload

    await replies.text(
        update,
        replies.reset_confirmation_message,
        reply_markup=replies.keyboards.inline_default,
    )
    return convo.states.s0


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]
    http_session: aiohttp.ClientSession = context.application.bot_data["http_session"]

    user_id = update.message.from_user.id
    payload = context.chat_data[user_id]

    query = update.callback_query
    chat_id = query.message.chat_id

    if query.data == "1":
        res = await dbutils.remove_entries_by_chat(db_service, chat_id)
        # if res.modified_count <= 0:
        log.logger.info(
            f'[BOT] User "{query.from_user.id}" reset chat, chat_id={chat_id}'
        )
        await teleapi.send_text(
            http_session,
            chat_id,
            replies.reset_success_messge,
            TELEGRAM_BOT_TOKEN,
            payload["message_thread_id"],
        )
    else:
        await teleapi.send_text(
            http_session,
            chat_id,
            replies.convo_ended_message,
            TELEGRAM_BOT_TOKEN,
            payload["message_thread_id"],
        )

    await context.bot.editMessageReplyMarkup(
        chat_id=chat_id, message_id=query.message.message_id
    )
    await query.answer()
    context.chat_data.pop(user_id, None)
    return ConversationHandler.END
