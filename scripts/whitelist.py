from pymongo import MongoClient
import config
import certifi
from common import utils
from config import TZ_OFFSET
from datetime import datetime, timedelta, timezone


"""
Configuration
"""
USERNAME = ""
NEW_LIMIT = 0
ACTION = "add"  # remove


client = MongoClient(config.MONGODB_CONNECTION_STRING, tlsCAFile=certifi.where())
db = client[config.MONGODB_DB]

whitelist_collection = db[config.MONGODB_USER_WHITELIST_COLLECTION]
user_collection = db[config.MONGODB_USER_DATA_COLLECTION]

user_id = user_collection.find_one({"username": USERNAME, "superseded_at": ""}).get(
    "user_id"
)

now = utils.parse_time_millis(datetime.now(timezone(timedelta(hours=TZ_OFFSET))))

if ACTION == "add":
    whitelist_collection.replace_one(
        {"user_id": user_id, "removed_ts": ""},
        {
            "user_id": user_id,
            "username": USERNAME,
            "new_limit": NEW_LIMIT,
            "created_ts": now,
            "removed_ts": "",
        },
        upsert=True,
    )
else:
    whitelist_collection.update_one(
        {"user_id": user_id, "removed_ts": ""}, {"$set": {"removed_ts": now}}
    )
