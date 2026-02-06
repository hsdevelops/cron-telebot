from database.dbutils.dbutils_empty import empty_update_result
from database.mongo import MongoService
from common import log
from typing import Dict, Any, Optional
from pymongo.results import UpdateResult
from pymongo.errors import PyMongoError

"""
Getters
"""


async def find_bot_by_token(db_service: MongoService, bot_token: str) -> Optional[Any]:
    q = {"token": bot_token}
    try:
        return await db_service.find_one_bot(q)
    except PyMongoError as e:
        log.logger.warning(f"[DB] find_bot_by_token failed: {type(e).__name__} - {e}")
        return None


"""
Setters
"""


async def upsert_new_bot(
    db_service: MongoService, user_id: int, bot_data: Dict[str, Any]
) -> UpdateResult:
    bot_id = bot_data.get("id")
    if bot_id is None:
        log.logger.warning("[DB] upsert_new_bot missing bot id")
        return empty_update_result()
    q = {"id": bot_id}
    payload = {**bot_data}
    try:
        res = await db_service.update_one_bot(q, payload)
        log.logger.info(
            f'[BOT] User "{user_id}" upserted bot "{bot_data.get("username")}"'
        )
        return res
    except PyMongoError as e:
        log.logger.warning(f"[DB] upsert_new_bot failed: {type(e).__name__} - {e}")
        return empty_update_result()
