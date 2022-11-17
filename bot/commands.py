from database.db import Database
from bot import replies, actions

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    db_service = Database(update).service

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
    db_service = Database(update).service

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not actions.check_rights(update, context, db_service):
        return

    # person limit
    exceed_limit, user_limit = db_service.exceed_user_limit(update.message.from_user.id)
    if exceed_limit:
        return replies.send_exceed_limit_error_message(update, user_limit)

    replies.send_request_jobname_message(update)


def delete(update, context):
    """Send a message when the command /delete is issued."""
    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_delete_message(update, entries)


def list_jobs(update, context):
    """Send a message when the command /list is issued."""
    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_list_jobs_message(update, entries)


def list_options(update, context):
    """Send a message when the command /options is issued."""
    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    is_group = update.message.chat.type in ["group", "supergroup"]
    replies.send_list_options_message(update, is_group)


def option_delete_previous(update, context):
    """Send a message when the command /deleteprevious is issued."""
    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service):
        return

    entries = db_service.get_entries_by_chatid(update.message.chat.id)
    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    replies.send_option_delete_previous_message(update, entries)


def option_restrict_to_admins(update, context):
    """Send a message when the command /adminsonly is issued."""
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service, True):
        return

    return actions.restrict_to_admins(update, db_service)


def option_restrict_to_user(update, context):
    """Send a message when the command /creatoronly is issued."""

    if update.message.chat.type not in ["group", "supergroup"]:
        return

    db_service = Database(update).service
    if not actions.check_rights(update, context, db_service):
        return

    return actions.restrict_to_user(update, db_service)


def change_tz(update, context):
    """Send a message when the command /changetz is issued."""
    db_service = Database(update).service

    # timezone must be defined in order to create new job
    if db_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    if not actions.check_rights(update, context, db_service):
        return

    return replies.send_change_timezone_message(update)
