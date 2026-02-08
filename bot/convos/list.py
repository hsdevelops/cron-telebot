from bot.convos import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram.ext import ConversationHandler
from telegram import Update

from bot.convos import convo
import config
from bot import replies
from database import mongo
from database.dbutils import dbutils


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /list is issued."""
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    entries = await dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        await replies.text(update, replies.simple_prompt_message)
        return ConversationHandler.END

    await replies.text(
        update,
        replies.list_jobs_message,
        reply_markup=replies.keyboard_from_dict(entries, "jobname"),
    )
    return convo.states.s0


async def show_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    chat_id = update.message.chat.id
    jobname = update.message.text
    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.missing_job_error_message % jobname)
        return ConversationHandler.END

    bot_name = config.BOT_NAME
    if entry.get("user_bot_token") is not None:
        bot_data = await dbutils.find_bot_by_token(
            db_service, entry.get("user_bot_token")
        )
        bot_name = f'@{bot_data["username"]}'

    reply = replies.format_job_detail(entry, bot_name)
    await replies.text(update, reply)
    return ConversationHandler.END
