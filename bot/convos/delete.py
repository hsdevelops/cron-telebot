from bot.convos import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram import Update

from bot.convos import convo
from bot import replies
from common import log, utils
from database import mongo
from database.dbutils import dbutils
from telegram.ext import ConversationHandler


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /delete is issued."""
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    entries = await dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        await replies.text(update, replies.simple_prompt_message)
        return ConversationHandler.END

    await replies.text(
        update,
        replies.delete_message,
        reply_markup=replies.keyboard_from_dict(entries, "jobname"),
    )
    return convo.states.s0


async def remove_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    chat_id = update.message.chat.id
    jobname = update.message.text
    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.missing_job_error_message % jobname)
        return ConversationHandler.END

    last_updated_by = update.message.from_user.id
    payload = {
        "removed_ts": utils.now(),
        "last_updated_by": last_updated_by,
    }
    res = await dbutils.update_entry_by_jobname(db_service, entry, payload)
    if res.modified_count <= 0:
        log.logger.error(f'[BOT] Failed to delete job, job_id={entry["_id"]}')
        await replies.text(update, replies.internal_failure_message)
        return ConversationHandler.END

    log.logger.info(
        f'[BOT] User "{last_updated_by}" removed job "{entry.get("jobname")}", chat_id={chat_id}'
    )
    await replies.text(update, replies.delete_success_message)
    return ConversationHandler.END
