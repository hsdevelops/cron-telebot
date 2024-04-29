import config
from common import utils
from pymongo import MongoClient
from database.dbutils.dbutils_user import sync_user_data
from typing import Any, List, Optional
from telegram import Update
from database.consts import QUERY_TYPE, COLLECTION_TYPE


class MongoService:
    def __init__(self, update: Optional[Update] = None, conn_str: Optional[str] = config.MONGODB_CONNECTION_STRING) -> None:
        # Provide the mongodb atlas url to connect python to mongodb using pymongo

        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
        client = MongoClient(conn_str)
        db = client[config.MONGODB_DB]
        self.main_collection = db[config.MONGODB_JOB_DATA_COLLECTION]
        self.chat_data_collection = db[config.MONGODB_CHAT_DATA_COLLECTION]
        self.user_data_collection = db[config.MONGODB_USER_DATA_COLLECTION]
        self.bot_data_collection = db[config.MONGODB_BOT_DATA_COLLECTION]
        self.user_whitelist_collection = db[config.MONGODB_USER_WHITELIST_COLLECTION]

        if update is not None:
            sync_user_data(self, update)

    def insert_new_entry(self, q: QUERY_TYPE) -> None:
        now = utils.now()
        q["created_ts"] = now
        q["last_update_ts"] = now
        self.main_collection.insert_one(q)

    def find_entries(self, q: QUERY_TYPE, sort: Optional[Any] = None) -> List[COLLECTION_TYPE]:
        res = self.main_collection.find(q)
        if sort is not None:
            res = res.sort(sort)
        return list(res)

    def find_one_entry(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.main_collection.find_one(q)

    def update_multiple_entries(self, q: QUERY_TYPE, update: QUERY_TYPE) -> COLLECTION_TYPE:
        q["removed_ts"] = ""
        update["last_update_ts"] = utils.now()
        return self.main_collection.update_many(q, {"$set": update})

    def update_entry(self, q: QUERY_TYPE, update: QUERY_TYPE) -> Any:
        update["last_update_ts"] = utils.now()
        return self.main_collection.update_one(q, {"$set": update})

    def count_entries(self, q: QUERY_TYPE) -> int:
        return self.main_collection.count_documents(q)

    def insert_new_chat(self, q: QUERY_TYPE) -> None:
        q["updated_ts"] = utils.now()
        self.chat_data_collection.insert_one(q)

    def find_one_chat_entry(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.chat_data_collection.find_one(q)

    def find_chat_entries(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return list(self.chat_data_collection.find(q))

    def update_chat_entries(self, q: QUERY_TYPE, update: QUERY_TYPE) -> COLLECTION_TYPE:
        update["updated_ts"] = utils.now()
        return self.chat_data_collection.update_many(q, {"$set": update})

    def update_one_chat_entry(self, q: QUERY_TYPE, update: QUERY_TYPE) -> None:
        update["updated_ts"] = utils.now()
        self.chat_data_collection.update_one(q, {"$set": update})

    def insert_new_user(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        now = utils.now()
        q["created_at"] = now
        q["last_used_at"] = now
        return self.user_data_collection.insert_one(q)

    def find_one_user(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.user_data_collection.find_one(q)

    def update_one_user(self, q: QUERY_TYPE, update: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.user_data_collection.update_one(q, {"$set": update})

    def update_one_bot(self, q: QUERY_TYPE, update: QUERY_TYPE) -> COLLECTION_TYPE:
        update["updated_at"] = utils.now()
        return self.bot_data_collection.update_one(q, {"$set": update}, upsert=True)

    def find_one_bot(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.bot_data_collection.find_one(q)

    def find_one_whitelist(self, q: QUERY_TYPE) -> COLLECTION_TYPE:
        return self.user_whitelist_collection.find_one(q)
