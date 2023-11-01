from database import mongo
from database.dbutils import dbutils
from common import log, utils
import os

# https://github.com/telegraf/telegraf/discussions/1833

start_ts = "2023-10-30"
end_ts = "2023-11-01"

mongo_conn = os.getenv("PROD_MONGODB_CONNECTION_STRING")
db_service = mongo.MongoService(None, mongo_conn)

entries = dbutils.find_entries_removed_between(db_service, start_ts, end_ts, 400)

entry_count = len(entries)
log.log_update_count(entry_count)

for entry in entries:
    chat_id = entry["chat_id"]
    crontab = entry["crontab"]
    entry_id = entry["_id"]
    chat_entry = dbutils.find_chat_by_chatid(db_service, chat_id)
    user_tz_offset = chat_entry.get("tz_offset")
    user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)
    payload = {
        "nextrun_ts": db_nextrun_ts,
        "user_nextrun_ts": user_nextrun_ts,
        "remarks": "",
        "removed_ts": "",
    }
    res = dbutils.update_entry_by_jobid(
        db_service, entry_id, payload, include_removed=True
    )
    log.log_entry_updated(entry)
    log.log_update_details(res)
