import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


# bot
def log_new_job_added(update):
    logger.info(
        '[BOT] User "%s" successfully added new job "%s" in room "%s", chat_id=%s',
        update.message.from_user.id,
        update.message.text,
        update.message.chat.title,
        update.message.chat.id,
    )


def log_new_jobs_added(update, jobs_string):
    logger.info(
        '[BOT] User "%s" successfully added several jobs "%s" in room "%s", chat_id=%s',
        update.message.from_user.id,
        jobs_string,
        update.message.chat.title,
        update.message.chat.id,
    )


def log_new_channel_job_added(update):
    logger.info(
        '[BOT] User "%s" successfully added new job/content for a channel, chat_id=%s',
        update.message.from_user.id,
        update.message.chat.id,
    )


def log_new_content_added(last_updated_by, jobname, chat_id):
    logger.info(
        '[BOT] User "%s" successfully added new message content for job "%s", chat_id=%s',
        last_updated_by,
        jobname,
        chat_id,
    )


def log_new_channel_jobname_added(entry):
    logger.info(
        '[BOT] User "%s" successfully added jobname "%s" in channel, channel_id=%s, chat_id=%s',
        entry.get("last_updated_by"),
        entry.get("jobname"),
        entry.get("channel_id"),
        entry.get("chat_id"),
    )


def log_crontab_updated(last_updated_by, jobname, chat_id):
    logger.info(
        '[BOT] User "%s" successfully added new crontab for job "%s", chat_id=%s',
        last_updated_by,
        jobname,
        chat_id,
    )


def log_job_removed(last_updated_by, jobname, chat_id):
    logger.info(
        '[BOT] User "%s" successfully removed job "%s", chat_id=%s',
        last_updated_by,
        jobname,
        chat_id,
    )


def log_option_updated(updated_fields, option, jobname, chat_id):
    logger.info(
        '[BOT] User "%s" successfully updated option "%s" to "%s" for job "%s", chat_id=%s',
        updated_fields["last_updated_by"],
        option,
        updated_fields[option],
        jobname,
        chat_id,
    )


def log_chat_reset(update):
    logger.info(
        '[BOT] User "%s" successfully reset chat, chat_id=%s',
        update.callback_query.from_user.id,
        update.callback_query.message.chat_id,
    )


# database
def log_new_entry(jobname, chat_id):
    logger.info(
        '[DB] Created new job, jobname="%s", chat_id=%s',
        jobname,
        str(chat_id),
    )


def log_new_chat(chat_id, chat_title):
    logger.info(
        "[DB] Created new chat entry, chat_id=%s, chat_title=%s",
        str(chat_id),
        chat_title,
    )


def log_new_user(user_id, username):
    logger.info(
        '[DB] Created new user, user_id=%s, username="%s"',
        str(user_id),
        username,
    )


def log_entry_updated(entry):
    logger.info(
        '[DB] Updated job entry "%s", chat_id=%s',
        entry.get("jobname"),
        str(entry.get("chat_id")),
    )


def log_chat_entry_updated(chat_id, updated_field, updated_value):
    logger.info(
        '[DB] Updated chat %s to "%s", chat_id=%s',
        updated_field,
        updated_value,
        chat_id,
    )


def log_chats_tz_updated_by_type(count, user_id, chat_type, tz_offset):
    logger.info(
        "[DB] Bulk updated timezone for %d chats, chat_type=%s, user_id=%s, new tz_offset=%d",
        count,
        chat_type,
        user_id,
        tz_offset,
    )


def log_user_updated(entry):
    logger.info(
        '[DB] Superseded user, user_id=%s, field_changed="%s"',
        entry.get("user_id"),
        entry.get("field_changed"),
    )


def log_username_updated(update):
    logger.info(
        "[DB] Superseded username, new username=%s, user_id=%s",
        update.message.from_user.username,
        update.message.from_user.id,
    )


def log_firstname_updated(update):
    logger.info(
        "[DB] Superseded first_name, new first_name=%s, username=%s, user_id=%s",
        update.message.from_user.first_name,
        update.message.from_user.username,
        update.message.from_user.id,
    )


# api
def log_api_previous_message_deletion(chat_id, message_id, status_code):
    logger.info(
        "[TELEGRAM API] Deleted previous message, response_status=%s, chat_id=%s, message_id=%s",
        status_code,
        chat_id,
        message_id,
    )


def log_api_send_message(chat_id, content, status_code):
    logger.info(
        '[TELEGRAM API] Sent message, response_status=%s, chat_id=%s, message="%s"',
        status_code,
        chat_id,
        content,
    )


def log_entry_count(count):
    logger.info("Processing %d message(s) to send this time...", count)


def log_completion(processed_count, total_count):
    logger.info("Finished processing %d/%d messages", processed_count, total_count)
