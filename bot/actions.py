import re
import jsons
from bot import replies
from config import TZ_OFFSET
from common import log, utils
from database.db import Database
from cron_descriptor import get_description
from datetime import datetime, timezone, timedelta


def show_job_details(update, context):
    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    entry = db_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry is None:
        replies.send_error_message(update)

    replies.send_job_details(update, entry)


def add_new_job(update, context):
    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    # person limit
    if db_service.exceed_user_limit(update.message.from_user.id):
        return replies.send_exceed_limit_error_message(update)

    # check name does not already exist
    if db_service.check_exists(update.message.chat.id, update.message.text):
        return replies.send_invalid_new_job_message(update)

    # add job to db
    db_service.add_new_entry(
        update.message.chat.id, update.message.text, update.message.from_user.id
    )
    replies.send_request_text_message(update)
    log.log_new_job_added(update)


def add_timezone(update):
    # check validity
    tz_values = re.match(
        "^(([+-])(2[0-3]|[01][0-9]):([0-5][0-9]))$", update.message.text
    )
    if not tz_values:
        return replies.send_error_message(update)

    match_groups = tz_values.groups()
    utc_tz = str(match_groups[0])
    sign = match_groups[1]
    hour = int(match_groups[2])
    mins = int(match_groups[3])

    tz_offset = float("%s%.2f" % (sign, hour + mins / 60))

    if tz_offset < -12 or tz_offset > 14:
        return replies.send_error_message(update)

    db_service = Database(update).service
    db_service.add_chat_data(
        chat_id=update.message.chat.id,
        chat_title=update.message.chat.title,
        chat_type=update.message.chat.type,
        tz_offset=tz_offset,
        utc_tz=utc_tz,
        created_by=update.message.from_user.id,
        telegram_ts=update.message.date,
    )
    replies.send_help_message(update)


def add_message(update, context, photo=False, poll=False):
    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    entry = db_service.retrieve_latest_entry(update.message.chat.id)
    if entry is None:
        return replies.send_simple_prompt_message(update)

    fields_to_update = {
        "last_updated_by": update.message.from_user.id,
    }

    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)
    same_photo_group = len(photo_group_id) > 0 and photo_group_id == str(
        utils.get_value(entry, "photo_group_id")
    )

    if same_photo_group:  # group of photos
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(utils.get_value(entry, "photo_id"), photo_id)
        fields_to_update["photo_id"] = photo_ids
        fields_to_update["content_type"] = "photo_group"
    elif utils.get_value(entry, "content") != "":  # field must not be filled already
        return replies.send_prompt_new_job_message(update)
    elif poll:
        fields_to_update["content_type"] = "poll"
        poll_json = update.message.poll
        fields_to_update["content"] = jsons.dumps(poll_json)
    elif photo and photo_group_id != "":  # first photo of media group
        fields_to_update["photo_id"] = update.message.photo[-1].file_id
        fields_to_update["photo_group_id"] = photo_group_id
        fields_to_update["content"] = (
            "" if update.message.caption is None else update.message.caption
        )
        fields_to_update["content_type"] = "photo_group"
    elif photo:  # single photo
        fields_to_update["photo_id"] = update.message.photo[-1].file_id
        fields_to_update["photo_group_id"] = photo_group_id
        fields_to_update["content"] = (
            "" if update.message.caption is None else update.message.caption_html
        )
        fields_to_update["content_type"] = "single_photo"
    else:  # only text
        fields_to_update["content"] = update.message.text_html
        fields_to_update["content_type"] = "text"

    updated_entry = utils.edit_entry_multiple_fields(
        entry,
        fields_to_update,
    )

    db_service.update_entry(updated_entry)
    log.log_new_content_added(updated_entry)

    # reply
    if not same_photo_group:
        replies.send_request_crontab_message(update)


def add_crontab(update, context):

    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_invalid_crontab_message(update)

    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    entry = db_service.retrieve_latest_entry(update.message.chat.id)

    if entry is None:
        return replies.send_simple_prompt_message(update)

    if len(utils.get_value(entry, "crontab")) > 0:  # field must be empty
        return replies.send_prompt_new_job_message(update)

    # arrange next run date and time
    crontab = update.message.text
    user_tz_offset = db_service.retrieve_tz(update.message.chat.id)
    user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)

    # update sheets entry
    updated_entry = utils.edit_entry_multiple_fields(
        entry,
        {
            "crontab": update.message.text,
            "nextrun_ts": db_nextrun_ts,
            "user_nextrun_ts": user_nextrun_ts,
            "last_updated_by": update.message.from_user.id,
        },
    )
    db_service.update_entry(updated_entry)
    log.log_crontab_updated(updated_entry)

    # reply
    replies.send_confirm_message(update, entry, description)


def remove_job(update, context):
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))

    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    entry = db_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry is None:
        return replies.send_error_message(update)

    updated_entry = utils.edit_entry_multiple_fields(
        entry,
        {
            "removed_ts": utils.parse_time_millis(now),
            "last_updated_by": update.message.from_user.id,
        },
    )
    db_service.update_entry(updated_entry)

    log.log_job_removed(updated_entry)
    replies.send_delete_success_message(update)


def decrypt_cron(update):
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_checkcron_invalid_message(update)

    replies.send_checkcron_meaning_message(update, description)


def toggle_delete_previous(update, context):
    db_service = Database(update).service
    if not check_rights(update, context, db_service):
        return

    entry = db_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry is None:
        return replies.send_error_message(update)

    # update sheets entry
    new_option_value = (
        "" if utils.get_value(entry, "option_delete_previous") != "" else True
    )
    updated_entry = utils.edit_entry_multiple_fields(
        entry,
        {
            "option_delete_previous": new_option_value,
            "last_updated_by": update.message.from_user.id,
        },
    )
    db_service.update_entry(updated_entry)
    log.log_option_updated(updated_entry, "option_delete_previous")

    replies.send_advanced_option_success_message(
        update, "deleteprevious", new_option_value
    )


def add_new_channel_job(update, poll=False):
    # channel jobs can only be set up from private chats
    if update.message.chat.type != "private":
        return

    forwarded_chat_info = update.message.forward_from_chat

    # job creation by forwarded messages only for channels
    if forwarded_chat_info.type != "channel":
        return replies.send_channels_only_error_message(
            update, forwarded_chat_info.type
        )

    db_service = Database(update).service
    # timezone must be defined in order to create new job
    tz_offset = db_service.retrieve_tz(update.message.chat.id)
    if tz_offset is None:
        return replies.send_start_message(update)

    # add chat to db
    chat_exists = db_service.check_chat_exists(forwarded_chat_info.id)
    if not chat_exists:
        db_service.add_chat_data(
            chat_id=forwarded_chat_info.id,
            chat_title=forwarded_chat_info.title,
            chat_type=forwarded_chat_info.type,
            tz_offset=tz_offset,
            utc_tz="",
            created_by=update.message.from_user.id,
            telegram_ts=update.message.date,
        )

    # add job to db
    entry = db_service.retrieve_latest_entry(update.message.chat.id)
    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)

    if (
        entry is not None
        and len(photo_group_id) > 0
        and photo_group_id == str(utils.get_value(entry, "photo_group_id"))
    ):  # same photo group
        fields_to_update = {
            "last_updated_by": update.message.from_user.id,
            "photo_id": "{};{}".format(
                utils.get_value(entry, "photo_id"), update.message.photo[-1].file_id
            ),
        }
        updated_entry = utils.edit_entry_multiple_fields(
            entry,
            fields_to_update,
        )
        return db_service.update_entry(updated_entry)

    # new job to be created, assert job limit
    if db_service.exceed_user_limit(update.message.from_user.id):
        return replies.send_exceed_limit_error_message(update)

    # add new job
    content = update.message.caption
    content_type = "single_photo"
    if content is None:
        content = update.message.text_html
        content_type = "text"
    elif photo_group_id == "":
        content = update.message.caption_html
        content_type = "photo_group"

    if poll:
        content_type = "poll"
        poll_json = update.message.poll
        content = jsons.dumps(poll_json)

    photo_id = "" if len(update.message.photo) < 1 else update.message.photo[-1].file_id

    # populate jobname for channels
    number = 1
    jobname = "%s (%d)" % (forwarded_chat_info.title[:6], number)
    while db_service.check_exists(update.message.chat.id, jobname):
        number = number + 1
        jobname = "%s (%d)" % (forwarded_chat_info.title[:6], number)

    db_service.add_new_entry(
        chat_id=update.message.chat.id,
        channel_id=forwarded_chat_info.id,
        jobname=jobname,
        user_id=update.message.from_user.id,
        crontab="",
        content=content,
        content_type=content_type,
        photo_id=photo_id,
        photo_group_id=photo_group_id,
    )

    log.log_new_channel_job_added(update)
    replies.send_request_crontab_message(update)


def restrict_to_admins(update, db_service):

    db_service = Database(update).service

    entry = db_service.get_chat_entry(update.message.chat.id)
    if entry is None:
        return

    current_restriction = utils.get_value(entry, "restriction")

    if current_restriction == "administrator":
        entry = utils.edit_entry_single_field(entry, "restriction", "")
        db_service.update_chat_entry(entry)
        return replies.send_restrict_success_message(update, "everyone")

    if current_restriction == "creator":
        return replies.send_wrong_restrction_message(update, "the current bot user")

    entry = utils.edit_entry_single_field(entry, "restriction", "administrator")
    db_service.update_chat_entry(entry)

    return replies.send_restrict_success_message(update, "only group admins")


def restrict_to_user(update, db_service):
    # user running this command must be creator

    entry = db_service.get_chat_entry(update.message.chat.id)
    if entry is None:
        return

    user_id = update.message.from_user.id
    if str(user_id) != str(utils.get_value(entry, "created_by")):
        return replies.send_user_unauthorized_error_message(
            update, "the current bot user"
        )

    current_restriction = utils.get_value(entry, "restriction")
    if current_restriction == "administrator":
        return replies.send_wrong_restrction_message(update, "group admins")

    if current_restriction == "creator":
        entry = utils.edit_entry_single_field(entry, "restriction", "")
        db_service.update_chat_entry(entry)
        return replies.send_restrict_success_message(update, "everyone")

    entry = utils.edit_entry_single_field(entry, "restriction", "creator")
    db_service.update_chat_entry(entry)

    return replies.send_restrict_success_message(update, "only you")


# def need to check if chat has this shit set else don't allow walao
def check_rights(update, context, db_service, must_be_admin=False):
    user_id = update.message.from_user.id
    group_id = update.message.chat.id

    entry = db_service.get_chat_entry(group_id)
    if entry is None:
        return

    current_restriction = utils.get_value(entry, "restriction")

    if current_restriction == "creator" and str(user_id) != str(
        utils.get_value(entry, "created_by")
    ):
        return replies.send_user_unauthorized_error_message(
            update, "the current bot user"
        )

    is_admin = context.bot.get_chat_member(group_id, user_id).status in [
        "administrator",
        "creator",
    ]
    if (
        must_be_admin
        and not is_admin
        or current_restriction == "administrator"
        and not is_admin
    ):
        return replies.send_user_unauthorized_error_message(update, "group admins")

    return True
