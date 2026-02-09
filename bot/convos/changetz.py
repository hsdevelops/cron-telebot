from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot.convos import permissions
from bot.convos import convo
from bot import replies
from common import log, utils
from database import mongo
from database.dbutils import dbutils
from telegram.ext import ConversationHandler


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /changetz is issued."""
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    # timezone must be defined in order to change tz
    chat_entry = await dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    if chat_entry is None:
        await replies.text(update, replies.prompt_start_message)
        return ConversationHandler.END

    await replies.text(
        update, replies.change_timezone_message, reply_markup=replies.force_reply
    )
    return convo.states.s0


async def update_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    user_id = update.message.from_user.id

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    # check validity
    timezone, tz_offset, err = utils.extract_timezone(update.message.text)
    if err is not None:
        await replies.text(update, replies.invalid_timezone_message)
        return ConversationHandler.END

    chat_id = update.message.chat.id
    chat_type = update.message.chat.type

    # update chat entry
    payload = {"tz_offset": tz_offset, "utc_tz": timezone}
    res = await dbutils.update_chat_entry(db_service, chat_id, payload, "utc_tz")
    if res.modified_count <= 0:
        log.logger.error(
            f"[BOT] Failed to update chat entry, chat_id = {chat_id}, payload = {payload}"
        )
        await replies.text(update, replies.internal_failure_message)
        return ConversationHandler.END

    if chat_type == "private":
        res = await dbutils.update_chats_tz_by_type(
            db_service, user_id, tz_offset, "channel", utc_tz=timezone
        )

    # update job entries
    job_entries = await dbutils.find_entries_by_chatid(db_service, chat_id)
    for job_entry in job_entries:
        if job_entry.get("nextrun_ts", "") == "":
            continue
        crontab = job_entry.get("crontab", "")
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, timezone, tz_offset
        )
        payload = {"nextrun_ts": db_nextrun_ts, "user_nextrun_ts": user_nextrun_ts}
        res = await dbutils.update_entry_by_jobname(db_service, job_entry, payload)
        if res.modified_count <= 0:
            log.logger.error(
                f'[BOT] Failed to update job entry, chat_id = {job_entry["_id"]}, payload = {payload}'
            )
            await replies.text(update, replies.internal_failure_message)
            return ConversationHandler.END

    await replies.text(
        update,
        replies.timezone_change_success_message
        % utils.format_timezone(timezone, tz_offset),
    )
    return ConversationHandler.END
