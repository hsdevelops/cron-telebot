from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    Dispatcher,
    CallbackQueryHandler,
    ConversationHandler,
)
from telegram import Update, Bot
from bot.convos import edit
import config
from common.log import logger
from flask import request, Response
from api import app
from bot import handlers, commands


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def prepare_dispatcher(dp):
    # conversations (must be declared first, not sure why)
    convo_text_filter = Filters.text & ~Filters.command
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("edit", commands.edit_job)],
            states={
                edit.state0: [MessageHandler(convo_text_filter, edit.choose_job)],
                edit.state1: [MessageHandler(convo_text_filter, edit.choose_attribute)],
                edit.state2: [
                    MessageHandler(convo_text_filter, edit.handle_edit_content),
                    MessageHandler(Filters.poll, edit.handle_edit_poll),
                ],
                edit.state3: [MessageHandler(Filters.photo, edit.handle_add_photo)],
                edit.state4: [
                    MessageHandler(convo_text_filter, edit.handle_clear_photos)
                ],
            },
            fallbacks=[MessageHandler(Filters.command, edit.end_convo)],
        )
    )

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
    dp.add_handler(MessageHandler(Filters.text, handlers.handle_messages))
    dp.add_handler(MessageHandler(Filters.photo, handlers.handle_photos))
    dp.add_handler(MessageHandler(Filters.poll, handlers.handle_polls))

    # on callback
    dp.add_handler(CallbackQueryHandler(handlers.handle_callback))

    # log all errors
    dp.add_error_handler(error)


# Use webhook when running in prod (via gunicorn)
if config.ENV:
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    bot.setWebhook(config.BOTHOST)
    dp = Dispatcher(bot=bot, update_queue=None)
    prepare_dispatcher(dp)

    @app.get("/")
    def home():
        return "Hello world!"

    @app.post("/")
    def process_update():
        dp.process_update(Update.de_json(request.get_json(force=True), bot))
        return Response(status=200)


# Use polling when running locally
if __name__ == "__main__":
    updater = Updater(config.TELEGRAM_BOT_TOKEN, use_context=True)
    updater.stop()
    updater.is_idle = False

    dp = updater.dispatcher
    prepare_dispatcher(dp)
    updater.start_polling()
    updater.idle()

    # Used for testing webhook locally, instructions for how to set up local webhook at https://dev.to/ibrarturi/how-to-test-webhooks-on-your-localhost-3b4f
    # app.run(debug=True)
