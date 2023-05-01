from bot.replies import replies
from database import mongo
from database.dbutils import dbutils
from cron_descriptor import get_description
from bot.actions.permissions import check_rights
import config


def show_job_details(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    chat_id = update.message.chat.id
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, update.message.text)
    if entry is None:
        replies.send_error_message(update)

    bot_name = config.BOT_NAME
    if entry.get("user_bot_token") is not None:
        bot_data = dbutils.find_bot_by_token(db_service, entry.get("user_bot_token"))
        bot_name = "@%s" % bot_data["username"]

    replies.send_job_details(update, entry, bot_name)


def decrypt_cron(update):
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_checkcron_invalid_message(update)

    replies.send_checkcron_meaning_message(update, description)
