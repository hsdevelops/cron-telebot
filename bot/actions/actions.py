import jsons
from bot.replies import replies
from common import log, utils
from database import mongo
from cron_descriptor import get_description
from bot.actions.permissions import check_rights
from bot.actions.readonly import *
from bot.actions.removals import *


def add_new_job(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    # person limit
    job_count, user_limit = db_service.get_user_limit(update.message.from_user.id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    # check name does not already exist
    if db_service.check_exists(update.message.chat.id, update.message.text):
        return replies.send_invalid_new_job_message(update)

    # add job to db
    msg = update.message
    db_service.add_new_entry(msg.chat.id, msg.text, msg.from_user.id)
    replies.send_request_text_message(update)
    log.log_new_job_added(update)


def add_new_channel_job(update, poll=False):
    chat_id = update.message.chat.id
    # channel jobs can only be set up from private chats
    if update.message.chat.type != "private":
        return

    forwarded_chat_info = update.message.forward_from_chat

    # job creation by forwarded messages only for channels
    if forwarded_chat_info.type != "channel":
        replies.send_channels_only_error_message(update, forwarded_chat_info.type)
        return

    db_service = mongo.MongoService(update)
    # timezone must be defined in order to create new job
    tz_offset = db_service.retrieve_tz(chat_id)
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
    entry = db_service.retrieve_latest_entry(chat_id)
    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)

    if (
        entry is not None
        and len(photo_group_id) > 0
        and photo_group_id == str(entry.get("photo_group_id", ""))
    ):  # same photo group
        photo_id = update.message.photo[-1].file_id
        fields_to_update = {
            "last_updated_by": update.message.from_user.id,
            "photo_id": "{};{}".format(entry.get("photo_id", ""), photo_id),
        }
        return db_service.update_entry(mongo.entry_filter(entry), fields_to_update)

    # new job to be created, assert job limit
    job_count, user_limit = db_service.get_user_limit(update.message.from_user.id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    # add new job
    content = update.message.caption
    content_type = "photo_group"
    if len(update.message.photo) < 1:
        content = update.message.text_html
        content_type = "text"
    elif photo_group_id == "":
        content = update.message.caption_html
        content_type = "single_photo"
    content = "" if content is None else content

    if poll:
        content_type = "poll"
        poll_json = update.message.poll
        content = jsons.dumps(poll_json)

    photo_id = "" if len(update.message.photo) < 1 else update.message.photo[-1].file_id

    # populate jobname for channels
    jobname = generate_jobname(db_service, forwarded_chat_info.title[:6], chat_id)
    db_service.add_new_entry(
        chat_id=chat_id,
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


def add_new_jobs(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    # timezone must be defined in order to create new job
    chat_id = update.message.chat.id
    if db_service.retrieve_tz(chat_id) is None:
        return replies.send_start_message(update)

    # parse user response
    res = utils.extract_jobs(update.message.text_html)
    new_job_count = len(res)

    # person limit
    current_job_count, user_limit = db_service.get_user_limit(
        update.message.from_user.id
    )
    if current_job_count + new_job_count > user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    successful_creation = []

    user_tz_offset = db_service.retrieve_tz(chat_id)
    for crontab, text_content in res:
        # arrange next run date and time
        try:
            user_nextrun, db_nextrun = utils.calc_next_run(crontab, user_tz_offset)
        except Exception:
            continue

        jobname = generate_jobname(db_service, update.message.chat.type, chat_id)
        db_service.add_new_entry(
            chat_id=chat_id,
            jobname=jobname,
            user_id=update.message.from_user.id,
            crontab=crontab,
            content=text_content,
            content_type="text",
            nextrun_ts=db_nextrun,
            user_nextrun_ts=user_nextrun,
        )

        successful_creation.append(
            "%s: %s %s"
            % (jobname, text_content[:10], "..." if len(text_content) > 9 else "")
        )

    if len(successful_creation) > 0:
        log.log_new_jobs_added(update, " // ".join(successful_creation))
        postfix = "\n".join("• %s" % x for x in successful_creation)
        replies.send_jobs_creation_success_message(update, postfix)
    else:
        replies.send_error_message(update)


def add_timezone(update):
    # check validity
    tz_values = utils.extract_tz_values(update.message.text)
    if not tz_values:
        return replies.send_error_message(update)

    utc_tz, tz_offset = utils.calc_tz(tz_values)
    if tz_offset < -12 or tz_offset > 14:
        return replies.send_error_message(update)

    db_service = mongo.MongoService(update)

    chat_exists = db_service.check_chat_exists(update.message.chat.id)
    if not chat_exists:
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
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    chat_id = update.message.chat.id
    entry = db_service.retrieve_latest_entry(chat_id)
    if entry is None:
        return replies.send_simple_prompt_message(update)

    last_updated_by = update.message.from_user.id
    fields_to_update = {"last_updated_by": update.message.from_user.id}

    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)
    same_photo_group = len(photo_group_id) > 0 and photo_group_id == str(
        entry.get("photo_group_id", "")
    )

    if same_photo_group:  # group of photos
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        fields_to_update["photo_id"] = photo_ids
        fields_to_update["content_type"] = "photo_group"
    elif entry.get("content", "") != "":  # field must not be filled already
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
        caption = "" if update.message.caption is None else update.message.caption_html
        fields_to_update["content"] = caption
        fields_to_update["content_type"] = "single_photo"
    else:  # only text
        fields_to_update["content"] = update.message.text_html
        fields_to_update["content_type"] = "text"

    db_service.update_entry(mongo.entry_filter(entry), fields_to_update)
    log.log_new_content_added(last_updated_by, entry.get("jobname"), chat_id)

    # reply
    if not same_photo_group:
        replies.send_request_crontab_message(update)


def prepare_crontab_update(update, crontab, db_service):
    try:
        description = get_description(crontab).lower()
    except Exception:  # crontab is not valid
        replies.send_invalid_crontab_message(update)
        return None, None, True

    # arrange next run date and time
    user_tz_offset = db_service.retrieve_tz(update.message.chat.id)
    try:
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)
    except Exception:
        replies.send_invalid_crontab_message(update)
        return None, None, True

    # update db entry
    fields = {
        "crontab": crontab,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "last_updated_by": update.message.from_user.id,
    }

    return description, fields, False


def update_crontab(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return
    entry = db_service.retrieve_latest_entry(update.message.chat.id)
    if entry is None:
        return replies.send_simple_prompt_message(update)
    if entry.get("crontab", "") != "":  # field must be empty
        return replies.send_prompt_new_job_message(update)

    crontab = update.message.text
    description, fields, has_err = prepare_crontab_update(update, crontab, db_service)
    if has_err:
        return

    jobname, chat_id = entry.get("jobname"), entry.get("chat_id")
    db_service.update_entry(mongo.entry_filter(entry), fields)
    log.log_crontab_updated(update.message.from_user.id, jobname, chat_id)
    replies.send_confirm_message(update, entry, description)


def update_timezone(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    # check validity
    tz_values = utils.extract_tz_values(update.message.text)
    if not tz_values:
        return replies.send_error_message(update)

    utc_tz, tz_offset = utils.calc_tz(tz_values)
    if tz_offset < -12 or tz_offset > 14:
        return replies.send_error_message(update)

    # retrieve current chat data
    chat_id = update.message.chat.id
    chat_entry = db_service.get_chat_entry(chat_id)
    if tz_offset == chat_entry.get("tz_offset", ""):
        return replies.send_timezone_nochange_error_message(update)

    # update chat entry
    fields = {"tz_offset": tz_offset, "utc_tz": utc_tz}
    db_service.update_chat_entry(chat_id, fields, "utc_tz")

    if chat_entry.get("chat_type", "") == "private":
        user_id = update.message.from_user.id
        db_service.update_chats_tz_by_type(user_id, tz_offset, utc_tz, "channel")

    # update job entries
    job_entries = db_service.get_entries_by_chatid(update.message.chat.id)
    for job_entry in job_entries:
        if job_entry("nextrun_ts", "") == "":
            continue
        crontab = job_entry.get("crontab", "")
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, tz_offset)
        fields = {"nextrun_ts": db_nextrun_ts, "user_nextrun_ts": user_nextrun_ts}
        db_service.update_entry(mongo.entry_filter(job_entry), fields)

    replies.send_timezone_change_success_message(update, utc_tz)


def generate_jobname(db_service, job_prefix, chat_id):
    number = 1
    jobname = "%s (%d)" % (job_prefix, number)
    while db_service.check_exists(chat_id, jobname):
        number = number + 1
        jobname = "%s (%d)" % (job_prefix, number)
    return jobname
