from telegram import Update
from bot.convos import config_chat, edit
from bot.replies import replies
from database import mongo
from database.dbutils import dbutils
from bot.actions import permissions


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, _):
    """Send a message when the command /start is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to create new job
    if dbutils.find_chat_by_chatid(db_service, update.message.chat.id) is None:
        return replies.send_start_message(update)

    replies.send_simple_prompt_message(update)


def help(update, _):
    """Send a message when the command /help is issued."""
    replies.send_help_message(update)


def checkcron(update, _):
    """Send a message when the command /checkcron is issued."""
    replies.send_checkcron_message(update)


def add(update, context):
    """Send a message when the command /add is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to create new job
    if dbutils.find_chat_by_chatid(db_service, update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    # person limit
    user_id = update.message.from_user.id
    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    replies.send_request_jobname_message(update)


def add_multiple(update, context):
    """Send a message when the command /addmultiple is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to create new job
    if dbutils.find_chat_by_chatid(db_service, update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    # person limit
    user_id = update.message.from_user.id
    job_count, user_limit = dbutils.get_user_limit(db_service, user_id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    replies.send_request_jobs_message(update)


def delete(update, context):
    """Send a message when the command /delete is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_delete_message(update, entries)


def list_jobs(update, context):
    """Send a message when the command /list is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_list_jobs_message(update, entries)


def list_options(update, _):
    """Send a message when the command /options is issued."""
    is_group = update.message.chat.type in ["group", "supergroup"]
    if is_group:
        replies.send_list_options_message(update)


def option_restrict_to_admins(update, context):
    """Send a message when the command /adminsonly is issued."""
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service, True):
        return

    return permissions.restrict_to_admins(update, db_service)


def option_restrict_to_user(update, context):
    """Send a message when the command /creatoronly is issued."""

    if update.message.chat.type not in ["group", "supergroup"]:
        return

    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    return permissions.restrict_to_user(update, db_service)


def change_tz(update, context):
    """Send a message when the command /changetz is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to change tz
    if dbutils.find_chat_by_chatid(db_service, update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    return replies.send_change_timezone_message(update)


def change_sender(update: Update, _):
    """Send a message when the command /changesender is issued."""
    db_service = mongo.MongoService(update)

    # find groups/private/channel created by user
    user_id = update.message.from_user.id
    chat_type = update.message.chat.type

    if chat_type != "private":
        return replies.send_private_only_error_message(update)

    chat_entries = dbutils.find_groups_created_by(db_service, user_id)
    if len(chat_entries) <= 0:
        return replies.send_missing_chats_error_message(update)

    replies.send_choose_chat_message(update, chat_entries)
    return config_chat.state0


def reset(update, context):
    """Send a message when the command /reset is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    replies.send_reset_confirmation_message(update)


def edit_job(update, context):
    """Send a message when the command /edit is issued."""

    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    context.user_data["user_id"] = update.message.from_user.id

    entries = dbutils.find_entries_by_chatid(db_service, update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_choose_job_message(update, entries)
    return edit.state0
