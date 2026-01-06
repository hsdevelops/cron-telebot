from contextlib import asynccontextmanager
import aiohttp
from fastapi import FastAPI
from influxdb_client_3 import InfluxDBClient3
import config
from telegram.ext import Application
from typing import AsyncGenerator
from bot.handlers import bot_handlers, handle_error

from database import mongo


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    db_service = mongo.MongoService(config.MONGODB_CONNECTION_STRING)
    app.state.mongo = db_service

    http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    app.state.http_session = http_session

    app.state.influx = InfluxDBClient3(
        host=config.INFLUXDB_HOST,
        token=config.INFLUXDB_TOKEN,
        org=config.INFLUXDB_ORG,
        database=config.INFLUXDB_BUCKET,
    )

    # https://github.com/python-telegram-bot/python-telegram-bot/wiki/Handling-network-errors
    ptb = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .read_timeout(7)
        .get_updates_read_timeout(42)
        .build()
    )
    app.state.ptb = ptb

    await ptb.initialize()

    await ptb.bot.deleteWebhook(drop_pending_updates=False)
    ptb.bot_data["mongo"] = db_service
    ptb.bot_data["http_session"] = http_session

    # add handlers
    ptb.add_error_handler(handle_error)
    for h in bot_handlers:
        ptb.add_handler(h)

    # polling
    if config.BOTHOST is None:
        try:
            await ptb.start()
            await ptb.updater.start_polling(drop_pending_updates=False)
            yield
        finally:
            await ptb.updater.stop()
            await ptb.stop()
            await ptb.shutdown()
            await http_session.close()
            db_service.disconnect()
        return

    # webhook
    try:
        await ptb.bot.setWebhook(config.BOTHOST)
        yield
    finally:
        await ptb.shutdown()
        await http_session.close()
        db_service.disconnect()
        app.state.influx.close()
