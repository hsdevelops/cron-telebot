from bot.replies import replies
from common import log, utils
from common.enums import ContentType
from database import mongo
from database.dbutils import dbutils
from cron_descriptor import get_description
from teleapi import endpoints as teleapi
from telegram import Update
from bot.actions import permissions
from bot.actions.readonly import *
from bot.actions.removals import *
from typing import Dict, Union


async def add_new_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return Exception()

    # timezone must be defined in order to create new job
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    chat_entry = dbutils.find_chat_by_chatid(db_service,        chat_id,)
    if chat_entry is None:
        await replies.send_start_message(update)
        return Exception()

    # person limit
    user_id = utils.get_user_id_from_update(update)
    if user_id is None:
        return

    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        await replies.send_exceed_limit_error_message(update, user_limit)
        return Exception()

    # check name does not already exist
    message_text = utils.get_msg_text_from_update(update)
    if dbutils.entry_exists(db_service, chat_id, message_text):
        await replies.send_invalid_new_job_message(update)
        return Exception()

    # add job to db
    msg = update.message
    if msg is None:
        return

    dbutils.add_new_entry(
        db_service,
        chat_id=chat_id,
        jobname=message_text,
        user_id=user_id,
        user_bot_token=chat_entry.get("user_bot_token"),
        message_thread_id=msg.message_thread_id if msg.is_topic_message else None,
    )
    await replies.send_request_text_message(update)
    log.log_new_job_added(update)


async def add_new_channel_job(update: Update, poll: bool = False):
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    # channel jobs can only be set up from private chats
    message = update.message
    if message is None:
        return
    if message.chat.type != "private":
        return Exception()

    forwarded_chat_info = message.forward_from_chat

    # job creation by forwarded messages only for channels
    if forwarded_chat_info.type != "channel":
        await replies.send_channels_only_error_message(update, forwarded_chat_info.type)
        return Exception()

    db_service = mongo.MongoService(update)
    # timezone must be defined in order to create new job
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if chat_entry is None:
        await replies.send_start_message(update)
        return Exception()

    # add chat to db
    chat_exists = dbutils.chat_exists(db_service, forwarded_chat_info.id)

    message = update.message
    if message is None:
        return

    from_user = message.from_user
    if from_user is None:
        return

    user_id = from_user.id
    if not chat_exists:
        dbutils.add_chat_data(
            db_service,
            chat_id=forwarded_chat_info.id,
            chat_title=forwarded_chat_info.title,
            chat_type=forwarded_chat_info.type,
            tz_offset=chat_entry.get("tz_offset"),
            utc_tz="",
            created_by=user_id,
            telegram_ts=message.date,
        )

    # add job to db
    entry = dbutils.find_latest_entry(db_service, chat_id)
    photo_group_id = message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)

    if (
        entry is not None
        and len(photo_group_id) > 0
        and photo_group_id == str(entry.get("photo_group_id", ""))
    ):  # same photo group
        photo_id = message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        payload = {"last_updated_by": user_id, "photo_id": photo_ids}
        dbutils.update_entry_by_jobname(db_service, entry, payload)
        return

    # new job to be created, assert job limit
    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        await replies.send_exceed_limit_error_message(update, user_limit)
        return Exception()

    # add new job
    content = message.caption
    content_type = ContentType.MEDIA.value
    if len(message.photo) < 1:
        content = message.text_html
        content_type = ContentType.TEXT.value
    elif photo_group_id == "":
        content = message.caption_html
        content_type = ContentType.PHOTO.value
    content = "" if content is None else content

    if poll:
        content_type = ContentType.POLL.value
        poll_val = message.poll
        if poll_val is None:
            return
        content = poll_val.to_json()

    photo_id = "" if len(message.photo) < 1 else message.photo[-1].file_id

    # populate jobname for channels
    jobname = generate_jobname(
        db_service, forwarded_chat_info.title[:6], str(chat_id))

    user_id = utils.get_user_id_from_update(update)
    if user_id is None:
        return

    dbutils.add_new_entry(
        db_service,
        chat_id=chat_id,
        channel_id=forwarded_chat_info.id,
        jobname=jobname,
        user_id=user_id,
        crontab="",
        content=content,
        content_type=content_type,
        photo_id=photo_id,
        photo_group_id=photo_group_id,
        user_bot_token=chat_entry.get("user_bot_token"),
        message_thread_id=None,
    )

    log.log_new_channel_job_added(update)
    await replies.send_request_crontab_message(update)


async def add_new_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return Exception()

    # timezone must be defined in order to create new job
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    if dbutils.find_chat_by_chatid(db_service, chat_id) is None:
        await replies.send_start_message(update)
        return Exception()

    # parse user response
    message = update.message
    if message is None:
        return

    res = utils.extract_jobs(message.text_html)
    new_job_count = len(res)

    # person limit
    message = update.message
    if message is None:
        return

    from_user = message.from_user
    if from_user is None:
        return
    user_id = from_user.id
    current_job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if current_job_count + new_job_count > user_limit:
        await replies.send_exceed_limit_error_message(update, user_limit)
        return Exception()

    successful_creation = []

    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    user_tz_offset = chat_entry.get("tz_offset")
    for crontab, text_content in res:
        # arrange next run date and time
        try:
            user_nextrun, db_nextrun = utils.calc_next_run(
                crontab, user_tz_offset)
        except Exception:
            continue

        jobname = generate_jobname(db_service, message.chat.type, str(chat_id))
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
            message_thread_id=message.message_thread_id if message.is_topic_message else None,
        )

        successful_creation.append("%s: (%s) %s" %
                                   (jobname, crontab, text_content))

    if len(successful_creation) > 0:
        log.log_new_jobs_added(update, " // ".join(successful_creation))
        postfix = "\n".join("• %s" % x for x in successful_creation)
        await replies.send_jobs_creation_success_message(update, postfix)
    else:
        await replies.send_error_message(update)


async def add_timezone(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # check validity
    message = update.message
    if message is None:
        return

    tz_values = utils.extract_tz_values(message.text)
    if not tz_values:
        await replies.send_error_message(update)
        return Exception()

    utc_tz, tz_offset = utils.calc_tz(tz_values)
    if tz_offset < -12 or tz_offset > 14:
        await replies.send_error_message(update)
        return Exception()

    db_service = mongo.MongoService(update)
    chat_exists = dbutils.chat_exists(db_service, message.chat.id)
    user_id = utils.get_user_id_from_update(update)

    if user_id is None:
        return

    if not chat_exists:
        dbutils.add_chat_data(
            db_service,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            tz_offset=tz_offset,
            utc_tz=utc_tz,
            created_by=user_id,
            telegram_ts=message.date,
        )

    await replies.send_help_message(update)


async def add_message(update: Update, context: ContextTypes.DEFAULT_TYPE, photo: bool = False, poll: bool = False):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return Exception()

    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    entry = dbutils.find_latest_entry(db_service, chat_id)
    if entry is None:
        await replies.send_simple_prompt_message(update)
        return Exception()

    last_updated_by_user = utils.get_user_id_from_update(update)
    if last_updated_by_user is None:
        return

    message = update.message
    if message is None:
        return

    payload: Dict[str, Union[int, str]] = {
        "last_updated_by": last_updated_by_user}
    photo_group_id = message.media_group_id
    photo_group_id = "" if photo_group_id is None else str(photo_group_id)
    same_photo_group = len(photo_group_id) > 0 and photo_group_id == str(
        entry.get("photo_group_id", "")
    )

    if same_photo_group:  # group of photos
        photo_id = message.photo[-1].file_id
        photo_ids = "{};{}".format(entry.get("photo_id", ""), photo_id)
        payload["photo_id"] = photo_ids
        payload["content_type"] = ContentType.MEDIA.value
    elif entry.get("content", "") != "":  # field must not be filled already
        await replies.send_prompt_new_job_message(update)
        return Exception()
    elif poll:
        payload["content_type"] = ContentType.POLL.value
        poll_val = message.poll
        if poll_val is None:
            return

        payload["content"] = poll_val.to_json()
    elif photo and photo_group_id != "":  # first photo of media group
        payload["photo_id"] = message.photo[-1].file_id
        payload["photo_group_id"] = photo_group_id
        payload["content"] = (
            "" if message.caption is None else message.caption
        )
        payload["content_type"] = ContentType.MEDIA.value
    elif photo:  # single photo
        payload["photo_id"] = message.photo[-1].file_id
        payload["photo_group_id"] = photo_group_id
        caption = "" if message.caption is None else message.caption_html
        payload["content"] = caption
        payload["content_type"] = ContentType.PHOTO.value
    else:  # only text
        payload["content"] = message.text_html
        payload["content_type"] = ContentType.TEXT.value

    dbutils.update_entry_by_jobname(db_service, entry, payload)
    log.log_new_content_added(last_updated_by_user,
                              entry.get("jobname"), chat_id)

    # reply
    if not same_photo_group:
        await replies.send_request_crontab_message(update)


async def prepare_crontab_update(update: Update, crontab, db_service):
    try:
        description = get_description(crontab).lower()
    except Exception:  # crontab is not valid
        await replies.send_invalid_crontab_message(update)
        return None, None, Exception()

    # arrange next run date and time
    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    user_tz_offset = chat_entry.get("tz_offset")
    try:
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, user_tz_offset)
    except Exception:
        await replies.send_invalid_crontab_message(update)
        return None, None, Exception()

    user_id = utils.get_user_id_from_update(update)
    if user_id is None:
        return

    # update db entry
    payload = {
        "crontab": crontab,
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "last_updated_by": user_id,
    }
    return description, payload, None


async def update_crontab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return Exception()

    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    entry = dbutils.find_latest_entry(db_service, chat_id)
    if entry is None:
        await replies.send_simple_prompt_message(update)
        return Exception()
    if entry.get("crontab", "") != "":  # field must be empty
        await replies.send_prompt_new_job_message(update)
        return Exception()

    crontab = utils.get_msg_text_from_update(update)
    if crontab is None:
        return

    res = await prepare_crontab_update(update, crontab, db_service)
    if res is None:
        return Exception()
    description, payload, err = res
    if err is not None:
        return Exception()

    message = update.message
    if message is None:
        return

    from_user = message.from_user
    if from_user is None:
        return
    user_id = from_user.id
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
        log.log_photo_transferred(
            user_id, new_photo_id, chat_id, resp.status_code)

    await replies.send_confirm_message(update, entry, description)


async def update_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = mongo.MongoService(update)
    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return Exception()

    # check validity
    msg_txt = utils.get_msg_text_from_update(update)
    tz_values = utils.extract_tz_values(msg_txt)
    if not tz_values:
        await replies.send_error_message(update)
        return Exception()

    utc_tz, tz_offset = utils.calc_tz(tz_values)
    if tz_offset < -12 or tz_offset > 14:
        return await replies.send_error_message(update)

    # retrieve current chat data
    chat_id = utils.get_chat_id_from_update(update)
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)

    if chat_entry is None:
        await replies.send_start_message(update)
        return Exception()

    if tz_offset == chat_entry.get("tz_offset", ""):
        await replies.send_timezone_nochange_error_message(update)
        return Exception()

    # update chat entry
    payload = {"tz_offset": tz_offset, "utc_tz": utc_tz}
    dbutils.update_chat_entry(db_service, chat_id, payload, "utc_tz")

    if chat_entry.get("chat_type", "") == "private":
        user_id = utils.get_user_id_from_update(update)
        dbutils.update_chats_tz_by_type(
            db_service, user_id, tz_offset, "channel")

    # update job entries
    job_entries = dbutils.find_entries_by_chatid(db_service, chat_id)
    for job_entry in job_entries:
        if job_entry.get("nextrun_ts", "") == "":
            continue
        crontab = job_entry.get("crontab", "")
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(
            crontab, tz_offset)
        payload = {"nextrun_ts": db_nextrun_ts,
                   "user_nextrun_ts": user_nextrun_ts}
        dbutils.update_entry_by_jobname(db_service, job_entry, payload)

    await replies.send_timezone_change_success_message(update, utc_tz)


def generate_jobname(db_service: mongo.MongoService, job_prefix: str, chat_id: str):
    number = 1
    jobname = "%s (%d)" % (job_prefix, number)
    while dbutils.entry_exists(db_service, chat_id, jobname):
        number = number + 1
        jobname = "%s (%d)" % (job_prefix, number)
    return jobname
