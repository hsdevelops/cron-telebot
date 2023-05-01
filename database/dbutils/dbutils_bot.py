from database.mongo import MongoService
from common import log

"""
Getters
"""


def find_bot_by_token(db_service: MongoService, bot_token):
    q = {"token": bot_token}
    return db_service.find_one_bot(q)


"""
Setters
"""


def upsert_new_bot(db_service: MongoService, user_id, bot_data):
    q = {"id": bot_data["id"]}
    payload = {**bot_data}
    db_service.update_one_bot(q, payload)
    log.log_bot_updated(user_id, bot_data)
