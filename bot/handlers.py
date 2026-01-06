from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot import replies
from common import log
from bot import commands

from telegram.ext import (
    filters,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
)
from bot.convos import (
    add,
    addforwarded,
    addmultiple,
    changesender,
    changetz,
    checkcron,
    convo,
    delete,
    edit,
    list,
    reset,
    start,
)


text = filters.TEXT & ~filters.COMMAND


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    log.logger.error(f'[BOT] Update "{update}" caused error "{context.error}"')


async def fallback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await replies.text(update, replies.convo_ended_message)
    return ConversationHandler.END


bot_handlers = [
    # conversations
    ConversationHandler(
        entry_points=[CommandHandler("add", add.command)],
        states={
            convo.states.s0: [MessageHandler(text, add.add_jobname)],
            convo.states.s1: [
                MessageHandler(text, add.add_content),
                MessageHandler(filters.PHOTO, add.add_content),
                MessageHandler(filters.POLL, add.add_content),
            ],
            convo.states.s2: [
                MessageHandler(text, add.add_crontab),
                MessageHandler(filters.PHOTO, add.add_photo_group),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("addmultiple", addmultiple.command)],
        states={
            convo.states.s0: [
                MessageHandler(text, addmultiple.add_jobs),
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("start", start.command)],
        states={
            convo.states.s0: [MessageHandler(text, start.add_timezone)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("edit", edit.command)],
        states={
            convo.states.s0: [MessageHandler(text, edit.choose_job)],
            convo.states.s1: [MessageHandler(text, edit.choose_attribute)],
            convo.states.s2: [
                MessageHandler(text, edit.handle_edit_content),
                MessageHandler(filters.POLL, edit.handle_edit_poll),
            ],
            convo.states.s3: [MessageHandler(filters.PHOTO, edit.handle_add_photo)],
            convo.states.s4: [MessageHandler(text, edit.handle_clear_photos)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("changesender", changesender.command)],
        states={
            convo.states.s0: [MessageHandler(text, changesender.choose_chat)],
            convo.states.s1: [MessageHandler(text, changesender.update_sender)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("delete", delete.command)],
        states={
            convo.states.s0: [
                MessageHandler(text, delete.remove_job),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("list", list.command)],
        states={
            convo.states.s0: [
                MessageHandler(text, list.show_job_details),
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("checkcron", checkcron.command)],
        states={
            convo.states.s0: [
                MessageHandler(text, checkcron.decrypt_cron),
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("changetz", changetz.command)],
        states={
            convo.states.s0: [
                MessageHandler(text, changetz.update_timezone),
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    ConversationHandler(
        entry_points=[CommandHandler("reset", reset.command)],
        states={
            convo.states.s0: [CallbackQueryHandler(reset.reset)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    # this conversation handler must be placed last, otherwise it will conflict with the rest
    ConversationHandler(
        entry_points=[
            MessageHandler(text, addforwarded.add_job),
            MessageHandler(filters.PHOTO, addforwarded.add_job),
            MessageHandler(filters.POLL, addforwarded.add_job),
        ],
        states={
            convo.states.s0: [
                MessageHandler(text, add.add_crontab),
                MessageHandler(filters.PHOTO, add.add_photo_group),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fallback)],
    ),
    # on different commands - answer in Telegram
    CommandHandler("help", commands.help),
    CommandHandler(
        "options", commands.list_options
    ),  # TODO - make these three a convo too
    CommandHandler("adminsonly", commands.option_restrict_to_admins),
    CommandHandler("creatoronly", commands.option_restrict_to_user),
    # on noncommand i.e message
]
