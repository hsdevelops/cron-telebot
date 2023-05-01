from bot.replies import replies
from config import TZ_OFFSET
from common import log, utils
from database import mongo
from datetime import datetime, timezone, timedelta
from bot.actions.permissions import check_rights
from database.dbutils import dbutils


def reset_chat(update, context):
    db_service = mongo.MongoService(update)

    if not check_rights(update, context, db_service):
        return

    chat_id = update.callback_query.message.chat_id
    dbutils.remove_entries_by_chat(db_service, chat_id)

    log.log_chat_reset(update)
    replies.send_reset_success_message(context, chat_id)


def remove_job(update, context):
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))

    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    chat_id = update.message.chat.id
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, update.message.text)

    if entry is None:
        return replies.send_error_message(update)

    last_updated_by = update.message.from_user.id
    payload = {
        "removed_ts": utils.parse_time_millis(now),
        "last_updated_by": last_updated_by,
    }
    dbutils.update_entry_by_jobname(db_service, entry, payload)

    log.log_job_removed(last_updated_by, entry.get("jobname"), chat_id)
    replies.send_delete_success_message(update)
