import jsons
from bot.replies import replies
from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from cron_descriptor import get_description
from teleapi import endpoints as teleapi
from bot.actions.permissions import *
from bot.actions.readonly import *
from bot.actions.removals import *


def add_new_job(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    # timezone must be defined in order to create new job
    chat_entry = dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    if chat_entry is None:
        return replies.send_start_message(update)

    # person limit
    user_id = update.message.from_user.id
    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    # check name does not already exist
    chat_id = update.message.chat.id
    if dbutils.entry_exists(db_service, chat_id, update.message.text):
        return replies.send_invalid_new_job_message(update)

    # add job to db
    msg = update.message
    dbutils.add_new_entry(
        db_service,
        chat_id=msg.chat.id,
        jobname=msg.text,
        user_id=msg.from_user.id,
        user_bot_token=chat_entry.get("user_bot_token"),
    )
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
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if chat_entry is None:
        return replies.send_start_message(update)

    # add chat to db
    chat_exists = dbutils.chat_exists(db_service, forwarded_chat_info.id)
    user_id = update.message.from_user.id
    if not chat_exists:
        dbutils.add_chat_data(
            db_service,
            chat_id=forwarded_chat_info.id,
            chat_title=forwarded_chat_info.title,
            chat_type=forwarded_chat_info.type,
            tz_offset=chat_entry.get("tz_offset"),
            utc_tz="",
            created_by=user_id,
            telegram_ts=update.message.date,
        )

    # add job to db
    entry = dbutils.find_latest_entry(db_service, chat_id)
    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)

    if (
        entry is not None
        and len(photo_group_id) > 0
        and photo_group_id == str(entry.get("photo_group_id", ""))
    ):  # same photo group
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        payload = {"last_updated_by": user_id, "photo_id": photo_ids}
        return dbutils.update_entry_by_jobname(db_service, entry, payload)

    # new job to be created, assert job limit
    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    # add new job
    content = update.message.caption
    content_type = ContentType.MEDIA.value
    if len(update.message.photo) < 1:
        content = update.message.text_html
        content_type = ContentType.TEXT.value
    elif photo_group_id == "":
        content = update.message.caption_html
        content_type = ContentType.PHOTO.value
    content = "" if content is None else content

    if poll:
        content_type = ContentType.POLL.value
        poll_json = update.message.poll
        content = jsons.dumps(poll_json)

    photo_id = "" if len(update.message.photo) < 1 else update.message.photo[-1].file_id

    # populate jobname for channels
    jobname = generate_jobname(db_service, forwarded_chat_info.title[:6], chat_id)
    dbutils.add_new_entry(
        db_service,
        chat_id=chat_id,
        channel_id=forwarded_chat_info.id,
        jobname=jobname,
        user_id=update.message.from_user.id,
        crontab="",
        content=content,
        content_type=content_type,
        photo_id=photo_id,
        photo_group_id=photo_group_id,
        user_bot_token=chat_entry.get("user_bot_token"),
    )

    log.log_new_channel_job_added(update)
    replies.send_request_crontab_message(update)


def add_new_jobs(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return

    # timezone must be defined in order to create new job
    chat_id = update.message.chat.id
    if dbutils.find_chat_by_chatid(db_service, chat_id) is None:
        return replies.send_start_message(update)

    # parse user response
    res = utils.extract_jobs(update.message.text_html)
    new_job_count = len(res)

    # person limit
    user_id = update.message.from_user.id
    current_job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if current_job_count + new_job_count > user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    successful_creation = []

    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    user_tz_offset = chat_entry.get("tz_offset")
    for crontab, text_content in res:
        # arrange next run date and time
        try:
            user_nextrun, db_nextrun = utils.calc_next_run(crontab, user_tz_offset)
        except Exception:
            continue

        jobname = generate_jobname(db_service, update.message.chat.type, chat_id)
        dbutils.add_new_entry(
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
        )

        successful_creation.append("%s: (%s) %s" % (jobname, crontab, text_content))

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

    chat_exists = dbutils.chat_exists(db_service, update.message.chat.id)
    if not chat_exists:
        dbutils.add_chat_data(
            db_service,
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
    entry = dbutils.find_latest_entry(db_service, chat_id)
    if entry is None:
        return replies.send_simple_prompt_message(update)

    last_updated_by = update.message.from_user.id
    payload = {"last_updated_by": update.message.from_user.id}

    photo_group_id = update.message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)
    same_photo_group = len(photo_group_id) > 0 and photo_group_id == str(
        entry.get("photo_group_id", "")
    )

    if same_photo_group:  # group of photos
        photo_id = update.message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        payload["photo_id"] = photo_ids
        payload["content_type"] = ContentType.MEDIA.value
    elif entry.get("content", "") != "":  # field must not be filled already
        return replies.send_prompt_new_job_message(update)
    elif poll:
        payload["content_type"] = ContentType.POLL.value
        poll_json = update.message.poll
        payload["content"] = jsons.dumps(poll_json)
    elif photo and photo_group_id != "":  # first photo of media group
        payload["photo_id"] = update.message.photo[-1].file_id
        payload["photo_group_id"] = photo_group_id
        payload["content"] = (
            "" if update.message.caption is None else update.message.caption
        )
        payload["content_type"] = ContentType.MEDIA.value
    elif photo:  # single photo
        payload["photo_id"] = update.message.photo[-1].file_id
        payload["photo_group_id"] = photo_group_id
        caption = "" if update.message.caption is None else update.message.caption_html
        payload["content"] = caption
        payload["content_type"] = ContentType.PHOTO.value
    else:  # only text
        payload["content"] = update.message.text_html
        payload["content_type"] = ContentType.TEXT.value

    dbutils.update_entry_by_jobname(db_service, entry, payload)
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
    chat_entry = dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    user_tz_offset = chat_entry.get("tz_offset")
    try:
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)
    except Exception:
        replies.send_invalid_crontab_message(update)
        return None, None, True

    # update db entry
    payload = {
        "crontab": crontab,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "last_updated_by": update.message.from_user.id,
    }
    return description, payload, False


def update_crontab(update, context):
    db_service = mongo.MongoService(update)
    if not check_rights(update, context, db_service):
        return
    entry = dbutils.find_latest_entry(db_service, update.message.chat.id)
    if entry is None:
        return replies.send_simple_prompt_message(update)
    if entry.get("crontab", "") != "":  # field must be empty
        return replies.send_prompt_new_job_message(update)

    crontab = update.message.text
    description, payload, has_err = prepare_crontab_update(update, crontab, db_service)
    if has_err:
        return

    user_id = update.message.from_user.id
    jobname, chat_id = entry.get("jobname"), entry.get("chat_id")
    dbutils.update_entry_by_jobname(db_service, entry, payload)
    log.log_crontab_updated(user_id, jobname, chat_id)

    # special case — transfer photo ownership to new sender
    is_single_photo = entry["content_type"] == ContentType.PHOTO.value
    bot_token = entry.get("user_bot_token")
    if is_single_photo and bot_token is not None:
        resp, new_photo_id = teleapi.transfer_photo_between_bots(
            db_service, bot_token, None, chat_id, entry
        )
        log.log_photo_transferred(user_id, new_photo_id, chat_id, resp.status_code)

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
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if chat_entry is None:
        return replies.send_start_message(update)

    if tz_offset == chat_entry.get("tz_offset", ""):
        return replies.send_timezone_nochange_error_message(update)

    # update chat entry
    payload = {"tz_offset": tz_offset, "utc_tz": utc_tz}
    dbutils.update_chat_entry(db_service, chat_id, payload, "utc_tz")

    if chat_entry.get("chat_type", "") == "private":
        user_id = update.message.from_user.id
        dbutils.update_chats_tz_by_type(db_service, user_id, tz_offset, "channel")

    # update job entries
    job_entries = dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    for job_entry in job_entries:
        if job_entry.get("nextrun_ts", "") == "":
            continue
        crontab = job_entry.get("crontab", "")
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, tz_offset)
        payload = {"nextrun_ts": db_nextrun_ts, "user_nextrun_ts": user_nextrun_ts}
        dbutils.update_entry_by_jobname(db_service, job_entry, payload)

    replies.send_timezone_change_success_message(update, utc_tz)


def generate_jobname(db_service, job_prefix, chat_id):
    number = 1
    jobname = "%s (%d)" % (job_prefix, number)
    while dbutils.entry_exists(db_service, chat_id, jobname):
        number = number + 1
        jobname = "%s (%d)" % (job_prefix, number)
    return jobname
