from telegram import ReplyKeyboardRemove

delete_success_message = "Yeet! This job is now gone."
restrict_success_message = "Hurray! From now on __bot_ic__ can set up recurring messages. Run the command again to toggle the restriction setting."
timezone_change_success_message = (
    "Yipee! Your timezone has been updated to UTC__utc_tz__."
)
reset_success_messge = "Yeet! No more recurring messages in this chat."
jobs_creation_success_message = (
    "The following recurring messages are created, /list to view all messages:\n"
)
attribute_change_success_message = "Yipee! Your recurring message is updated successfully.\n\n/list to view all messages and their details."


def send_delete_success_message(update):
    update.message.reply_text(
        delete_success_message, reply_markup=ReplyKeyboardRemove()
    )


def send_reset_success_message(context, chat_id):
    context.bot.send_message(chat_id, reset_success_messge)


def send_restrict_success_message(update, bot_ic):
    update.message.reply_text(restrict_success_message.replace("__bot_ic__", bot_ic))


def send_timezone_change_success_message(update, utc_tz):
    reply = timezone_change_success_message.replace("__utc_tz__", utc_tz)
    update.message.reply_text(reply)


def send_jobs_creation_success_message(update, additional_text):
    update.message.reply_text(jobs_creation_success_message + additional_text)


def send_attribute_change_success_message(update):
    update.message.reply_text(
        attribute_change_success_message, reply_markup=ReplyKeyboardRemove()
    )
