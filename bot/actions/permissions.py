from bot.replies import replies
from common.enums import Restriction
from database import mongo
from database.dbutils import dbutils


def restrict_to_admins(update, db_service):
    chat_id = update.message.chat.id

    db_service = mongo.MongoService(update)
    entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    current_restriction = entry.get("restriction", "")

    if current_restriction == Restriction.ADMIN.value:
        dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return replies.send_restrict_success_message(update, "everyone")

    if current_restriction == Restriction.OWNER.value:
        return replies.send_wrong_restriction_message(update, "the current bot user")

    payload = {"restriction": Restriction.ADMIN.value}
    dbutils.update_chat_entry(db_service, chat_id, payload)
    return replies.send_restrict_success_message(update, "only group admins")


def check_rights(update, context, db_service, must_be_admin=False):
    message = update.callback_query if update.message is None else update.message
    user_id = message.from_user.id
    group_id = get_chat_id(update, context)

    entry = dbutils.find_chat_by_chatid(db_service, group_id)
    if entry is None:
        return replies.send_start_message(update)

    current_restriction = entry.get("restriction")
    is_creator = str(user_id) == str(entry.get("created_by", ""))
    if current_restriction == Restriction.OWNER.value and not is_creator:
        replies.send_user_unauthorized_error_message(update, "the current bot user")
        return False

    admin_roles = [Restriction.ADMIN.value, Restriction.OWNER.value]
    is_admin = context.bot.get_chat_member(group_id, user_id).status in admin_roles
    must_be_admin = must_be_admin or current_restriction == Restriction.ADMIN.value
    if must_be_admin and not is_admin:
        replies.send_user_unauthorized_error_message(update, "group admins")
        return False

    return True


def restrict_to_user(update, db_service):
    # user running this command must be creator
    chat_id = update.message.chat.id
    entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    if entry is None:
        return

    user_id = update.message.from_user.id
    if str(user_id) != str(entry.get("created_by", "")):
        replies.send_user_unauthorized_error_message(update, "the current bot user")
        return

    current_restriction = entry.get("restriction", "")
    if current_restriction == Restriction.ADMIN.value:
        return replies.send_wrong_restriction_message(update, "group admins")

    if current_restriction == Restriction.OWNER.value:
        dbutils.update_chat_entry(db_service, chat_id, {"restriction": ""})
        return replies.send_restrict_success_message(update, "everyone")

    dbutils.update_chat_entry(
        db_service, chat_id, {"restriction": Restriction.OWNER.value}
    )
    return replies.send_restrict_success_message(update, "only you")


def get_chat_id(update, context):
    chat_id = -1
    if update.message is not None:  # text message
        return update.message.chat.id
    elif update.callback_query is not None:  # callback message
        return update.callback_query.message.chat.id
    elif update.poll is not None:  # answer in Poll
        return context.bot_data[update.poll.id]
    return chat_id
