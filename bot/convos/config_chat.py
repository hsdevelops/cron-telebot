from teleapi.endpoints import get_bot_details
from telegram.ext import ConversationHandler
from bot.replies import replies
from database import mongo
from database.dbutils import dbutils
from common import log
import teleapi.endpoints as teleapi


state0, state1 = range(2)

# state 0
def choose_chat(update, context):
    db_service = mongo.MongoService(update)
    chat_title = str(update.message.text)
    user_id = update.message.from_user.id
    chat_entry = dbutils.find_chat_by_title(db_service, user_id, chat_title)

    if chat_entry is None:
        replies.send_error_message(update)
        return state0

    prev_token = chat_entry.get("user_bot_token")
    if prev_token is None:
        context.user_data["chat_id"] = chat_entry["chat_id"]
        context.user_data["chat_title"] = chat_entry["chat_title"]
        replies.send_prompt_user_bot_message(update)
        return state1

    # Revert back to default — both chat and jobs
    has_err = reset_sender(db_service, chat_entry["chat_id"], user_id, None, prev_token)
    if has_err:
        replies.send_missing_bot_in_group_message(update)
        return ConversationHandler.END
    replies.send_sender_reset_success_message(update)
    return ConversationHandler.END


# state 1
def update_sender(update, context):
    new_token = str(update.message.text)
    user_id = update.message.from_user.id

    # check if bot exists
    resp = get_bot_details(new_token)
    if resp.status_code != 200:
        replies.send_error_message(update)
        return state1

    db_service = mongo.MongoService(update)
    bot_data = {"token": new_token, **resp.json()["result"]}
    dbutils.upsert_new_bot(db_service, user_id, bot_data)

    chat_id, chat_title = context.user_data["chat_id"], context.user_data["chat_title"]
    has_err = reset_sender(db_service, chat_id, user_id, new_token, None)
    if has_err:
        replies.send_missing_bot_in_group_message(update)
        return ConversationHandler.END

    replies.send_sender_change_success_message(update, chat_title, bot_data["username"])
    return ConversationHandler.END


def reset_sender(db_service, chat_id, user_id, new_token, prev_token=None):
    # special case — single photos can only be sent from the same bot
    single_photo_entries = dbutils.find_entries_by_content_type(db_service, chat_id)
    for entry in single_photo_entries:
        resp, new_photo_id = teleapi.transfer_photo_between_bots(
            db_service, new_token, prev_token, chat_id, entry
        )
        if resp.status_code != 200:
            return True
        log.log_photo_transferred(user_id, new_photo_id, chat_id, resp.status_code)

    # jobs
    q = {"$or": [{"chat_id": chat_id}, {"channel_id": chat_id}]}
    payload = {"last_updated_by": user_id, "user_bot_token": new_token}
    db_service.update_multiple_entries(q, payload)

    # chat
    field = "user_bot_token"
    payload = {"user_bot_token": new_token}
    dbutils.update_chat_entry(db_service, chat_id, payload, updated_field=field)

    log.log_sender_updated(user_id, prev_token, new_token, chat_id)
    return False
