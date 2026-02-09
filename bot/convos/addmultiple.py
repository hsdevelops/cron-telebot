from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot.convos import addforwarded, convo
from bot import replies
from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from bot.convos import permissions
from typing import Optional
from telegram.ext import ConversationHandler


async def command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /addmultiple is issued."""
    if update.message is None:
        return ConversationHandler.END

    await replies.text(
        update, replies.request_jobs_message, reply_markup=replies.force_reply
    )
    return convo.states.s0


async def add_jobs(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Exception]:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    msg = update.message
    if msg is None:
        return ConversationHandler.END

    # parse user response
    res = utils.extract_jobs(msg.text_html)
    new_job_count = len(res)

    # person limit
    user_id = msg.from_user.id
    current_job_count, user_limit = await dbutils.get_user_limit(db_service, user_id)
    if current_job_count + new_job_count > user_limit:
        await replies.text(update, replies.format_exceed_limit_reply(user_limit))
        return ConversationHandler.END

    # timezone must be defined in order to create new job
    chat_id = msg.chat.id
    chat_entry = await dbutils.find_chat_by_chatid(db_service, chat_id)
    if chat_entry is None:
        await replies.text(update, replies.prompt_start_message)
        return ConversationHandler.END

    successful_creation = []
    user_timezone = chat_entry.get("utc_tz")
    user_tz_offset = chat_entry.get("tz_offset")
    for crontab, text_content in res:
        # arrange next run date and time
        try:
            user_nextrun, db_nextrun = utils.calc_next_run(
                crontab, user_timezone, user_tz_offset
            )
        except Exception:
            continue

        jobname = await addforwarded.generate_jobname(
            db_service, msg.chat.type, chat_id
        )
        res = await dbutils.add_new_entry(
            db_service,
            chat_id=chat_id,
            jobname=jobname,
            user_id=user_id,
            crontab=crontab,
            content=text_content,
            content_type=ContentType.TEXT.value,
            nextrun_ts=db_nextrun,
            user_nextrun_ts=user_nextrun,
            user_bot_token=chat_entry.get("user_bot_token"),
            message_thread_id=msg.message_thread_id if msg.is_topic_message else None,
        )
        if res is not None:
            successful_creation.append("%s: (%s) %s" % (jobname, crontab, text_content))

    if len(successful_creation) <= 0:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    log.logger.info(
        f'[BOT] User "{msg.from_user.id}" added several jobs "{" // ".join(successful_creation)}" in room "{msg.chat.title}", chat_id={msg.chat.id}'
    )
    postfix = "\n".join("• %s" % x for x in successful_creation)
    await replies.text(update, replies.jobs_creation_success_message + postfix)
    return ConversationHandler.END
