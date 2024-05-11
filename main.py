from http import HTTPStatus
from fastapi import Request, Response
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from telegram.ext._contexttypes import ContextTypes
from telegram import Update
import uvicorn
from bot.ptb import ptb
from api import app
from bot import handlers, commands
import config
from bot.convos import handlers as convo_handlers
from common.log import logger
from telegram.ext import Application, ExtBot, JobQueue
from typing import Dict, Any


async def error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def add_handlers(
    dp: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        Dict[Any, Any],
        Dict[Any, Any],
        Dict[Any, Any],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ]
) -> None:
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


add_handlers(ptb)

# Use webhook when running in prod (via gunicorn)
if config.ENV:

    @app.post("/")
    async def process_update(request: Request):
        req = await request.json()
        update = Update.de_json(req, ptb.bot)
        await ptb.process_update(update)
        return Response(status_code=HTTPStatus.OK)


# Use polling when running locally
if __name__ == "__main__":
    if not config.ENV:
        ptb.run_polling()
    else:
        # Used for testing webhook locally, instructions for how to set up local webhook at https://dev.to/ibrarturi/how-to-test-webhooks-on-your-localhost-3b4f
        uvicorn.run(app, host="0.0.0.0", port=8000)
