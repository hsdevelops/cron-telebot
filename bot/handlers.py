from telegram.ext._contexttypes import ContextTypes
from typing import Dict

from bot.actions import actions
from bot.replies import replies
from common import log
from database import mongo
from teleapi import endpoints as teleapi
from telegram import Update
from typing import Optional, Callable, Coroutine, Any, Optional
from bot.convos import handlers as convo_handlers
from bot import commands

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

message_handler_map: Dict[
    str, Callable[[Any, Any], Coroutine[Any, Any, Optional[Exception]]]
] = {
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


async def handle_messages(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Exception]:
    if update.message is None:
        return

    # job creation for channels
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if update.message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update, db_service)

    # job creation for groups/private chats
    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return

    text = reply_to_message.text_html
    handler = message_handler_map.get(text, None)
    if handler is None:
        return

    err = await handler(update, context)
    if err is None:
        teleapi.delete_message(
            update.message.chat.id,
            reply_to_message.message_id,
        )


async def handle_photos(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Exception]:
    if update.message is None:
        return

    # job creation for channels
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if update.message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update, db_service)

    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(update, context, True)
        if err is None:
            teleapi.delete_message(update.message.chat.id, reply_to_message.message_id)


async def handle_polls(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Exception]:
    if update.message is None:
        return

    # job creation for channels
    is_channel_job = update.message.forward_from_chat is not None
    if update.message.poll.type == "quiz" and (
        update.message.chat.type != "private" or is_channel_job
    ):
        return await replies.send_quiz_unavailable_message(update)

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if is_channel_job:
        return await actions.add_new_channel_job(
            update=update, db_service=db_service, poll=True
        )

    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(
            update=update, context=context, photo=False, poll=True
        )
        if err is None:
            teleapi.delete_message(update.message.chat.id, reply_to_message.message_id)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == "1":
        await actions.reset_chat(update, context)
    await context.bot.editMessageReplyMarkup(
        chat_id=query.message.chat_id, message_id=query.message.message_id
    )
    await query.answer()


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    log.log_bot_error(f'Update "{update}" caused error "{context.error}"')


bot_handlers = [
    # conversations (must be declared first, not sure why)
    convo_handlers.edit_handler,
    convo_handlers.config_chat_handler,
    # on different commands - answer in Telegram
    CommandHandler("start", commands.start),
    CommandHandler("help", commands.help),
    CommandHandler("add", commands.add),
    CommandHandler("delete", commands.delete),
    CommandHandler("list", commands.list_jobs),
    CommandHandler("checkcron", commands.checkcron),
    CommandHandler("options", commands.list_options),
    CommandHandler("adminsonly", commands.option_restrict_to_admins),
    CommandHandler("creatoronly", commands.option_restrict_to_user),
    CommandHandler("changetz", commands.change_tz),
    CommandHandler("reset", commands.reset),
    CommandHandler("addmultiple", commands.add_multiple),
    # on noncommand i.e message
    MessageHandler(filters.TEXT, handle_messages),
    MessageHandler(filters.PHOTO, handle_photos),
    MessageHandler(filters.POLL, handle_polls),
    # on callback
    CallbackQueryHandler(handle_callback),
]
