from database.mongo import MongoService
from common import log
from typing import Dict, Any, Optional

"""
Getters
"""


async def find_bot_by_token(db_service: MongoService, bot_token: str) -> Optional[Any]:
    q = {"token": bot_token}
    return await db_service.find_one_bot(q)


"""
Setters
"""


async def upsert_new_bot(
    db_service: MongoService, user_id: int, bot_data: Dict[str, Any]
) -> None:
    q = {"id": bot_data["id"]}
    payload = {**bot_data}
    await db_service.update_one_bot(q, payload)
    log.logger.info(f'[BOT] User "{user_id}" upserted bot "{bot_data.get("username")}"')
