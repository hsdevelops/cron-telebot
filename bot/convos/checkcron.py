from typing import Optional
from telegram.ext._contexttypes import ContextTypes
from bot.convos import convo
from bot import replies
from telegram import Update
from cron_descriptor import get_description
from telegram.ext import ConversationHandler


async def command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /checkcron is issued."""
    if update.message is None:
        return ConversationHandler.END

    await replies.text(
        update, replies.checkcron_message, reply_markup=replies.force_reply
    )
    return convo.states.s0


async def decrypt_cron(update: Update, _: ContextTypes) -> Optional[int]:
    if update.message is None:
        return ConversationHandler.END

    try:
        description = get_description(update.message.text).lower()
    except Exception:  # crontab is not valid
        await replies.text(
            update, replies.checkcron_invalid_message, reply_markup=replies.force_reply
        )
        return None  # stay in current state

    await replies.text(update, replies.checkcron_meaning_message + description)

    return ConversationHandler.END
