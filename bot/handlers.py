from telegram.ext._contexttypes import ContextTypes
from typing import Dict

from bot.actions import actions
from bot.replies import replies
from bot.types import MESSAGE_HANDLER
from teleapi import endpoints as teleapi
from telegram import Update
from common import utils

message_handler_map: Dict[str, MESSAGE_HANDLER] = {
    replies.request_jobname_message: actions.add_new_job,
    replies.request_text_message: actions.add_message,
    replies.delete_message: actions.remove_job,
    replies.start_message: actions.add_timezone,
    replies.list_jobs_message: actions.show_job_details,
    replies.checkcron_message: actions.decrypt_cron,
    replies.request_jobs_message: actions.add_new_jobs,
    replies.request_crontab_message: actions.update_crontab,
    replies.invalid_crontab_message: actions.update_crontab,
    replies.change_timezone_message: actions.update_timezone,
}


async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    # job creation for channels
    if message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update)

    # job creation for groups/private chats
    reply_to_message = message.reply_to_message
    if reply_to_message is None:
        return

    text = reply_to_message.text_html
    handler = message_handler_map.get(text, None)
    if handler is None:
        return

    err = await handler(update, context)
    if err is None:
        teleapi.delete_message(
            message.chat.id,
            reply_to_message.message_id,
        )


async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    # job creation for channels
    if message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update)

    reply_to_message = message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(update, context, True)
        if err is None:
            teleapi.delete_message(
                message.chat.id, reply_to_message.message_id)


async def handle_polls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    # job creation for channels
    poll_type = utils.get_poll_type_from_update(update)
    if poll_type is None:
        return

    is_channel_job = message.forward_from_chat is not None
    if poll_type == "quiz" and (message.chat.type != "private" or is_channel_job):
        return await replies.send_quiz_unavailable_message(update)

    if is_channel_job:
        return await actions.add_new_channel_job(update=update, poll=True)

    reply_to_message = message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(
            update=update, context=context, photo=False, poll=True
        )
        if err is None:
            teleapi.delete_message(
                message.chat.id, reply_to_message.message_id)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return

    message = query.message
    if message is None:
        return

    if query.data == "1":
        await actions.reset_chat(update, context)

    chat_id = utils.get_chat_id_from_update(update)
    if chat_id is None:
        return

    await context.bot.editMessageReplyMarkup(
        chat_id=chat_id, message_id=message.message_id
    )
    await query.answer()
