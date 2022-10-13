from common.sheets import SheetsService
from bot import replies

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    sheets_service = SheetsService(update)

    # timezone must be defined in order to create new job
    if sheets_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    replies.send_simple_prompt_message(update)


def help(update, context):
    """Send a message when the command /help is issued."""
    replies.send_help_message(update)


def checkcron(update, context):
    """Send a message when the command /checkcron is issued."""
    replies.send_checkcron_message(update)


def add(update, context):
    """Send a message when the command /add is issued."""
    sheets_service = SheetsService(update)

    # timezone must be defined in order to create new job
    if sheets_service.retrieve_tz(update.message.chat.id) is None:
        return replies.send_start_message(update)

    # person limit
    if sheets_service.exceed_user_limit(update.message.from_user.id):
        return replies.send_exceed_limit_error_message(update)

    replies.send_request_jobname_message(update)


def delete(update, context):
    """Send a message when the command /delete is issued."""
    sheets_service = SheetsService(update)
    entries = sheets_service.get_entries_by_chatid(update.message.chat.id)

    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_delete_message(update, entries)


def list_jobs(update, context):
    """Send a message when the command /list is issued."""
    sheets_service = SheetsService(update)
    entries = sheets_service.get_entries_by_chatid(update.message.chat.id)

    if len(entries) <= 0:
        return replies.send_simple_prompt_message(update)

    replies.send_list_jobs_message(update, entries)


def list_options(update, context):
    """Send a message when the command /options is issued."""
    sheets_service = SheetsService(update)
    entries = sheets_service.get_entries_by_chatid(update.message.chat.id)

    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    replies.send_list_options_message(update)


def option_delete_previous(update, context):
    sheets_service = SheetsService(update)
    entries = sheets_service.get_entries_by_chatid(update.message.chat.id)

    if len(entries) <= 0:  # there must be at least one job available
        return replies.send_simple_prompt_message(update)

    replies.send_option_delete_previous_message(update, entries)
