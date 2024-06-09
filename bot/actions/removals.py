from datetime import datetime, timezone, timedelta
from bot.actions import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram import Update

from bot.replies import replies
from config import TZ_OFFSET
from common import log, utils
from database import mongo
from database.dbutils import dbutils


async def reset_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_service = mongo.MongoService(update)

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return

    chat_id = update.callback_query.message.chat_id
    dbutils.remove_entries_by_chat(db_service, chat_id)

    log.log_chat_reset(update)
    await replies.send_reset_success_message(context, chat_id)


async def remove_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return

    chat_id = update.message.chat.id
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, update.message.text)

    if entry is None:
        return await replies.send_error_message(update)

    last_updated_by = update.message.from_user.id
    payload = {
        "removed_ts": utils.now(),
        "last_updated_by": last_updated_by,
    }
    dbutils.update_entry_by_jobname(db_service, entry, payload)

    log.log_job_removed(last_updated_by, entry.get("jobname"), chat_id)
    await replies.send_delete_success_message(update)
