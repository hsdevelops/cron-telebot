from contextlib import asynccontextmanager
from fastapi import FastAPI
import config
from telegram.ext import Application
from typing import AsyncGenerator
from bot.handlers import bot_handlers, handle_error

from database import mongo

db_service = mongo.MongoService(config.MONGODB_CONNECTION_STRING)


async def setup_bot(application: Application):
    await ptb.bot.deleteWebhook(drop_pending_updates=False)
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
    .post_init(setup_bot)  # for polling
    .build()
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    app.state.mongo = db_service

    if config.BOTHOST is None:
        yield
        return

    await ptb.initialize()
    await setup_bot(ptb)
    await ptb.bot.setWebhook(config.BOTHOST)
    yield
    await ptb.shutdown()
    # TODO : close db
