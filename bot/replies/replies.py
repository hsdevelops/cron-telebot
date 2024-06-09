import json
from telegram.constants import ParseMode
from telegram import (
    ForceReply,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from bot.replies.success import *
from bot.replies.errors import *
from bot.convos import edit
from common.enums import ContentType
from typing import Any, List, Optional, Sequence, Union
from telegram import KeyboardButton

# custom messages
# html
start_message = "<b>Thank you for using Recurring Messages!</b>\n\nTo start, please tell me your UTC timezone. For example, if your timezone is UTC+08:30, enter +08:30.\n\n(swipe left to reply to this message)"
help_message = 'I can help you schedule recurring messages using <a href="https://crontab.guru/">cron schedule expressions</a> (min. 1 minute intervals).\n\n<b>Available commands</b>\n/add - add a new job\n/addmultiple - add multiple jobs\n/edit - edit job details\n/list - list active jobs\n/delete - delete a job\n/reset - delete all jobs\n/changetz - edit timezone\n/changesender - change sender for group\n/options - edit permissions for group\n/checkcron - check the validity/meaning of a cron expression\n\n<b>Feeling lost?</b>\nRefer to our <a href="https://github.com/hsdevelops/cron-telebot/wiki/User-Guide">user guide</a> for more usage instructions.\n\n<b>Found a bug?</b>\nPlease contact the bot owner at <a href="mailto:hs.develops.1@gmail.com">hs.develops.1@gmail.com</a>.\n\n<b>Enjoying the bot?</b>\nYou can <a href="https://www.buymeacoffee.com/hschua">buy the creator a coffee</a>!'  # html
delete_message = "Hey, tell me the name of the job you want to delete. Get /list of available jobs.\n\n(swipe left to reply to this message)"
request_jobname_message = (
    "Give me your job name\n\n(swipe left to reply to this message)"
)
# html
request_crontab_message = 'Give me your cron schedule expression (e.g. 4 5 * * *), click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.\n\n(swipe left to reply to this message)'
request_text_message = (
    "Now give me what you want to send\n\n(swipe left to reply to this message)"
)
request_jobs_message = "Reply this message with your jobs in the following format (example):\n\n0 10 * * 2 Clean up a table\n0 10 * * 4 Check the calendar\n0 14 * * 5 Check this and that and that\n\n(swipe left to reply to this message)"
simple_prompt_message = "/add to create a new job"
prompt_new_job_message = "The job already got this field. Please /add and create a new job. If you want to override, /delete job and create again."
list_jobs_message = "Choose the job you are interested to know more about. The jobs are listed on the reply keyboard.\n\n(swipe left to reply to this message)"
checkcron_message = "Hey, send me your cron expression, I will decrypt it for you.\n\n(swipe left to reply to this message)"
checkcron_meaning_message = "Ok, that means: "
list_options_message_group = "<b>Group options</b>\n/adminsonly - restrict bot to group admins\n/creatoronly - restrict bot to first user\n\n"
add_to_channel_message = "\n\nRemember to add RM bot into the channel as an admin and enable:\n1. <i>Change Channel Info</i> and\n2. <i>Post Messages</i>."
change_timezone_message = "Please tell me your new UTC timezone.\n\nNote that this will change the timezone for all jobs set up in this chat.\n\n(swipe left to reply to this message)"
checkcron_invalid_message = "Alright, that is not a valid cron. Click <a href='https://crontab.guru/'>here</a> if you need help."  # html
reset_confirmation_message = (
    "This will delete all the recurring message set up in this chat. Confirm?"
)

# convo
choose_job_message = (
    "Choose the job you want to edit. The jobs are listed on the reply keyboard."
)
choose_attribute_message = "Which attribute would you like to change?"
prompt_new_value_message = "What would you like to change it to?"
choose_chat_message = "Which chat would you like to change the sender for?"
prompt_user_bot_message = "This will change the message sender to the selected chat.\n\nPlease send me your bot token:"
convo_ended_message = "Terminating previous conversation...\n\n/add another recurring message or /edit an existing one."
reset_photos_confirmation_message = "This will clear ALL photos for this job. Proceed?"


def prepare_keyboard(
    entries: List[Optional[Any]], field: str = "jobname"
) -> Sequence[Sequence[Union[str, KeyboardButton]]]:
    keyboard = []
    for i, entry in enumerate(entries):
        if i % 2 == 0:
            keyboard.append([entry[field]])
            continue
        keyboard[len(keyboard) - 1].append(entry[field])
    return keyboard


async def send_start_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=start_message,
        parse_mode=ParseMode.HTML,
    )


async def send_help_message(update: Update) -> None:
    await update.message.reply_text(
        help_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def send_checkcron_message(update: Update) -> None:
    await update.message.reply_text(
        checkcron_message, reply_markup=ForceReply(selective=True)
    )


async def send_request_jobname_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True), text=request_jobname_message
    )


async def send_request_jobs_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=request_jobs_message,
        parse_mode=ParseMode.HTML,
    )


async def send_simple_prompt_message(update: Update) -> None:
    await update.message.reply_text(simple_prompt_message)


async def send_delete_message(update: Update, entries: List[Optional[Any]]) -> None:
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )

    await update.message.reply_text(delete_message, reply_markup=reply_markup)


async def send_list_jobs_message(update: Update, entries: List[Optional[Any]]) -> None:
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(list_jobs_message, reply_markup=reply_markup)


async def send_choose_job_message(update: Update, entries: List[Optional[Any]]) -> None:
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(choose_job_message, reply_markup=reply_markup)


async def send_choose_attribute_message(update: Update) -> None:
    keyboard = [edit.attrs[i : i + 2] for i in range(0, len(edit.attrs), 2)]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(choose_attribute_message, reply_markup=reply_markup)


async def send_list_options_message(update: Update) -> None:
    await update.message.reply_text(
        list_options_message_group,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_reset_confirmation_message(update: Update) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data=1),
            InlineKeyboardButton("Cancel", callback_data=0),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        reset_confirmation_message, reply_markup=reply_markup
    )


async def send_job_details(update: Update, entry: Optional[Any], bot_name: str) -> None:
    photo_id = str(entry.get("photo_id", ""))
    content = entry.get("content", "")

    content_type = entry.get("content_type", "")
    if content_type == ContentType.POLL.value:
        content = "(Poll) %s" % json.loads(content).get("question")

    is_paused = entry.get("paused_ts", "") != ""
    reply_text = "<b>Job name</b>: {}\n<b>Cron</b>: {}\n<b>Content</b>: {}\n<b>Photos</b>: {}\n<b>Category</b>: {}\n<b>Next run</b>: {}\n\n<b>Advanced options</b>\nDelete previous: {}\nSender: {}\n\n/edit".format(
        entry.get("jobname", ""),
        entry.get("crontab", ""),
        content,
        "no" if photo_id == "" else len(photo_id.split(";")),
        "in-chat" if entry.get("channel_id", "") == "" else "channel",
        "paused" if is_paused else entry.get("user_nextrun_ts", ""),
        "enabled" if entry.get("option_delete_previous", "") != "" else "disabled",
        bot_name,
    )
    await update.message.reply_text(
        reply_text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove()
    )


async def send_request_crontab_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=request_crontab_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_request_text_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=request_text_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_confirm_message(
    update: Update, entry: Optional[Any], cron_description: str
) -> None:
    content = 'message "%s"' % entry.get("content")
    if entry.get("content_type") == ContentType.POLL.value:
        content = ContentType.POLL.value
    await update.message.reply_text(
        text='Ok. Done. Added a job titled "{}". Your {} will be sent {}. {}'.format(
            entry.get("jobname"),
            content,
            cron_description,
            "" if entry.get("channel_id", "") == "" else add_to_channel_message,
        ),
        parse_mode=ParseMode.HTML,
    )


async def send_checkcron_invalid_message(update: Update) -> None:
    await update.message.reply_text(
        text=checkcron_invalid_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def send_checkcron_meaning_message(update: Update, cron_description: str) -> None:
    await update.message.reply_text(checkcron_meaning_message + cron_description)


async def send_prompt_new_job_message(update: Update) -> None:
    await update.message.reply_text(prompt_new_job_message)


async def send_change_timezone_message(update: Update) -> None:
    await update.message.reply_text(
        reply_markup=ForceReply(selective=True), text=change_timezone_message
    )


async def send_convo_ended_message(update: Update) -> None:
    await update.message.reply_text(
        convo_ended_message, reply_markup=ReplyKeyboardRemove()
    )


async def send_prompt_new_value_message(update: Update) -> None:
    await update.message.reply_text(
        prompt_new_value_message,
        reply_markup=ForceReply(selective=True),
    )


async def send_reset_photos_confirmation_message(update: Update) -> None:
    keyboard = [["yes", "no"]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(
        reset_photos_confirmation_message, reply_markup=reply_markup
    )


async def send_prompt_user_bot_message(update: Update) -> None:
    await update.message.reply_text(
        prompt_user_bot_message, reply_markup=ReplyKeyboardRemove()
    )


async def send_choose_chat_message(
    update: Update, entries: List[Optional[Any]]
) -> None:
    keyboard = prepare_keyboard(entries, field="chat_title")
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(choose_chat_message, reply_markup=reply_markup)
