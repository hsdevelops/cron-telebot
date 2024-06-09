from contextlib import asynccontextmanager
from fastapi import FastAPI
import config
from telegram.ext import Application
from typing import AsyncGenerator

# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Handling-network-errors
ptb = (
    Application.builder()
    .token(config.TELEGRAM_BOT_TOKEN)
    .read_timeout(7)
    .get_updates_read_timeout(42)
)
if config.ENV:
    ptb = ptb.updater(None)
ptb = ptb.build()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    if config.BOTHOST:
        await ptb.bot.setWebhook(config.BOTHOST)
    async with ptb:
        await ptb.start()
        yield
        await ptb.stop()
