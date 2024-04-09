from cron_descriptor import get_description
from bot.actions import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram import Update

import config
from bot.replies import replies
from database import mongo
from common import utils
from database.dbutils import dbutils


async def show_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return

    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    msg_text = utils.get_msg_text_from_update(update)
    if msg_text is None:
        return

    entry = dbutils.find_entry_by_jobname(db_service, chat_id, msg_text)
    if entry is None:
        await replies.send_error_message(update)

    bot_name = config.BOT_NAME
    if entry.get("user_bot_token") is not None:
        bot_data = dbutils.find_bot_by_token(
            db_service, entry.get("user_bot_token"))
        bot_name = "@%s" % bot_data["username"]

    await replies.send_job_details(update, entry, bot_name)


async def decrypt_cron(update: Update, _: ContextTypes.DEFAULT_TYPE):
    msg_text = utils.get_msg_text_from_update(update)
    if msg_text is None:
        return

    try:
        description = get_description(msg_text).lower()
    except Exception:  # crontab is not valid
        return await replies.send_checkcron_invalid_message(update)

    await replies.send_checkcron_meaning_message(update, description)
