import config
from database.dbutils import dbutils
from typing import Tuple


def get_user_limit(db_service, user_id) -> Tuple[int, int]:
    current_job_count = dbutils.count_entries_by_userid(db_service, user_id)

    q = {"user_id": float(user_id), "removed_ts": ""}
    result = db_service.find_one_whitelist(q)

    if result is None:
        exceeded = current_job_count >= config.JOB_LIMIT_PER_PERSON
        return (exceeded, config.JOB_LIMIT_PER_PERSON)

    new_limit = result.get("new_limit", 0)
    return (current_job_count, new_limit)
