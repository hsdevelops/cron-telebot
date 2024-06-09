from cron_descriptor import get_description
from bot.actions import permissions
from telegram.ext._contexttypes import ContextTypes
from telegram import Update

import config
from bot.replies import replies
from database import mongo
from database.dbutils import dbutils


async def show_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return

    chat_id = update.message.chat.id
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, update.message.text)
    if entry is None:
        await replies.send_error_message(update)

    bot_name = config.BOT_NAME
    if entry.get("user_bot_token") is not None:
        bot_data = dbutils.find_bot_by_token(db_service, entry.get("user_bot_token"))
        bot_name = "@%s" % bot_data["username"]

    await replies.send_job_details(update, entry, bot_name)


async def decrypt_cron(update: Update, _: ContextTypes) -> None:
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return await replies.send_checkcron_invalid_message(update)

    await replies.send_checkcron_meaning_message(update, description)
