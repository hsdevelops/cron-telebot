import json
from types import SimpleNamespace
from telegram.constants import ParseMode
from telegram import (
    ForceReply,
    Update,
    Message,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from bot.convos import edit
from common import log
from common.enums import ContentType
from typing import Any, Dict, List, Optional, Sequence, Union
from telegram import KeyboardButton
from telegram.ext._contexttypes import ContextTypes
from config import JOB_LIMIT_PER_PERSON
from telegram.constants import ParseMode

# custom messages
prompt_start_message = "Your chat has not been set up yet. Please /start to set up the chat with @cron_telebot."
start_message = "<b>Thank you for using Recurring Messages!</b>\n\nTo start, please tell me your UTC timezone. For example, if your timezone is UTC+08:30, enter +08:30."
help_message = 'I can help you schedule recurring messages using <a href="https://crontab.guru/">cron schedule expressions</a> (min. 1 minute intervals).\n\n<b>Available commands</b>\n/add - add a new job\n/addmultiple - add multiple jobs\n/edit - edit job details\n/list - list active jobs\n/delete - delete a job\n/reset - delete all jobs\n/changetz - edit timezone\n/changesender - change sender for group\n/options - edit permissions for group\n/checkcron - check the validity/meaning of a cron expression\n\n<b>Feeling lost?</b>\nRefer to our <a href="https://github.com/hsdevelops/cron-telebot/wiki/User-Guide">user guide</a> for more usage instructions.\n\n<b>Found a bug?</b>\nPlease contact the bot owner at <a href="mailto:hs.develops.1@gmail.com">hs.develops.1@gmail.com</a>.\n\n<b>Enjoying the bot?</b>\nYou can <a href="https://www.buymeacoffee.com/hschua">buy the creator a coffee</a>!'  # html
delete_message = (
    "Hey, tell me the name of the job you want to delete. Get /list of available jobs."
)
request_jobname_message = "Give me your job name"
request_crontab_message = 'Give me your cron schedule expression (e.g. 4 5 * * *), click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.'
request_text_message = "Now give me what you want to send"
request_jobs_message = "Reply this message with your jobs in the following format (example):\n\n0 10 * * 2 Clean up a table\n0 10 * * 4 Check the calendar\n0 14 * * 5 Check this and that and that"
simple_prompt_message = "/add to create a new job"
prompt_new_job_message = "The job already got this field. Please /add and create a new job. If you want to override, /delete job and create again."
list_jobs_message = "Choose the job you are interested to know more about. The jobs are listed on the reply keyboard."
checkcron_message = "Hey, send me your cron expression, I will decrypt it for you."
checkcron_meaning_message = "Ok, that means: "
list_options_message_group = "<b>Group options</b>\n/adminsonly - restrict bot to group admins\n/creatoronly - restrict bot to first user\n\n"
add_to_channel_message = "\n\nRemember to add RM bot into the channel as an admin and enable:\n1. <i>Change Channel Info</i> and\n2. <i>Post Messages</i>."
change_timezone_message = "Please tell me your new UTC timezone.\n\nNote that this will change the timezone for all jobs set up in this chat."
checkcron_invalid_message = "That is not a valid cron. Click <a href='https://crontab.guru/'>here</a> if you need help."  # html
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
reset_photos_confirmation_message = (
    "This will clear ALL photos for this job. Please confirm to proceed."
)


# sucess messages
delete_success_message = "Yeet! This job is now gone."
restrict_success_message = "Hurray! From now on %s can set up recurring messages. Run the command again to toggle the restriction setting."
timezone_change_success_message = "Yipee! Your timezone has been updated to UTC%s."
reset_success_messge = "Yeet! No more recurring messages in this chat."
jobs_creation_success_message = "The following recurring messages are created, /list to view all messages and their details:\n"
attribute_change_success_message = "Yipee! Your recurring message is updated successfully.\n\n/list to view all messages and their details."
sender_change_success_message = "Sender for %s is now %s. \n\nRemember to add %s into the group/channel as an admin and enable:\n1. <i>Change Group/Channel Info</i> and\n2. <i>Post Messages</i>."
sender_reset_success_message = (
    "Sender has been reset to default for chat. /changesender to set a new sender."
)


# error messages
error_message = "You know that's not right..."
exceed_limit_error_message = (
    "Recurring Messages currently only supports %s jobs per person, in an effort to reduce spam.\n\n{custom_message} If you need to create more than {limit} jobs, please contact the bot owner at hs.develops.1@gmail.com specifying:\n1. the number of jobs you need, and\n2. your Telegram handle.\n\n<b>Enjoying the bot?</b>\nYou can <a href='https://www.buymeacoffee.com/rmteam'>buy the RM team a coffee</a>!"
    % JOB_LIMIT_PER_PERSON
)  # html
user_unauthorized_error_message = "Oh no... You are unauthorized to run this command. Please check with %s if you think this is an error."
wrong_restrction_error_message = (
    "Restriction is already set. Please ask %s to unset bot restriction first."
)
timezone_nochange_error_message = "Whut? That's the same timezone!"
invalid_new_job_message = "A job with this name already exists. Please /add and create a new job, or /edit this job."
quiz_unavailable_message = 'Recurring messages unfortunately cannot support recurring quizzes in channels and groups... because Telegram does not return the correct option id for forwarded messages (◕︵◕) (<a href="https://docs.python-telegram-bot.org/en/v12.5.1/telegram.poll.html#telegram.Poll.correct_option_id">see docs</a>)'
type_unavailable_message = (
    "Recurring messages unfortunately does not support messages of this type."
)
invalid_crontab_message = 'This expression is invalid. Please provide a valid expression. Click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.'  # html
convo_unauthorized_message = (
    "Only the user who started this convo can continue this convo."
)
no_photos_to_delete_error_message = "No photos to delete. Ending conversation..."
attribute_change_error_message = "Something went wrong on the server... Please contact the bot owner at hs.develops.1@gmail.com."
private_only_error_message = "This command can only be run in private chat with %s"
group_only_error_message = "This command can only be run in groups"
missing_chats_error_message = "Please add and set up %s in a group"
missing_bot_in_group_message = "Terminating conversation... \n\nPlease add bot into the group as an admin and enable:\n1. <i>Change Channel Info</i> and\n2. <i>Post Messages</i>\nbefore running /changesender."
missing_job_error_message = 'You do not have a job named "%s". You may only /list and /delete jobs that are active.'
internal_failure_message = "Failed to create/update/remove your cron job... please try to /add or /delete again. If this happens consistently, please contact the bot owner at hs.develops.1@gmail.com."
start_error_message = "Failed to set up your chat for usage with @cron_telebot. Please try to /start again. If this happens consistently, please contact the bot owner at hs.develops.1@gmail.com."


# keyboards
def keyboard(x: Sequence[Sequence[Union[str, KeyboardButton]]]):
    return ReplyKeyboardMarkup(x, one_time_keyboard=True, resize_keyboard=True)


def keyboard_from_dict(
    entries: List[Dict], field
) -> Sequence[Sequence[Union[str, KeyboardButton]]]:
    k = []
    for i, entry in enumerate(entries):
        if i % 2 == 0:
            k.append([entry[field]])
            continue
        k[len(k) - 1].append(entry[field])
    return keyboard(k)


keyboards = SimpleNamespace(
    **{
        "cron": keyboard([["0 9 * * *", "*/5 * * * *"], ["0 0 * * 0", "30 22 1 * *"]]),
        "attrs": keyboard(
            [edit.attrs[i : i + 2] for i in range(0, len(edit.attrs), 2)]
        ),
        "inline_default": InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Confirm", callback_data=1),
                    InlineKeyboardButton("Cancel", callback_data=0),
                ]
            ]
        ),
    }
)

# other options
force_reply = ForceReply(selective=True)


# formatters
def format_job_detail(entry: Dict, bot_name: str) -> str:
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
    return reply_text


def format_add_success_message(entry: Optional[Any], cron_description: str) -> str:
    content, content_type, jobname = (
        entry["content"],
        entry["content_type"],
        entry["jobname"],
    )
    content = (
        content_type
        if content_type == ContentType.POLL.value
        else 'message "%s"' % content
    )
    return f'Ok. Done. Added a job titled "{jobname}". Your {content} will be sent {cron_description}. {"" if entry.get("channel_id", "") == "" else add_to_channel_message}'


def format_exceed_limit_reply(limit: int) -> str:
    if limit == JOB_LIMIT_PER_PERSON:
        return exceed_limit_error_message.format(custom_message="", limit=limit)

    if limit < JOB_LIMIT_PER_PERSON:
        msg = "However, we have received reports of spam from you and as a result you have been blacklisted.\n\n"
        return exceed_limit_error_message.format(custom_message=msg, limit=limit)

    msg = f"As per prior request we have increased your limit to {limit}.\n\n"
    return exceed_limit_error_message.format(custom_message=msg, limit=limit)


# send message
async def text(
    update: Update,
    msg: str,
    parse_mode=ParseMode.HTML,
    disable_web_page_preview=True,
    reply_markup=ReplyKeyboardRemove(),
) -> Optional[Message]:
    try:
        return await update.message.reply_text(
            msg,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        log.logger.error(f"[BOT] Failed to send text reply: {e}", exc_info=True)
        return None
