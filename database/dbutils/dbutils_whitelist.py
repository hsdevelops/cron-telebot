import config
from common import log
from database.dbutils import dbutils
from typing import Tuple


async def get_user_limit(db_service, user_id) -> Tuple[int, int]:
    try:
        current_job_count = await dbutils.count_entries_by_userid(db_service, user_id)
    except Exception as e:
        current_job_count = 0
        log.logger.warning(
            f"[DB] get_user_limit count failed: {type(e).__name__} - {e}"
        )

    q = {"user_id": float(user_id), "removed_ts": ""}
    try:
        result = await db_service.find_one_whitelist(q)
    except Exception as e:
        log.logger.warning(
            f"[DB] get_user_limit whitelist lookup failed: {type(e).__name__} - {e}"
        )
        result = None

    if result is None:
        exceeded = current_job_count >= config.JOB_LIMIT_PER_PERSON
        return (exceeded, config.JOB_LIMIT_PER_PERSON)

    new_limit = result.get("new_limit", 0)
    return (current_job_count, new_limit)
