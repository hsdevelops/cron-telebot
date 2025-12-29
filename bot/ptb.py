from contextlib import asynccontextmanager
from fastapi import FastAPI
import config
from telegram.ext import Application
from typing import AsyncGenerator
from bot.handlers import bot_handlers, handle_error

from database import mongo

db_service = mongo.MongoService(config.MONGODB_CONNECTION_STRING)


async def setup_bot(application: Application):
    application.bot_data["mongo"] = db_service

    # add handlers
    application.add_error_handler(handle_error)
    for h in bot_handlers:
        application.add_handler(h)


# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Handling-network-errors
ptb = (
    Application.builder()
    .token(config.TELEGRAM_BOT_TOKEN)
    .read_timeout(7)
    .get_updates_read_timeout(42)
)

ptb_builder = ptb.post_init(setup_bot)
ptb = ptb_builder.build()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    app.state.mongo = db_service

    if config.BOTHOST is None:
        yield
        return

    await ptb.initialize()
    await ptb.bot.deleteWebhook(drop_pending_updates=True)
    await ptb.bot.setWebhook(config.BOTHOST)
    await ptb.start()
    yield
    await ptb.stop()
    await ptb.shutdown()
    # TODO : close db
