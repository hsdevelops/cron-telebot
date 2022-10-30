import json
from config import JOB_LIMIT_PER_PERSON
from telegram.forcereply import ForceReply
from telegram import ParseMode, ReplyKeyboardRemove, ReplyKeyboardMarkup
from common.utils import get_value


# custom messages
start_message = "<b>Thank you for using Recurring Messages!</b>\n\nTo start, please tell me your UTC timezone. For example, if your timezone is UTC+08:30, enter +08:30.\n\n(swipe left to reply to this message)"  # html
help_message = "I can help you schedule recurring messages using <a href='https://crontab.guru/'>cron schedule expressions</a> (min. 1 minute intervals).\n\n<b>Available commands</b>\n/add - add a new job\n/list - list created jobs\n/delete - delete a job\n/options - view advanced job options\n/checkcron - check the validity/meaning of a cron expression\n/changetz - update timezone\n\n<b>Feeling lost?</b>\nRefer to our <a href='https://github.com/hsdevelops/rm-bot/wiki/User-Guide'>user guide</a> for more usage instructions.\n\n<b>Found a bug?</b>\nPlease contact the bot owner at hs.develops.1@gmail.com.\n\n<b>Enjoying the bot?</b>\nYou can <a href='https://www.buymeacoffee.com/rmteam'>buy the RM team a coffee</a>!"  # html
delete_message = "Hey, tell me the name of the job you want to delete. Get /list of available jobs.\n\n(swipe left to reply to this message)"
request_jobname_message = (
    "Give me your job name\n\n(swipe left to reply to this message)"
)
request_crontab_message = 'Give me your cron schedule expression (e.g. 4 5 * * *), click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.\n\n(swipe left to reply to this message)'  # html
request_text_message = (
    "Now give me what you want to send\n\n(swipe left to reply to this message)"
)
simple_prompt_message = "/add to create a new job"
prompt_new_job_message = "The job already got this field. Please /add and create a new job. If you want to override, /delete job and create again."
invalid_new_job_message = "A job with this name already exists. Please /add and create a new job. If you want to override, /delete job and create again."
confirm_message_append = "To set advanced options, please use /options."
invalid_crontab_message = 'This expression is invalid. Please provide a valid expression. Click <a href="https://crontab.guru/">here</a> if you need help. Use /checkcron to check your cron expression.'  # html
list_jobs_message = "Hey, choose the job you are interested to know more about. The jobs are listed on the reply keyboard.\n\n(swipe left to reply to this message)"
delete_success_message = "Yeet! This job is now gone."
error_message = "You know that's not right..."
checkcron_message = "Hey, send me your cron expression, I will decrypt it for you.\n\n(swipe left to reply to this message)"
checkcron_invalid_message = "Alright, that is not a valid cron. Click <a href='https://crontab.guru/'>here</a> if you need help."  # html
checkcron_meaning_message = "Ok, that means: "
list_options_message_group = "<b>Group options</b>\n/adminsonly - restrict bot to group admins\n/creatoronly - restrict bot to first user\n\n"
list_options_message = "__additional_commands__<b>Job options</b>\n/deleteprevious - delete the previous message when the next message is sent. Disabled by default. Note that this option is subject to the limitations mentioned in the <a href='https://core.telegram.org/bots/api#deletemessage'>Telegram API documentation</a>.\n\nTo request for a new feature, please contact the bot owner at hs.develops.1@gmail.com.\n\n<b>Enjoying the bot?</b>\nYou can <a href='https://www.buymeacoffee.com/rmteam'>buy the RM team a coffee</a>!"  # html
option_delete_previous_message = "Tell me the name of the job you want to toggle the /deleteprevious option for. The jobs are listed on the reply keyboard.\n\n(swipe left to reply to this message)"
exceed_limit_error_message = (
    "Recurring Messages currently only supports %d jobs per person, in an effort to reduce spam.\n\nIf you need to create more than %d jobs, please contact the bot owner at hs.develops.1@gmail.com specifying:\n1. the number of jobs you need, and\n2. your Telegram handle.\n\n<b>Enjoying the bot?</b>\nYou can <a href='https://www.buymeacoffee.com/rmteam'>buy the RM team a coffee</a>!"
    % (JOB_LIMIT_PER_PERSON, JOB_LIMIT_PER_PERSON)
)  # html
channels_only_error_message = "Job creation by forwarded messages is only enabled for channels. Please run the /add command in your __chat_type__ chat."
add_to_channel_message = "\n\nRemember to add RM bot into the channel as an admin and enable:\n1. <i>Change Channel Info</i> and\n2. <i>Post Messages</i>."
user_unauthorized_error_message = "Oh no... You are unauthorized to run this command. Please check with __bot_ic__ if you think this is an error."
restrict_success_message = "Hurray! From now on __bot_ic__ can set up recurring messages. Run the command again to toggle the restriction setting."
wrong_restrction_error_message = (
    "Restriction is already set. Please ask __bot_ic__ to unset bot restriction first."
)
channel_quiz_unavailable_message = 'Recurring messages unfortunately cannot support recurring quizzes in channels... because Telegram does not return the correct option id for forwarded messages (◕︵◕) (<a href="https://docs.python-telegram-bot.org/en/v12.5.1/telegram.poll.html#telegram.Poll.correct_option_id">see docs</a>)'
change_timezone_message = "Please tell me your new UTC timezone.\n\nNote that this will change the timezone for all jobs set up in this chat.\n\n(swipe left to reply to this message)"
timezone_nochange_error_message = "Whut? That's the same timezone!"
timezone_change_success_message = (
    "Yipee! Your timezone has been updated to UTC__utc_tz__."
)


def prepare_keyboard(entries):
    keyboard = []
    for i, row in enumerate(entries):
        if i % 2 == 0:
            keyboard.append([row.get("jobname")])
            continue
        keyboard[len(keyboard) - 1].append(row.get("jobname"))
    return keyboard


def send_start_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=start_message,
        parse_mode=ParseMode.HTML,
    )


def send_help_message(update):
    update.message.reply_text(
        help_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


def send_checkcron_message(update):
    update.message.reply_text(
        checkcron_message, reply_markup=ForceReply(selective=True)
    )


def send_exceed_limit_error_message(update):
    update.message.reply_text(
        text=exceed_limit_error_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_request_jobname_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True), text=request_jobname_message
    )


def send_simple_prompt_message(update):
    update.message.reply_text(simple_prompt_message)


def send_delete_message(update, entries):
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )

    update.message.reply_text(delete_message, reply_markup=reply_markup)


def send_list_jobs_message(update, entries):
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.message.reply_text(list_jobs_message, reply_markup=reply_markup)


def send_list_options_message(update, is_group):
    reply = list_options_message.replace(
        "__additional_commands__", list_options_message_group if is_group else ""
    )
    update.message.reply_text(
        reply,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_option_delete_previous_message(update, entries):
    keyboard = prepare_keyboard(entries)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.message.reply_text(option_delete_previous_message, reply_markup=reply_markup)


def send_job_details(update, entry_df):
    photo_id = str(get_value(entry_df, "photo_id"))
    content = get_value(entry_df, "content")

    content_type = get_value(entry_df, "content_type")
    if content_type == "poll":
        content = "(Poll) %s" % json.loads(content).get("question")

    reply_text = "<b>Job name</b>: {}\n<b>Cron</b>: {}\n<b>Content</b>: {}\n<b>Photos</b>: {}\n<b>Category</b>: {}\n<b>Next run</b>: {}\n\n<b>Advanced options</b>\n/deleteprevious: {}".format(
        get_value(entry_df, "jobname"),
        get_value(entry_df, "crontab"),
        content,
        "no" if photo_id == "" else len(photo_id.split(";")),
        "in-chat" if get_value(entry_df, "channel_id") == "" else "channel",
        get_value(entry_df, "user_nextrun_ts"),
        "enabled"
        if get_value(entry_df, "option_delete_previous") != ""
        else "disabled",
    )
    update.message.reply_text(
        reply_text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove()
    )


def send_error_message(update):
    update.message.reply_text(error_message)


def send_exceed_limit_error_message(update):
    update.message.reply_text(
        text=exceed_limit_error_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_invalid_new_job_message(update):
    update.message.reply_text(invalid_new_job_message)


def send_request_crontab_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=request_crontab_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_request_text_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=request_text_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_confirm_message(update, entry_df, cron_description):
    content = (
        "poll"
        if get_value(entry_df, "content_type") == "poll"
        else 'message "%s"' % get_value(entry_df, "content")
    )
    update.message.reply_text(
        text='Ok. Done. Added a job titled "{}". Your {} will be sent {}. {} {}'.format(
            get_value(entry_df, "jobname"),
            content,
            cron_description,
            confirm_message_append,
            "" if get_value(entry_df, "channel_id") == "" else add_to_channel_message,
        ),
        parse_mode=ParseMode.HTML,
    )


def send_delete_success_message(update):
    update.message.reply_text(
        delete_success_message, reply_markup=ReplyKeyboardRemove()
    )


def send_invalid_crontab_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True),
        text=invalid_crontab_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_checkcron_invalid_message(update):
    update.message.reply_text(
        text=checkcron_invalid_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_checkcron_meaning_message(update, cron_description):
    update.message.reply_text(checkcron_meaning_message + cron_description)


def send_prompt_new_job_message(update):
    update.message.reply_text(prompt_new_job_message)


def send_advanced_option_success_message(update, option, new_option_value):
    update.message.reply_text(
        "The /{} option is now {} for {}. Cheers!".format(
            option,
            "enabled" if new_option_value != "" else "disabled",
            update.message.text,
        ),
        reply_markup=ReplyKeyboardRemove(),
    )


def send_channels_only_error_message(update, chat_type):
    update.message.reply_text(
        channels_only_error_message.replace("__chat_type__", chat_type)
    )


def send_user_unauthorized_error_message(update, bot_ic):
    update.message.reply_text(
        user_unauthorized_error_message.replace("__bot_ic__", bot_ic)
    )


def send_wrong_restrction_message(update, bot_ic):
    update.message.reply_text(
        wrong_restrction_error_message.replace("__bot_ic__", bot_ic)
    )


def send_restrict_success_message(update, bot_ic):
    update.message.reply_text(restrict_success_message.replace("__bot_ic__", bot_ic))


def send_channel_quiz_unavailable_message(update):
    update.message.reply_text(
        text=channel_quiz_unavailable_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_change_timezone_message(update):
    update.message.reply_text(
        reply_markup=ForceReply(selective=True), text=change_timezone_message
    )


def send_timezone_nochange_error_message(update):
    update.message.reply_text(timezone_nochange_error_message)


def send_timezone_change_success_message(update, utc_tz):
    update.message.reply_text(
        timezone_change_success_message.replace("__utc_tz__", utc_tz)
    )
