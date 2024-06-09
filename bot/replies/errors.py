from config import JOB_LIMIT_PER_PERSON, BOT_NAME
from telegram import ForceReply, Update
from telegram.constants import ParseMode

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
invalid_new_job_message = "A job with this name already exists. Please /add and create a new job, or /edit this job."
quiz_unavailable_message = 'Recurring messages unfortunately cannot support recurring quizzes in channels and groups... because Telegram does not return the correct option id for forwarded messages (◕︵◕) (<a href="https://docs.python-telegram-bot.org/en/v12.5.1/telegram.poll.html#telegram.Poll.correct_option_id">see docs</a>)'
invalid_crontab_message = 'This expression is invalid. Please provide a valid expression. Click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.'  # html
convo_unauthorized_message = (
    "Only the user who started this convo can continue this convo."
)
no_photos_to_delete_error_message = "No photos to delete. Ending conversation..."
attribute_change_error_message = "Something went wrong on the server... Please contact the bot owner at hs.develops.1@gmail.com."
private_only_error_message = "This command can only be run in private chat with %s"
missing_chats_error_message = "Please add and set up %s in a group"
missing_bot_in_group_message = "Terminating conversation... \n\nPlease add bot into the group as an admin and enable:\n1. <i>Change Channel Info</i> and\n2. <i>Post Messages</i>\nbefore running /changesender."


async def send_error_message(update: Update) -> None:
    await update.message.reply_text(error_message)


async def send_exceed_limit_error_message(update: Update, limit: int) -> None:
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
    await update.message.reply_text(
        text=reply_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_channels_only_error_message(update: Update, chat_type: str) -> None:
    reply = channels_only_error_message.replace("__chat_type__", chat_type)
    await update.message.reply_text(reply)


async def send_user_unauthorized_error_message(update: Update, bot_ic: str) -> None:
    reply = user_unauthorized_error_message.replace("__bot_ic__", bot_ic)
    await update.message.reply_text(reply)


async def send_wrong_restriction_message(update: Update, bot_ic: str) -> None:
    reply = wrong_restrction_error_message.replace("__bot_ic__", bot_ic)
    await update.message.reply_text(reply)


async def send_timezone_nochange_error_message(update: Update) -> None:
    await update.message.reply_text(timezone_nochange_error_message)


async def send_invalid_crontab_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=invalid_crontab_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_invalid_new_job_message(update: Update) -> None:
    await update.message.reply_text(invalid_new_job_message)


async def send_quiz_unavailable_message(update: Update) -> None:
    await update.message.reply_text(
        text=quiz_unavailable_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_no_photos_to_delete_error_message(update: Update) -> None:
    await update.message.reply_text(no_photos_to_delete_error_message)


async def send_attribute_change_error_message(update: Update) -> None:
    await update.message.reply_text(attribute_change_error_message)


async def send_private_only_error_message(update: Update) -> None:
    await update.message.reply_text(private_only_error_message % BOT_NAME)


async def send_missing_chats_error_message(update: Update) -> None:
    await update.message.reply_text(missing_chats_error_message % BOT_NAME)


async def send_missing_bot_in_group_message(update: Update) -> None:
    await update.message.reply_text(
        missing_bot_in_group_message, parse_mode=ParseMode.HTML
    )
