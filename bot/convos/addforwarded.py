from typing import Optional
from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from common import utils
from bot.convos import convo
from bot import replies
from config import BOT_NAME
from database import mongo
from database.dbutils import dbutils
from telegram.ext import ConversationHandler
from bot import replies
from common import log
from common.enums import ContentType
from database import mongo
from telegram import Update
from typing import Optional


async def add_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    if update.message is None:
        return ConversationHandler.END

    # forward_from_chat field is populated only for channels
    forwarded_chat_info = update.message.forward_from_chat
    if forwarded_chat_info is None:
        return ConversationHandler.END

    # channel jobs can only be set up from private chats
    if update.message.chat.type != "private":
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    chat_id = update.message.chat.id

    # timezone must be defined in order to create new job
    chat_entry = await dbutils.find_chat_by_chatid(db_service, chat_id)
    if chat_entry is None:
        await replies.text(update, replies.prompt_start_message)
        return ConversationHandler.END

    # add chat to db
    chat_exists = await dbutils.chat_exists(db_service, forwarded_chat_info.id)
    user_id = update.message.from_user.id
    if not chat_exists:
        res = await dbutils.add_chat_data(
            db_service,
            chat_id=forwarded_chat_info.id,
            chat_title=forwarded_chat_info.title,
            chat_type=forwarded_chat_info.type,
            tz_offset=chat_entry.get("tz_offset"),
            utc_tz=chat_entry.get("utc_tz"),
            created_by=user_id,
            telegram_ts=update.message.date,
        )
        if res is None:
            log.logger.error(
                f'[BOT] Failed to insert new chat "{forwarded_chat_info.id}"'
            )
            await replies.text(replies.internal_failure_message)
            return ConversationHandler.END

    # new job to be created, assert job limit
    job_count, user_limit = await dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        await replies.text(update, replies.format_exceed_limit_reply(user_limit))
        return ConversationHandler.END

    # add new job
    payload = {
        "user_id": user_id,
        "user_bot_token": chat_entry.get("user_bot_token"),  # TODO - check which
        "tz_offset": chat_entry.get("tz_offset"),
        "utc_tz": chat_entry.get("utc_tz"),
        "channel_id": forwarded_chat_info.id,
    }

    if update.message.poll:
        if update.message.poll.type == "quiz":
            await replies.text(update, replies.quiz_unavailable_message)
            return ConversationHandler.END
        payload["content_type"] = ContentType.POLL.value
        payload["content"] = update.message.poll.to_json()
    elif update.message.photo:  # single photo
        payload["photo_id"] = update.message.photo[-1].file_id
        payload["photo_group_id"] = update.message.media_group_id
        caption = "" if update.message.caption is None else update.message.caption_html
        payload["content"] = caption
        payload["content_type"] = ContentType.PHOTO.value
    elif update.message.text:  # only text
        payload["content"] = update.message.text_html
        payload["content_type"] = ContentType.TEXT.value
    else:
        await replies.text(update, replies.type_unavailable_message)
        return ConversationHandler.END

    # populate jobname for channels
    payload["jobname"] = await generate_jobname(
        db_service, forwarded_chat_info.title[:6], chat_id
    )

    context.chat_data[user_id] = payload

    await replies.text(
        update, replies.request_crontab_message, reply_markup=replies.keyboards.cron
    )
    return convo.states.s0


# helpers


async def generate_jobname(
    db_service: mongo.MongoService, job_prefix: str, chat_id: int
) -> str:
    number = 1
    jobname = "%s (%d)" % (job_prefix, number)
    while await dbutils.entry_exists(db_service, chat_id, jobname):
        number = number + 1
        jobname = "%s (%d)" % (job_prefix, number)
    return jobname
