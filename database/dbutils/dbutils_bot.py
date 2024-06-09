from database.mongo import MongoService
from common import log
from typing import Dict, Any, Optional

"""
Getters
"""


def find_bot_by_token(db_service: MongoService, bot_token: str) -> Optional[Any]:
    q = {"token": bot_token}
    return db_service.find_one_bot(q)


"""
Setters
"""


def upsert_new_bot(
    db_service: MongoService, user_id: int, bot_data: Dict[str, Any]
) -> None:
    q = {"id": bot_data["id"]}
    payload = {**bot_data}
    db_service.update_one_bot(q, payload)
    log.log_bot_updated(user_id, bot_data)
