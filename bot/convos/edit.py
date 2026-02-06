import jsons
from telegram import Update
from telegram.ext import ConversationHandler
from telegram.ext._contexttypes import ContextTypes
from bot.convos import convo, permissions
from bot import replies
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from common import log, utils
from cron_descriptor import get_description
from typing import Dict, Tuple, Optional, Any

attr_cron = "crontab"
attr_jobname = "job name"
attr_content = "text content"
attr_add_photo = "add photo"
attr_del_photo = "remove all photos"
attr_del_prev = "toggle delete previous"
attr_pause_job = "pause/resume job"

attrs = [
    attr_cron,
    attr_jobname,
    attr_content,
    attr_add_photo,
    attr_del_photo,
    attr_del_prev,
    attr_pause_job,
]


async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Send a message when the command /edit is issued."""
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return ConversationHandler.END

    context.user_data["user_id"] = update.message.from_user.id

    entries = await dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        await replies.text(update, replies.simple_prompt_message)
        return ConversationHandler.END

    await replies.text(
        update,
        replies.choose_job_message,
        reply_markup=replies.keyboard_from_dict(entries, "jobname"),
    )
    return convo.states.s0


# state 0
async def choose_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    jobname = str(update.message.text)

    if not await dbutils.entry_exists(db_service, update.message.chat.id, jobname):
        await replies.text(update, replies.error_message)
        return convo.states.s0

    context.user_data["jobname"] = jobname
    await replies.text(
        update, replies.choose_attribute_message, reply_markup=replies.keyboards.attrs
    )
    return convo.states.s1


# state 1
async def choose_attribute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    attr = str(update.message.text)
    context.user_data["attribute"] = attr

    if attr not in attrs:
        await replies.text(update, replies.error_message)
        return convo.states.s1

    if attr == attr_del_prev:
        await toggle_delete_previous(update, context)
        return ConversationHandler.END

    if attr == attr_del_photo:
        await replies.text(
            update,
            replies.reset_photos_confirmation_message,
            reply_markup=replies.keyboard([["yes", "no"]]),
        )
        return convo.states.s4

    if attr == attr_pause_job:
        await toggle_pause_job(update, context)
        return ConversationHandler.END

    await replies.text(
        update, replies.prompt_new_value_message, reply_markup=replies.force_reply
    )

    if attr == attr_add_photo:
        return convo.states.s3

    return convo.states.s2


async def toggle_delete_previous(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.error_message)
        return

    new_option_value = "" if entry.get("option_delete_previous", "") != "" else True
    payload = {
        "option_delete_previous": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    option = "option_delete_previous"
    log.logger.info(
        f'[BOT] User "{payload["last_updated_by"]}" updated option "{option}" to "{payload[option]}" for job "{jobname}", chat_id={chat_id}'
    )
    await replies.text(update, replies.attribute_change_success_message)


async def toggle_pause_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.error_message)
        return

    new_option_value = "" if entry.get("paused_ts", "") != "" else utils.now()
    payload = {
        "paused_ts": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    if new_option_value == "":  # calculate next run
        crontab = entry.get("crontab")
        _, crontab_payload, err = await prepare_crontab_update(
            update, crontab, db_service
        )
        if err is not None:
            await replies.text(update, replies.attribute_change_error_message)
            return ConversationHandler.END
        payload = {
            "nextrun_ts": crontab_payload["nextrun_ts"],
            "user_nextrun_ts": crontab_payload["user_nextrun_ts"],
            **payload,
        }
    await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    option = "paused_ts"
    log.logger.info(
        f'[BOT] User "{payload["last_updated_by"]}" updated option "{option}" to "{payload[option]}" for job "{jobname}", chat_id={chat_id}'
    )
    await replies.text(update, replies.attribute_change_success_message)


# state 2
async def handle_edit_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    jobname, attr = context.user_data["jobname"], context.user_data["attribute"]
    chat_id = update.message.chat.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if attr == attr_cron:
        crontab = update.message.text
        _, payload, err = await prepare_crontab_update(update, crontab, db_service)
        if err is not None:
            await replies.text(
                update,
                replies.invalid_crontab_message,
                reply_markup=replies.force_reply,
            )
            return convo.states.s2
        mongo_key = "crontab"

    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    if attr == attr_content:
        old_content_type = entry.get("content_type", "")
        mongo_key = "content"
        content_type = old_content_type
        if old_content_type == ContentType.POLL.value:
            content_type = ContentType.TEXT.value

        payload = {
            "last_updated_by": update.message.from_user.id,
            "content": update.message.text_html,
            "content_type": content_type,
        }

    if attr == attr_jobname:
        new_jobname = update.message.text.strip()
        if new_jobname != jobname and await dbutils.entry_exists(
            db_service, chat_id, new_jobname
        ):
            await replies.text(
                update,
                replies.invalid_new_jobname_message,
                reply_markup=replies.force_reply,
            )
            return convo.states.s2
        mongo_key = "jobname"
        payload = {
            "last_updated_by": update.message.from_user.id,
            "jobname": new_jobname,
        }

    await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    log.logger.info(
        f'[BOT] User "{payload["last_updated_by"]}" updated option "{mongo_key}" to "{payload[mongo_key]}" for job "{jobname}", chat_id={chat_id}'
    )
    await replies.text(update, replies.attribute_change_success_message)
    return ConversationHandler.END


async def handle_edit_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    poll_json = update.message.poll
    payload = {
        "last_updated_by": update.message.from_user.id,
        "content": jsons.dumps(poll_json),
        "content_type": ContentType.POLL.value,
    }
    await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    option = "content"
    log.logger.info(
        f'[BOT] User "{payload["last_updated_by"]}" updated option "{option}" to "{payload[option]}" for job "{jobname}", chat_id={chat_id}'
    )
    await replies.text(update, replies.attribute_change_success_message)
    return ConversationHandler.END


# state 3
async def handle_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    if entry is None:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    payload = {"last_updated_by": update.message.from_user.id}
    if entry.get("photo_id", "") == "":
        payload["photo_id"] = update.message.photo[-1].file_id
        payload["content_type"] = ContentType.PHOTO.value
    else:  # photo group
        payload["content_type"] = ContentType.MEDIA.value
        payload["photo_group_id"] = "-"
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        payload["photo_id"] = photo_ids
    await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    option = "photo_id"
    log.logger.info(
        f'[BOT] User "{payload["last_updated_by"]}" updated option "{option}" to "{payload[option]}" for job "{jobname}", chat_id={chat_id}'
    )
    await replies.text(update, replies.attribute_change_success_message)
    return ConversationHandler.END


# state 4
async def handle_clear_photos(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    res = update.message.text.lower()

    if res == "no":
        await replies.text(update, replies.convo_ended_message)
        return ConversationHandler.END

    if res == "yes":
        db_service: mongo.MongoService = context.application.bot_data["mongo"]
        entry = await dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
        if entry is None:
            await replies.text(update, replies.error_message)
            return ConversationHandler.END

        if entry.get("photo_id", "") == "":
            await replies.text(update, replies.no_photos_to_delete_error_message)
            return ConversationHandler.END

        payload = {
            "last_updated_by": update.message.from_user.id,
            "content_type": ContentType.TEXT.value,
            "photo_id": "",
            "photo_group_id": "",
        }
        await dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)

        option = "photo_id"
        log.logger.info(
            f'[BOT] User "{payload["last_updated_by"]}" updated option "{option}" to "{payload[option]}" for job "{jobname}", chat_id={chat_id}'
        )
        await replies.text(update, replies.attribute_change_success_message)
        return ConversationHandler.END

    await replies.text(update, replies.error_message)


# helpers
async def prepare_crontab_update(
    update: Update, crontab: str, db_service: mongo.MongoService
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Exception]]:
    try:
        description = get_description(crontab).lower()
    except Exception:  # crontab is not valid
        return None, None, Exception()

    # arrange next run date and time
    chat_entry = await dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    if chat_entry is None:
        return None, None, Exception()

    user_timezone = chat_entry.get("utc_tz")
    user_tz_offset = chat_entry.get("tz_offset")
    try:
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, user_timezone, user_tz_offset
        )
    except Exception:
        return None, None, Exception()

    # update db entry
    payload = {
        "crontab": crontab,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "last_updated_by": update.message.from_user.id,
    }
    return description, payload, None
