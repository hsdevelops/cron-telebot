from telegram.ext import ConversationHandler
from bot.actions import actions
from bot.replies import replies
from database import mongo
from common import log, utils
import jsons

state0, state1, state2, state3, state4 = range(5)

attr_cron = "crontab"
attr_content = "text content"
attr_add_photo = "add photo"
attr_del_photo = "remove all photos"
attr_del_prev = "toggle delete previous"
attr_pause_job = "pause/resume job"

attr_set = set(
    [
        attr_cron,
        attr_content,
        attr_add_photo,
        attr_del_photo,
        attr_del_prev,
        attr_pause_job,
    ]
)

# state 0
def choose_job(update, context):
    db_service = mongo.MongoService(update)
    jobname = str(update.message.text)

    if update.message.from_user.id != context.user_data["user_id"]:
        replies.send_convo_unauthorized_message(update)
        return state0

    if not db_service.check_exists(update.message.chat.id, jobname):
        replies.send_error_message(update)
        return state0

    context.user_data["jobname"] = jobname
    replies.send_choose_attribute_message(update)
    return state1


# state 1
def choose_attribute(update, context):
    attr = str(update.message.text)
    context.user_data["attribute"] = attr

    if update.message.from_user.id != context.user_data["user_id"]:
        replies.send_convo_unauthorized_message(update)
        return state1

    if attr not in attr_set:
        replies.send_error_message(update)
        return state1

    if attr == attr_del_prev:
        toggle_delete_previous(update, context)
        return ConversationHandler.END

    if attr == attr_del_photo:
        replies.send_reset_photos_confirmation_message(update)
        return state4

    if attr == attr_pause_job:
        toggle_pause_job(update, context)
        return ConversationHandler.END

    replies.send_prompt_new_value_message(update)

    if attr == attr_add_photo:
        return state3

    return state2


def toggle_delete_previous(update, context):
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    db_service = mongo.MongoService(update)
    entry = db_service.get_one_entry(chat_id, jobname)
    new_option_value = "" if entry.get("option_delete_previous", "") != "" else True
    fields_to_update = {
        "option_delete_previous": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    db_service.update_entry({"_id": entry["_id"]}, fields_to_update)
    log.log_option_updated(fields_to_update, "option_delete_previous", jobname, chat_id)
    replies.send_attribute_change_success_message(update)


def toggle_pause_job(update, context):
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    db_service = mongo.MongoService(update)
    entry = db_service.get_one_entry(chat_id, jobname)
    new_option_value = "" if entry.get("paused_ts", "") != "" else utils.now()
    fields_to_update = {
        "paused_ts": new_option_value,
        "last_updated_by": update.message.from_user.id,
    }
    if new_option_value == "":  # calculate next run
        crontab = entry.get("crontab")
        _, fields, has_err = actions.prepare_crontab_update(update, crontab, db_service)
        if has_err:
            return replies.send_attribute_change_error_message(update)
        fields_to_update = {
            "nextrun_ts": fields["nextrun_ts"],
            "user_nextrun_ts": fields["user_nextrun_ts"],
            **fields_to_update,
        }
    db_service.update_entry({"_id": entry["_id"]}, fields_to_update)
    log.log_option_updated(fields_to_update, "paused_ts", jobname, chat_id)
    replies.send_attribute_change_success_message(update)


# state 2
def handle_edit_content(update, context):
    if update.message.from_user.id != context.user_data["user_id"]:
        replies.send_convo_unauthorized_message(update)
        return state2

    jobname, attr = context.user_data["jobname"], context.user_data["attribute"]
    chat_id = update.message.chat.id
    db_service = mongo.MongoService(update)

    if attr == attr_cron:
        crontab = update.message.text
        _, fields, has_err = actions.prepare_crontab_update(update, crontab, db_service)
        if has_err:
            return state2
        mongo_key = "crontab"

    entry = db_service.get_one_entry(chat_id, jobname)

    if attr == attr_content:
        old_content_type = entry.get("content_type", "")
        mongo_key = "content"
        fields = {
            "last_updated_by": update.message.from_user.id,
            "content": update.message.text_html,
            "content_type": "text" if old_content_type == "poll" else old_content_type,
        }

    db_service.update_entry({"_id": entry["_id"]}, fields)
    log.log_option_updated(fields, mongo_key, jobname, chat_id)
    replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


def handle_edit_poll(update, context):
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service = mongo.MongoService(update)
    entry = db_service.get_one_entry(chat_id, jobname)

    poll_json = update.message.poll
    fields_to_update = {
        "last_updated_by": update.message.from_user.id,
        "content": jsons.dumps(poll_json),
        "content_type": "poll",
    }
    db_service.update_entry({"_id": entry["_id"]}, fields_to_update)

    log.log_option_updated(fields_to_update, "content", jobname, chat_id)
    replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


# state 3
def handle_add_photo(update, context):
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id

    db_service = mongo.MongoService(update)
    entry = db_service.get_one_entry(chat_id, jobname)

    fields_to_update = {"last_updated_by": update.message.from_user.id}
    if entry.get("photo_id", "") == "":
        fields_to_update["photo_id"] = update.message.photo[-1].file_id
        fields_to_update["content_type"] = "single_photo"
    else:  # photo group
        fields_to_update["content_type"] = "photo_group"
        fields_to_update["photo_group_id"] = "-"
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        fields_to_update["photo_id"] = photo_ids
    db_service.update_entry({"_id": entry["_id"]}, fields_to_update)

    log.log_option_updated(fields_to_update, "photo_id", jobname, chat_id)
    replies.send_attribute_change_success_message(update)
    return ConversationHandler.END


# state 4
def handle_clear_photos(update, context):
    jobname, chat_id = context.user_data["jobname"], update.message.chat.id
    res = update.message.text.lower()

    if res == "no":
        replies.send_convo_ended_message(update)
        return ConversationHandler.END

    if res == "yes":
        db_service = mongo.MongoService(update)
        entry = db_service.get_one_entry(chat_id, jobname)

        if entry.get("photo_id", "") == "":
            replies.send_no_photos_to_delete_error_message(update)
            return ConversationHandler.END

        fields_to_update = {
            "last_updated_by": update.message.from_user.id,
            "content_type": "text",
            "photo_id": "",
            "photo_group_id": "",
        }
        db_service.update_entry({"_id": entry["_id"]}, fields_to_update)

        log.log_option_updated(fields_to_update, "photo_id", jobname, chat_id)
        replies.send_attribute_change_success_message(update)
        return ConversationHandler.END

    replies.send_error_message(update)
