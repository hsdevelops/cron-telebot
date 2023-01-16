from config import JOB_LIMIT_PER_PERSON
from telegram import ParseMode, ForceReply
from bot.replies.postfixes import *

error_message = "You know that's not right..."
exceed_limit_error_message = (
    "Recurring Messages currently only supports %d jobs per person, in an effort to reduce spam.\n\n__custom_message__If you need to create more than __limit__ jobs, please contact the bot owner at hs.develops.1@gmail.com specifying:\n1. the number of jobs you need, and\n2. your Telegram handle.\n\n<b>Enjoying the bot?</b>\nYou can <a href='https://www.buymeacoffee.com/rmteam'>buy the RM team a coffee</a>!"
    % (JOB_LIMIT_PER_PERSON)
)  # html
channels_only_error_message = "Job creation by forwarded messages is only enabled for channels. Please run the /add command in your __chat_type__ chat."
user_unauthorized_error_message = "Oh no... You are unauthorized to run this command. Please check with __bot_ic__ if you think this is an error."
wrong_restrction_error_message = (
    "Restriction is already set. Please ask __bot_ic__ to unset bot restriction first."
)
timezone_nochange_error_message = "Whut? That's the same timezone!"
invalid_new_job_message = "A job with this name already exists. Please /add and create a new job. If you want to override, /delete job and create again."
quiz_unavailable_message = 'Recurring messages unfortunately cannot support recurring quizzes in channels and groups... because Telegram does not return the correct option id for forwarded messages (◕︵◕) (<a href="https://docs.python-telegram-bot.org/en/v12.5.1/telegram.poll.html#telegram.Poll.correct_option_id">see docs</a>)'
invalid_crontab_message = 'This expression is invalid. Please provide a valid expression. Click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.'  # html
convo_unauthorized_message = (
    "Only the user who started this convo can continue this convo." + convo_postfix
)
no_photos_to_delete_error_message = "No photos to delete. Ending conversation..."
attribute_change_error_message = "Something went wrong on the server... Please contact the bot owner at hs.develops.1@gmail.com."


def send_error_message(update):
    update.message.reply_text(error_message)


def send_exceed_limit_error_message(update, limit):
    reply_text = exceed_limit_error_message.replace("__limit__", str(limit))
    if limit == JOB_LIMIT_PER_PERSON:
        reply_text = reply_text.replace("__custom_message__", "")
    elif limit < JOB_LIMIT_PER_PERSON:
        reply_text = reply_text.replace(
            "__custom_message__",
            "However, we have received reports of spam from you and as a result you have been blacklisted.\n\n",
        )
    else:
        reply_text = reply_text.replace(
            "__custom_message__",
            "As per prior request we have increased your limit to %d.\n\n" % limit,
        )
    update.message.reply_text(
        text=reply_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_channels_only_error_message(update, chat_type):
    reply = channels_only_error_message.replace("__chat_type__", chat_type)
    update.message.reply_text(reply)


def send_user_unauthorized_error_message(update, bot_ic):
    reply = user_unauthorized_error_message.replace("__bot_ic__", bot_ic)
    update.message.reply_text(reply)


def send_wrong_restrction_message(update, bot_ic):
    reply = wrong_restrction_error_message.replace("__bot_ic__", bot_ic)
    update.message.reply_text(reply)


def send_timezone_nochange_error_message(update):
    update.message.reply_text(timezone_nochange_error_message)


def send_invalid_crontab_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=invalid_crontab_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_invalid_new_job_message(update):
    update.message.reply_text(invalid_new_job_message)


def send_quiz_unavailable_message(update):
    update.message.reply_text(
        text=quiz_unavailable_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_no_photos_to_delete_error_message(update):
    update.message.reply_text(no_photos_to_delete_error_message)


def send_attribute_change_error_message(update):
    update.message.reply_text(attribute_change_error_message)
