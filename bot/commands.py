from telegram import Update
from telegram.ext._contexttypes import ContextTypes
from bot.convos import permissions
from bot import replies
from common.enums import Restriction
from database import mongo
from database.dbutils import dbutils


async def help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if update.message is None:
        return

    await replies.text(update, replies.help_message)


async def list_options(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /options is issued."""
    if update.message is None:
        return

    is_group = update.message.chat.type in ["group", "supergroup"]
    if is_group:
        await replies.text(update, replies.list_options_message_group)
        return

    await replies.text(update, replies.group_only_error_message)


async def option_restrict_to_admins(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /adminsonly is issued."""
    if update.message is None:
        return

    if update.message.chat.type not in ["group", "supergroup"]:
        return

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if not await permissions.check_rights(update, context, db_service, True):
        return

    return await restrict_to_admins(update, db_service)


async def restrict_to_admins(update: Update, db_service: mongo.MongoService) -> None:
    if update.message is None:
        return

    chat_id = update.message.chat.id

    entry = await dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    current_restriction = entry.get("restriction", "")

    if current_restriction == Restriction.ADMIN.value:
        await dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return await replies.text(update, replies.restrict_success_message % "everyone")

    if current_restriction == Restriction.OWNER.value:
        return await replies.text(
            update, replies.wrong_restrction_error_message % "the current bot user"
        )

    payload = {"restriction": Restriction.ADMIN.value}
    await dbutils.update_chat_entry(db_service, chat_id, payload)
    return await replies.text(
        update, replies.restrict_success_message % "only group admins"
    )


async def option_restrict_to_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /creatoronly is issued."""
    if update.message is None:
        return

    db_service: mongo.MongoService = context.application.bot_data["mongo"]

    if update.message.chat.type not in ["group", "supergroup"]:
        return

    rights = await permissions.check_rights(update, context, db_service)
    if not rights:
        return

    return await restrict_to_user(update, db_service)


async def restrict_to_user(update: Update, db_service: mongo.MongoService) -> None:
    if update.message is None:
        return

    # user running this command must be creator
    chat_id = update.message.chat.id
    entry = await dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    user_id = update.message.from_user.id
    if str(user_id) != str(entry.get("created_by", "")):
        await replies.text(
            update, replies.user_unauthorized_error_message % "the current bot user"
        )
        return

    current_restriction = entry.get("restriction", "")
    if current_restriction == Restriction.ADMIN.value:
        return await replies.text(
            update, replies.wrong_restrction_error_message % "group admins"
        )

    if current_restriction == Restriction.OWNER.value:
        await dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return await replies.text(update, replies.restrict_success_message % "everyone")

    await dbutils.update_chat_entry(
        db_service, chat_id, {"restriction": Restriction.OWNER.value}
    )
    return await replies.text(update, replies.restrict_success_message % "only you")
