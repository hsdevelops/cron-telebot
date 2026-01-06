import config
from common import utils
from typing import Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import UpdateResult, InsertOneResult


class MongoService:
    def __init__(self, conn_str=config.MONGODB_CONNECTION_STRING) -> None:
        # Provide the mongodb atlas url to connect python to mongodb using pymongo

        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
        self.client = AsyncIOMotorClient(conn_str)
        self.db = self.client[config.MONGODB_DB]
        self.main_collection = self.db[config.MONGODB_JOB_DATA_COLLECTION]
        self.chat_data_collection = self.db[config.MONGODB_CHAT_DATA_COLLECTION]
        self.user_data_collection = self.db[config.MONGODB_USER_DATA_COLLECTION]
        self.bot_data_collection = self.db[config.MONGODB_BOT_DATA_COLLECTION]
        self.user_whitelist_collection = self.db[
            config.MONGODB_USER_WHITELIST_COLLECTION
        ]

    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        db = getattr(self, "db")
        return getattr(db, collection_name)

    def disconnect(self) -> AsyncIOMotorCollection:
        self.client.close()

    async def insert_new_entry(self, q: Optional[Any]) -> InsertOneResult:
        now = utils.now()
        q["created_ts"] = now
        q["last_update_ts"] = now
        return await self.main_collection.insert_one(q)

    async def find_entries(
        self, q: Optional[Any], sort: Optional[Any] = None
    ) -> List[Optional[Any]]:
        cursor = self.main_collection.find(q)
        if sort is not None:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=None)

    async def find_one_entry(self, q: Optional[Any]) -> Optional[Any]:
        return await self.main_collection.find_one(q)

    async def update_multiple_entries(
        self, q: Optional[Any], update: Optional[Any]
    ) -> UpdateResult:
        q["removed_ts"] = ""
        update["last_update_ts"] = utils.now()
        return await self.main_collection.update_many(q, {"$set": update})

    async def update_entry(
        self, q: Optional[Any], update: Optional[Any]
    ) -> UpdateResult:
        update["last_update_ts"] = utils.now()
        return await self.main_collection.update_one(q, {"$set": update})

    async def count_entries(self, q: Optional[Any]) -> int:
        return await self.main_collection.count_documents(q)

    async def insert_new_chat(self, q: Optional[Any]) -> InsertOneResult:
        q["updated_ts"] = utils.now()
        return await self.chat_data_collection.insert_one(q)

    async def find_one_chat_entry(self, q: Optional[Any]) -> Optional[Any]:
        return await self.chat_data_collection.find_one(q)

    async def find_chat_entries(self, q: Optional[Any]) -> Optional[Any]:
        cursor = self.chat_data_collection.find(q)
        return await cursor.to_list(length=None)

    async def update_chat_entries(
        self, q: Optional[Any], update: Optional[Any]
    ) -> UpdateResult:
        update["updated_ts"] = utils.now()
        return await self.chat_data_collection.update_many(q, {"$set": update})

    async def update_one_chat_entry(
        self, q: Optional[Any], update: Optional[Any]
    ) -> UpdateResult:
        update["updated_ts"] = utils.now()
        return await self.chat_data_collection.update_one(q, {"$set": update})

    async def insert_new_user(self, q: Optional[Any]) -> Optional[Any]:
        now = utils.now()
        q["created_at"] = now
        q["last_used_at"] = now
        return await self.user_data_collection.insert_one(q)

    async def find_one_user(self, q: Optional[Any]) -> Optional[Any]:
        return await self.user_data_collection.find_one(q)

    async def update_one_user(
        self, q: Optional[Any], update: Optional[Any]
    ) -> Optional[Any]:
        return await self.user_data_collection.update_one(q, {"$set": update})

    async def update_one_bot(
        self, q: Optional[Any], update: Optional[Any]
    ) -> Optional[Any]:
        update["updated_at"] = utils.now()
        return await self.bot_data_collection.update_one(
            q, {"$set": update}, upsert=True
        )

    async def find_one_bot(self, q: Optional[Any]) -> Optional[Any]:
        return await self.bot_data_collection.find_one(q)

    async def find_one_whitelist(self, q: Optional[Any]) -> Optional[Any]:
        return await self.user_whitelist_collection.find_one(q)
