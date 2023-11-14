import asyncio
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    Application,
    CallbackQueryHandler,
)
from telegram.ext._contexttypes import ContextTypes
from telegram import Update
from bot.convos import handlers as convo_handlers
import config
from common.log import logger
from flask import request, Response
from api import app
from bot import handlers, commands


async def error(update, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def prepare_application(dp):
    # conversations (must be declared first, not sure why)
    dp.add_handler(convo_handlers.edit_handler)
    dp.add_handler(convo_handlers.config_chat_handler)

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", commands.start))
    dp.add_handler(CommandHandler("help", commands.help))
    dp.add_handler(CommandHandler("add", commands.add))
    dp.add_handler(CommandHandler("delete", commands.delete))
    dp.add_handler(CommandHandler("list", commands.list_jobs))
    dp.add_handler(CommandHandler("checkcron", commands.checkcron))
    dp.add_handler(CommandHandler("options", commands.list_options))
    dp.add_handler(CommandHandler("adminsonly", commands.option_restrict_to_admins))
    dp.add_handler(CommandHandler("creatoronly", commands.option_restrict_to_user))
    dp.add_handler(CommandHandler("changetz", commands.change_tz))
    dp.add_handler(CommandHandler("reset", commands.reset))
    dp.add_handler(CommandHandler("addmultiple", commands.add_multiple))

    # on noncommand i.e message
    dp.add_handler(MessageHandler(filters.TEXT, handlers.handle_messages))
    dp.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photos))
    dp.add_handler(MessageHandler(filters.POLL, handlers.handle_polls))

    # on callback
    dp.add_handler(CallbackQueryHandler(handlers.handle_callback))

    # log all errors
    dp.add_error_handler(error)


# Use webhook when running in prod (via gunicorn)
if config.ENV:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    asyncio.run(application.bot.setWebhook(config.BOTHOST))

    @app.get("/")
    def home():
        return "Hello world!"

    @app.post("/")
    async def process_update():
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        prepare_application(application)
        async with application:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
            return Response(status=200)


# Use polling when running locally
if __name__ == "__main__":
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    prepare_application(application)
    application.run_polling()

    # Used for testing webhook locally, instructions for how to set up local webhook at https://dev.to/ibrarturi/how-to-test-webhooks-on-your-localhost-3b4f
    # app.run(debug=True)
