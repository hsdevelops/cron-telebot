from bot.convos import edit
from bot.replies import replies
from database import mongo
from bot.actions import permissions
from telegram.ext import ConversationHandler

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
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
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    # person limit
    job_count, user_limit = db_service.get_user_limit(update.message.from_user.id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    replies.send_request_jobname_message(update)


def add_multiple(update, context):
    """Send a message when the command /addmultiple is issued."""
    db_service = mongo.MongoService(update)

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    # person limit
    job_count, user_limit = db_service.get_user_limit(update.message.from_user.id)
    if job_count >= user_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    replies.send_request_jobs_message(update)


def delete(update, context):
    """Send a message when the command /delete is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_delete_message(update, entries)


def list_jobs(update, context):
    """Send a message when the command /list is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
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

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not permissions.check_rights(update, context, db_service):
        return

    return replies.send_change_timezone_message(update)


def reset(update, context):
    """Send a message when the command /reset is issued."""
    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    replies.send_reset_confirmation_message(update)


def edit(update, context):
    """Send a message when the command /edit is issued."""

    db_service = mongo.MongoService(update)
    if not permissions.check_rights(update, context, db_service):
        return

    context.user_data["user_id"] = update.message.from_user.id

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_choose_job_message(update, entries)
    return edit.state0


def cancel(update, _):
    """Send a message when the command /cancel is issued."""
    replies.send_convo_ended_message(update)
    return ConversationHandler.END
