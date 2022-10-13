from common.utils import calc_next_run, get_value, parse_time_millis
from common import log, sheets

import re
from config import TZ_OFFSET
from cron_descriptor import get_description
from datetime import datetime, timezone, timedelta

from bot import replies


def show_job_details(update):
    sheets_service = sheets.SheetsService(update)

    entry_df = sheets_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry_df is None:
        replies.send_error_message(update)

    replies.send_job_details(update, entry_df)


def add_new_job(update):
    sheets_service = sheets.SheetsService(update)

    # timezone must be defined in order to create new job
    if sheets_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    # person limit
    if sheets_service.exceed_user_limit(update.message.from_user.id):
        return replies.send_exceed_limit_error_message(update)

    # check name does not already exist
    if sheets_service.check_exists(update.message.chat.id, update.message.text):
        return replies.send_invalid_new_job_message(update)

    # add job to db
    sheets_service.add_new_entry(
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
    utc_tz = "'%s" % match_groups[0]
    sign = match_groups[1]
    hour = int(match_groups[2])
    mins = int(match_groups[3])

    tz_offset = float("%s%.2f" % (sign, hour + mins / 60))

    if tz_offset < -12 or tz_offset > 14:
        return replies.send_error_message(update)

    sheets_service = sheets.SheetsService(update)
    sheets_service.add_chat_data(
        chat_id=update.message.chat.id,
        chat_title=update.message.chat.title,
        chat_type=update.message.chat.type,
        tz_offset=tz_offset,
        utc_tz=utc_tz,
        created_by=update.message.from_user.id,
        telegram_ts=update.message.date,
    )
    replies.send_help_message(update)


def add_message(update, photo=False):
    sheets_service = sheets.SheetsService(update)
    entry_df = sheets_service.retrieve_latest_entry(update.message.chat.id)

    if entry_df is None:
        return replies.send_simple_prompt_message(update)

    fields_to_update = {
        "last_updated_by": str(update.message.from_user.id),
    }

    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)
    same_photo_group = len(photo_group_id) > 0 and photo_group_id == str(
        get_value(entry_df, "photo_group_id")
    )

    if same_photo_group:  # group of photos
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(get_value(entry_df, "photo_id"), photo_id)
        fields_to_update["photo_id"] = photo_ids
    elif get_value(entry_df, "content") != "":  # field must not be filled already
        return replies.send_prompt_new_job_message(update)
    elif photo and photo_group_id != "":  # first photo of media group
        fields_to_update["photo_id"] = update.message.photo[-1].file_id
        fields_to_update["photo_group_id"] = photo_group_id
        fields_to_update["content"] = (
            "" if update.message.caption is None else update.message.caption
        )
    elif photo:  # single photo
        fields_to_update["photo_id"] = update.message.photo[-1].file_id
        fields_to_update["photo_group_id"] = photo_group_id
        fields_to_update["content"] = (
            "" if update.message.caption is None else update.message.caption_html
        )
    else:  # only text
        fields_to_update["content"] = update.message.text_html

    updated_entry_df = sheets.edit_entry_multiple_fields(
        entry_df,
        fields_to_update,
    )
    sheets_service.update_entry(updated_entry_df)
    log.log_new_content_added(updated_entry_df)

    # reply
    if not same_photo_group:
        replies.send_request_crontab_message(update)


def add_crontab(update):
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_invalid_crontab_message(update)

    sheets_service = sheets.SheetsService(update)
    entry_df = sheets_service.retrieve_latest_entry(update.message.chat.id)

    if entry_df is None:
        return replies.send_simple_prompt_message(update)

    if len(get_value(entry_df, "crontab")) > 0:  # field must be empty
        return replies.send_prompt_new_job_message(update)

    # arrange next run date and time
    crontab = update.message.text
    user_tz_offset = sheets_service.retrieve_tz(update.message.chat.id)
    user_nextrun_ts, db_nextrun_ts = calc_next_run(crontab, user_tz_offset)

    # update sheets entry
    updated_entry_df = sheets.edit_entry_multiple_fields(
        entry_df,
        {
            "crontab": update.message.text,
            "nextrun_ts": db_nextrun_ts,
            "user_nextrun_ts": user_nextrun_ts,
            "last_updated_by": str(update.message.from_user.id),
        },
    )
    sheets_service.update_entry(updated_entry_df)
    log.log_crontab_updated(updated_entry_df)

    # reply
    replies.send_confirm_message(update, entry_df, description)


def remove_job(update):
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))

    sheets_service = sheets.SheetsService(update)
    entry_df = sheets_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry_df is None:
        return replies.send_error_message(update)

    updated_entry_df = sheets.edit_entry_multiple_fields(
        entry_df,
        {
            "removed_ts": parse_time_millis(now),
            "last_updated_by": str(update.message.from_user.id),
        },
    )
    sheets_service.update_entry(updated_entry_df)

    log.log_job_removed(updated_entry_df)
    replies.send_delete_success_message(update)


def decrypt_cron(update):
    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        return replies.send_checkcron_invalid_message(update)

    replies.send_checkcron_meaning_message(update, description)


def toggle_delete_previous(update):
    sheets_service = sheets.SheetsService(update)
    entry_df = sheets_service.retrieve_specific_entry(
        update.message.chat.id, update.message.text
    )

    if entry_df is None:
        return replies.send_error_message(update)

    # update sheets entry
    new_option_value = (
        "" if get_value(entry_df, "option_delete_previous") != "" else True
    )
    updated_entry_df = sheets.edit_entry_multiple_fields(
        entry_df,
        {
            "option_delete_previous": new_option_value,
            "last_updated_by": str(update.message.from_user.id),
        },
    )
    sheets_service.update_entry(updated_entry_df)
    log.log_option_updated(updated_entry_df, "option_delete_previous")

    replies.send_advanced_option_success_message(
        update, "deleteprevious", new_option_value
    )


def add_new_channel_job(update):
    forwarded_chat_info = update.message.forward_from_chat

    # job creation by forwarded messages only for channels
    if forwarded_chat_info.type != "channel":
        return replies.send_channels_only_error_message(
            update, forwarded_chat_info.type
        )

    sheets_service = sheets.SheetsService(update)
    # timezone must be defined in order to create new job
    tz_offset = sheets_service.retrieve_tz(update.message.chat.id)
    if tz_offset is None:
        return replies.send_start_message(update)

    # add chat to db
    chat_exists = sheets_service.check_chat_exists(forwarded_chat_info.id)
    if not chat_exists:
        sheets_service.add_chat_data(
            chat_id=forwarded_chat_info.id,
            chat_title=forwarded_chat_info.title,
            chat_type=forwarded_chat_info.type,
            tz_offset=tz_offset,
            utc_tz="",
            created_by=update.message.from_user.id,
            telegram_ts=update.message.date,
        )

    # add job to db
    entry_df = sheets_service.retrieve_latest_entry(update.message.chat.id)
    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)

    if (
        entry_df is not None
        and len(photo_group_id) > 0
        and photo_group_id == str(get_value(entry_df, "photo_group_id"))
    ):  # same photo group
        fields_to_update = {
            "last_updated_by": str(update.message.from_user.id),
            "photo_id": "{};{}".format(
                get_value(entry_df, "photo_id"), update.message.photo[-1].file_id
            ),
        }
        updated_entry_df = sheets.edit_entry_multiple_fields(
            entry_df,
            fields_to_update,
        )
        return sheets_service.update_entry(updated_entry_df)

    # person limit
    if sheets_service.exceed_user_limit(update.message.from_user.id):
        return replies.send_exceed_limit_error_message(update)

    content = update.message.caption
    if content is None:
        content = update.message.text_html
    elif photo_group_id == "":
        content = update.message.caption_html

    if (
        entry_df is None
        or get_value(entry_df, "jobname") != ""
        or get_value(entry_df, "content") != ""
    ):  # single/first photo or text
        photo_id = (
            "" if len(update.message.photo) < 1 else update.message.photo[-1].file_id
        )

        # populate jobname for channels
        number = 1
        jobname = "%s (%d)" % (forwarded_chat_info.title[:6], number)
        while sheets_service.check_exists(update.message.chat.id, jobname):
            number = number + 1
            jobname = "%s (%d)" % (forwarded_chat_info.title[:6], number)

        sheets_service.add_new_entry(
            chat_id=update.message.chat.id,
            channel_id=forwarded_chat_info.id,
            jobname=jobname,
            userid=update.message.from_user.id,
            crontab="",
            content=content,
            photo_id=photo_id,
            photo_group_id=photo_group_id,
        )

        log.log_new_channel_job_added(update)
        replies.send_request_crontab_message(update)
