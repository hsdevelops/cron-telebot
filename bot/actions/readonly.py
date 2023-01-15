from bot.replies import replies
from database import mongo
from cron_descriptor import get_description
from bot.actions.permissions import check_rights

def show_job_details(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    entry = db_service.get_one_entry(update.message.chat.id, update.message.text)

    if entry is None:
        replies.send_error_message(update)

    replies.send_job_details(update, entry)


def decrypt_cron(update):
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_checkcron_invalid_message(update)

    replies.send_checkcron_meaning_message(update, description)
