import aiohttp
from cron_descriptor import get_description
from telegram.ext import ConversationHandler
from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from common import utils
from bot.convos import convo, permissions
from bot import replies
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from common import log
from typing import Optional
from teleapi.endpoints import transfer_photo_between_bots


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Send a message when the command /add is issued."""
    if update.message is None:
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    # timezone must be defined in order to create new job
    chat_entry = await dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    if chat_entry is None:
        await replies.text(update, replies.prompt_start_message)
        return ConversationHandler.END

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    user_id = update.message.from_user.id
    payload = {
        "user_id": update.message.from_user.id,
        "user_bot_token": chat_entry.get("user_bot_token"),
        "message_thread_id": update.message.message_thread_id
        if update.message.is_topic_message
        else None,
        "tz_offset": chat_entry.get("tz_offset"),
        "utc_tz": chat_entry.get("utc_tz"),
    }

    # person limit
    user_id = update.message.from_user.id
    job_count, user_limit = await dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        await replies.text(update, replies.format_exceed_limit_reply(user_limit))
        return ConversationHandler.END

    context.chat_data[user_id] = payload

    await replies.text(
        update, replies.request_jobname_message, reply_markup=replies.force_reply
    )
    return convo.states.s0


# state 0
async def add_jobname(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    if update.message is None:
        if update.effective_user is not None:
            context.chat_data.pop(update.effective_user.id, None)
        return ConversationHandler.END

    user_id = update.message.from_user.id
    payload = context.chat_data[user_id]

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    # check name does not already exist
    chat_id = update.message.chat.id
    if await dbutils.entry_exists(db_service, chat_id, update.message.text):
        await replies.text(update, replies.invalid_new_job_message)
        context.chat_data.pop(user_id, None)
        return ConversationHandler.END

    payload["jobname"] = update.message.text
    context.chat_data[user_id] = payload

    await replies.text(
        update, replies.request_text_message, reply_markup=replies.force_reply
    )
    return convo.states.s1


# state 1
async def add_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        if update.effective_user is not None:
            context.chat_data.pop(update.effective_user.id, None)
        return ConversationHandler.END

    user_id = update.message.from_user.id
    payload = context.chat_data[user_id]

    if (
        update.message.poll
        and update.message.poll.type == "quiz"
        and update.message.chat.type != "private"
    ):
        await replies.text(update, replies.quiz_unavailable_message)
        context.chat_data.pop(user_id, None)
        return ConversationHandler.END

    payload = context.chat_data[user_id]

    if update.message.poll:
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
        context.chat_data.pop(user_id, None)
        return ConversationHandler.END

    context.chat_data[user_id] = payload

    await replies.text(
        update, replies.request_crontab_message, reply_markup=replies.keyboards.cron
    )
    return convo.states.s2


# state 2
async def add_photo_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.media_group_id is None:
        return None  # continue waiting for crontab

    user_id = update.message.from_user.id
    payload = context.chat_data[user_id]

    photo_group_id = update.message.media_group_id
    if photo_group_id != payload.get("photo_group_id"):
        return None  # continue waiting for crontab

    # triggered from the next state
    photo_id = update.message.photo[-1].file_id
    photo_ids = "{};{}".format(payload.get("photo_id", ""), photo_id)
    payload["photo_id"] = photo_ids
    payload["content_type"] = ContentType.MEDIA.value
    context.chat_data[user_id] = payload
    return None  # continue waiting for crontab


async def add_crontab(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    if update.message is None:
        if update.effective_user is not None:
            context.chat_data.pop(update.effective_user.id, None)
        return ConversationHandler.END

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    user_id = update.message.from_user.id
    payload = context.chat_data[user_id]

    user_timezone = payload["utc_tz"]
    user_tz_offset = payload["tz_offset"]

    crontab = update.message.text
    try:
        description = get_description(crontab).lower()
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, user_timezone, user_tz_offset
        )
    except Exception as e:  # crontab is not valid
        log.logger.info(
            f"[BOT] Invalid crontab received, crontab = {crontab}, err = {e}"
        )
        await replies.text(
            update, replies.invalid_crontab_message, reply_markup=replies.force_reply
        )
        return None

    # update db entry
    chat_id = update.message.chat.id
    jobname = payload["jobname"]
    user_id = payload["user_id"]
    user_bot_token = payload.get("user_bot_token", None)
    channel_id = payload.get("channel_id", None)
    result = await dbutils.add_new_entry(
        db_service,
        chat_id=chat_id,
        channel_id=channel_id,
        jobname=jobname,
        user_id=user_id,
        crontab=crontab,
        content=payload["content"],
        content_type=payload["content_type"],
        photo_group_id=payload.get("photo_group_id", ""),
        photo_id=payload.get("photo_id", ""),
        nextrun_ts=db_nextrun_ts,
        user_nextrun_ts=user_nextrun_ts,
        user_bot_token=user_bot_token,
        message_thread_id=payload.get("message_thread_id", None),
    )

    if result is None:
        log.logger.error(
            f'[BOT] Failed to insert new job "{jobname}" for user "{user_id}", chat_id={chat_id}'
        )
        await replies.text(replies.internal_failure_message)
        context.chat_data.pop(user_id, None)
        return ConversationHandler.END

    payload["_id"] = result.inserted_id
    log.logger.info(
        f'[BOT] User "{user_id}" added new job "{jobname}" {"" if channel_id is None else "via forwarding"}, job_id={result.inserted_id}, chat_id={chat_id}'
    )

    # special case — transfer photo ownership to new sender
    http_session: aiohttp.ClientSession = context.application.bot_data["http_session"]
    photo_ids = payload.get("photo_id", None)
    if photo_ids is not None and user_bot_token is not None:
        for photo_id in str.split(photo_ids, ";"):
            resp, new_photo_id = await transfer_photo_between_bots(
                http_session,
                db_service,
                user_bot_token,
                None,
                chat_id,
                photo_id,
                result.inserted_id,
            )
            log.logger.info(
                f'[BOT] User "{user_id}" transferred photo "{new_photo_id}", chat_id="{chat_id}", status={resp.get("status")}'
            )

    await replies.text(update, replies.format_add_success_message(payload, description))
    context.chat_data.pop(user_id, None)
    return ConversationHandler.END
