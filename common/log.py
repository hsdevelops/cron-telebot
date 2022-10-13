import logging
from common.utils import get_value

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


# bot
def log_new_job_added(update):
    logger.info(
        '[BOT] User "%s" successfully added new job "%s" added in room "%s", chat_id=%s',
        update.message.text,
        update.message.from_user.id,
        update.message.chat.title,
        update.message.chat.id,
    )


def log_new_channel_job_added(update):
    logger.info(
        '[BOT] User "%s" successfully added new job/content for a channel, chat_id=%s',
        update.message.from_user.id,
        update.message.chat.id,
    )


def log_new_content_added(entry_df):
    logger.info(
        '[BOT] User "%s" successfully added new message content for job "%s", chat_id=%s',
        get_value(entry_df, "last_updated_by"),
        get_value(entry_df, "jobname"),
        get_value(entry_df, "chat_id"),
    )


def log_new_channel_jobname_added(entry_df):
    logger.info(
        '[BOT] User "%s" successfully added jobname "%s" in channel, channel_id=%s, chat_id=%s',
        get_value(entry_df, "last_updated_by"),
        get_value(entry_df, "jobname"),
        get_value(entry_df, "channel_id"),
        get_value(entry_df, "chat_id"),
    )


def log_crontab_updated(entry_df):
    logger.info(
        '[BOT] User "%s" successfully added new crontab for job "%s", chat_id=%s',
        get_value(entry_df, "last_updated_by"),
        get_value(entry_df, "jobname"),
        get_value(entry_df, "chat_id"),
    )


def log_job_removed(entry_df):
    logger.info(
        '[BOT] User "%s" successfully removed job "%s", chat_id=%s',
        get_value(entry_df, "last_updated_by"),
        get_value(entry_df, "jobname"),
        get_value(entry_df, "chat_id"),
    )


def log_option_updated(entry_df, option):
    logger.info(
        '[BOT] User "%s" successfully updated option "%s" to "%s" for job "%s", chat_id=%s',
        get_value(entry_df, "last_updated_by"),
        option,
        get_value(entry_df, option),
        get_value(entry_df, "jobname"),
        get_value(entry_df, "chat_id"),
    )


# sheets
def log_new_entry(jobname, chat_id):
    logger.info(
        '[SHEET] Created new job, jobname="%s", chat_id=%s',
        jobname,
        str(chat_id),
    )


def log_new_chat(chat_id, chat_title):
    logger.info(
        "[SHEET] Created new chat entry, chat_id=%s, chat_title=%s",
        str(chat_id),
        chat_title,
    )


def log_new_user(user_id, username):
    logger.info(
        '[SHEET] Created new user, user_id=%s, username="%s"',
        str(user_id),
        username,
    )


def log_entry_updated(entry):
    logger.info(
        '[SHEET] Updated job entry "%s", chat_id=%s',
        get_value(entry, "jobname"),
        str(get_value(entry, "chat_id")),
    )


def log_user_updated(entry):
    logger.info(
        '[SHEET] Superseded user, user_id=%s, field_changed="%s"',
        get_value(entry, "user_id"),
        get_value(entry, "field_changed"),
    )


def log_username_updated(update):
    logger.info(
        "[SHEET] Superseded username, new username=%s, user_id=%s",
        update.message.from_user.username,
        update.message.from_user.id,
    )


def log_firstname_updated(update):
    logger.info(
        "[SHEET] Superseded first_name, new first_name=%s, username=%s, user_id=%s",
        update.message.from_user.first_name,
        update.message.from_user.username,
        update.message.from_user.id,
    )


# api
def log_api_previous_message_deletion(chat_id, message_id, status_code):
    logger.info(
        '[TELEGRAM API] Deleted previous message, response_status=%s, chat_id=%s, message_id="%s"',
        chat_id,
        message_id,
        status_code,
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
