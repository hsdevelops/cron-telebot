from bot.replies import replies
from config import TZ_OFFSET
from common import log, utils
from database import mongo
from datetime import datetime, timezone, timedelta
from bot.actions.permissions import check_rights


def reset_chat(update, context):
    db_service = mongo.MongoService(update)

    if not check_rights(update, context, db_service):
        return

    chat_id = update.callback_query.message.chat_id
    db_service.remove_entries_by_chat(chat_id)

    log.log_chat_reset(update)
    replies.send_reset_success_message(context, chat_id)


def remove_job(update, context):
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))

    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    chat_id = update.message.chat.id
    entry = db_service.get_one_entry(chat_id, update.message.text)

    if entry is None:
        return replies.send_error_message(update)

    last_updated_by = update.message.from_user.id
    fields = {
        "removed_ts": utils.parse_time_millis(now),
        "last_updated_by": last_updated_by,
    }
    db_service.update_entry(mongo.entry_filter(entry), fields)

    log.log_job_removed(last_updated_by, entry.get("jobname"), chat_id)
    replies.send_delete_success_message(update)
