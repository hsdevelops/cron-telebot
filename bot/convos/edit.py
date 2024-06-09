from telegram import Update
from telegram.ext import ConversationHandler
from telegram.ext._contexttypes import ContextTypes
from bot.actions import actions
from bot.replies import replies
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from common import log, utils
import jsons
from typing import Optional

state0, state1, state2, state3, state4 = range(5)

attr_cron = "crontab"
attr_content = "text content"
attr_add_photo = "add photo"
attr_del_photo = "remove all photos"
attr_del_prev = "toggle delete previous"
attr_pause_job = "pause/resume job"

attrs = [
    attr_cron,
    attr_content,
    attr_add_photo,
    attr_del_photo,
    attr_del_prev,
    attr_pause_job,
]

# state 0


async def choose_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db_service = mongo.MongoService(update)
    jobname = str(update.message.text)

    if not dbutils.entry_exists(db_service, update.message.chat.id, jobname):
        await replies.send_error_message(update)
        return state0

    context.user_data["jobname"] = jobname
    await replies.send_choose_attribute_message(update)
    return state1


# state 1
async def choose_attribute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    attr = str(update.message.text)
    context.user_data["attribute"] = attr

    if attr not in attrs:
        await replies.send_error_message(update)
        return state1

    if attr == attr_del_prev:
        await toggle_delete_previous(update, context)
        return ConversationHandler.END

    if attr == attr_del_photo:
        await replies.send_reset_photos_confirmation_message(update)
        return state4

    if attr == attr_pause_job:
        await toggle_pause_job(update, context)
        return ConversationHandler.END

    await replies.send_prompt_new_value_message(update)

    if attr == attr_add_photo:
        return state3

    return state2


async def toggle_delete_previous(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    db_service = mongo.MongoService(update)
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    new_option_value = "" if entry.get("option_delete_previous", "") != "" else True
    payload = {
        "option_delete_previous": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    log.log_option_updated(payload, "option_delete_previous", jobname, chat_id)
    await replies.send_attribute_change_success_message(update)


async def toggle_pause_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    db_service = mongo.MongoService(update)
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)
    new_option_value = "" if entry.get("paused_ts", "") != "" else utils.now()
    payload = {
        "paused_ts": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    if new_option_value == "":  # calculate next run
        crontab = entry.get("crontab")
        _, crontab_payload, err = await actions.prepare_crontab_update(
            update, crontab, db_service
        )
        if err is not None:
            return await replies.send_attribute_change_error_message(update)
        payload = {
            "nextrun_ts": crontab_payload["nextrun_ts"],
            "user_nextrun_ts": crontab_payload["user_nextrun_ts"],
            **payload,
        }
    dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    log.log_option_updated(payload, "paused_ts", jobname, chat_id)
    await replies.send_attribute_change_success_message(update)


# state 2
async def handle_edit_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    jobname, attr = context.user_data["jobname"], context.user_data["attribute"]
    chat_id = update.message.chat.id
    db_service = mongo.MongoService(update)

    if attr == attr_cron:
        crontab = update.message.text
        _, payload, err = await actions.prepare_crontab_update(
            update, crontab, db_service
        )
        if err is not None:
            return state2
        mongo_key = "crontab"

    entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)

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

    dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)
    log.log_option_updated(payload, mongo_key, jobname, chat_id)
    await replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


async def handle_edit_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service = mongo.MongoService(update)
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)

    poll_json = update.message.poll
    payload = {
        "last_updated_by": update.message.from_user.id,
        "content": jsons.dumps(poll_json),
        "content_type": ContentType.POLL.value,
    }
    dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)

    log.log_option_updated(payload, "content", jobname, chat_id)
    await replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


# state 3
async def handle_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service = mongo.MongoService(update)
    entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)

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
    dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)

    log.log_option_updated(payload, "photo_id", jobname, chat_id)
    await replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


# state 4
async def handle_clear_photos(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    res = await update.message.text.lower()

    if res == "no":
        return end_convo(update, context)

    if res == "yes":
        db_service = mongo.MongoService(update)
        entry = dbutils.find_entry_by_jobname(db_service, chat_id, jobname)

        if entry.get("photo_id", "") == "":
            await replies.send_no_photos_to_delete_error_message(update)
            return ConversationHandler.END

        payload = {
            "last_updated_by": update.message.from_user.id,
            "content_type": ContentType.TEXT.value,
            "photo_id": "",
            "photo_group_id": "",
        }
        dbutils.update_entry_by_jobid(db_service, entry["_id"], payload)

        log.log_option_updated(payload, "photo_id", jobname, chat_id)
        await replies.send_attribute_change_success_message(update)
        return ConversationHandler.END

    await replies.send_error_message(update)


async def end_convo(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await replies.send_convo_ended_message(update)
    return ConversationHandler.END
