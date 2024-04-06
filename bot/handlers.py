from telegram.ext._contexttypes import ContextTypes

from bot.actions import actions
from bot.replies import replies
from teleapi import endpoints as teleapi


async def handle_messages(update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    # job creation for channels
    if update.message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update)

    # job creation for groups/private chats
    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return
    text = reply_to_message.text_html
    if text == replies.request_jobname_message:
        err = await actions.add_new_job(update, context)
    elif text == replies.request_text_message:
        err = await actions.add_message(update, context)
    elif text == replies.delete_message:
        err = await actions.remove_job(update, context)
    elif text == replies.start_message:
        err = await actions.add_timezone(update)
    elif text == replies.list_jobs_message:
        err = await actions.show_job_details(update, context)
    elif text == replies.checkcron_message:
        err = await actions.decrypt_cron(update)
    elif text == replies.request_jobs_message:
        err = await actions.add_new_jobs(update, context)
    elif (
        text == replies.request_crontab_message
        or text == replies.invalid_crontab_message
    ):
        err = await actions.update_crontab(update, context)
    elif text == replies.change_timezone_message:
        err = await actions.update_timezone(update, context)
    else:
        err = None

    if err is None:
        teleapi.delete_message(update.message.chat.id, reply_to_message.message_id)


async def handle_photos(update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    # job creation for channels
    if update.message.forward_from_chat is not None:
        return await actions.add_new_channel_job(update)

    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(update, context, True)
        if err is None:
            teleapi.delete_message(update.message.chat.id, reply_to_message.message_id)


async def handle_polls(update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    # job creation for channels
    is_channel_job = update.message.forward_from_chat is not None
    if update.message.poll.type == "quiz" and (
        update.message.chat.type != "private" or is_channel_job
    ):
        return await replies.send_quiz_unavailable_message(update)

    if is_channel_job:
        return await actions.add_new_channel_job(update=update, poll=True)

    reply_to_message = update.message.reply_to_message
    if reply_to_message is None:
        return

    if reply_to_message.text_html == replies.request_text_message:
        err = await actions.add_message(
            update=update, context=context, photo=False, poll=True
        )
        if err is None:
            teleapi.delete_message(update.message.chat.id, reply_to_message.message_id)


async def handle_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "1":
        await actions.reset_chat(update, context)
    await context.bot.editMessageReplyMarkup(
        chat_id=query.message.chat_id, message_id=query.message.message_id
    )
    await query.answer()
