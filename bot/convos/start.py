from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot.convos import convo
from bot import replies
from common import utils
from database import mongo
from database.dbutils import dbutils
from telegram.ext import ConversationHandler

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    chat_entry = await dbutils.find_chat_by_chatid(db_service, update.message.chat.id)
    if chat_entry is not None:
        await replies.text(update, replies.simple_prompt_message)
        return ConversationHandler.END

    await replies.text(update, replies.start_message, reply_markup=replies.force_reply)
    return convo.states.s0


async def add_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    # check validity
    tz_values = utils.extract_tz_values(update.message.text)
    if not tz_values:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    utc_tz, tz_offset = utils.calc_tz(tz_values)
    if tz_offset < -12 or tz_offset > 14:
        await replies.text(update, replies.error_message)
        return ConversationHandler.END

    chat_exists = await dbutils.chat_exists(db_service, update.message.chat.id)
    if not chat_exists:
        res = await dbutils.add_chat_data(
            db_service,
            chat_id=update.message.chat.id,
            chat_title=update.message.chat.title,
            chat_type=update.message.chat.type,
            tz_offset=tz_offset,
            utc_tz=utc_tz,
            created_by=update.message.from_user.id,
            telegram_ts=update.message.date,
        )
        if res is None:
            await replies.text(update, replies.start_error_message)
            return ConversationHandler.END

    await replies.text(update, replies.help_message)
    return ConversationHandler.END
