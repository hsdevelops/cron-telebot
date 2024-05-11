from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext._contexttypes import ContextTypes

delete_success_message = "Yeet! This job is now gone."
restrict_success_message = "Hurray! From now on __bot_ic__ can set up recurring messages. Run the command again to toggle the restriction setting."
timezone_change_success_message = (
    "Yipee! Your timezone has been updated to UTC__utc_tz__."
)
reset_success_messge = "Yeet! No more recurring messages in this chat."
jobs_creation_success_message = "The following recurring messages are created, /list to view all messages and their details:\n"
attribute_change_success_message = "Yipee! Your recurring message is updated successfully.\n\n/list to view all messages and their details."
sender_change_success_message = "Sender for %s is now %s. \n\nRemember to add %s into the group/channel as an admin and enable:\n1. <i>Change Group/Channel Info</i> and\n2. <i>Post Messages</i>."
sender_reset_success_message = (
    "Sender has been reset to default for chat. /changesender to set a new sender."
)


async def send_delete_success_message(update: Update) -> None:
    await update.message.reply_text(
        delete_success_message, reply_markup=ReplyKeyboardRemove()
    )


async def send_reset_success_message(context: ContextTypes, chat_id: int) -> None:
    await context.bot.send_message(chat_id, reset_success_messge)


async def send_restrict_success_message(update: Update, bot_ic: str) -> None:
    await update.message.reply_text(
        restrict_success_message.replace("__bot_ic__", bot_ic)
    )


async def send_timezone_change_success_message(update: Update, utc_tz: str) -> None:
    reply = timezone_change_success_message.replace("__utc_tz__", utc_tz)
    await update.message.reply_text(reply)


async def send_jobs_creation_success_message(
    update: Update, additional_text: str
) -> None:
    await update.message.reply_text(jobs_creation_success_message + additional_text)


async def send_attribute_change_success_message(update: Update) -> None:
    await update.message.reply_text(
        attribute_change_success_message, reply_markup=ReplyKeyboardRemove()
    )


async def send_sender_reset_success_message(update: Update) -> None:
    await update.message.reply_text(
        sender_reset_success_message, reply_markup=ReplyKeyboardRemove()
    )


async def send_sender_change_success_message(
    update: Update, chat_title: str, bot_username: str
) -> None:
    await update.message.reply_text(
        sender_change_success_message % (chat_title, bot_username, bot_username),
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
