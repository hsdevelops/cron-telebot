import config
from common import log, utils
from pymongo import MongoClient, ASCENDING, DESCENDING

# define service
class MongoService:
    def __init__(self, update=None):
        # Provide the mongodb atlas url to connect python to mongodb using pymongo

        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
        client = MongoClient(config.MONGODB_CONNECTION_STRING)
        db = client[config.MONGODB_DB]
        self.main_collection = db[config.MONGODB_JOB_DATA_COLLECTION]
        self.chat_data_collection = db[config.MONGODB_CHAT_DATA_COLLECTION]
        self.user_data_collection = db[config.MONGODB_USER_DATA_COLLECTION]
        self.user_whitelist_collection = db[config.MONGODB_USER_WHITELIST_COLLECTION]

        if update is not None:
            self.sync_user_data(update)

    def add_new_entry(
        self,
        chat_id,
        jobname,  # must have jobname for /delete
        user_id,
        channel_id="",
        crontab="",
        content="",
        content_type="",
        photo_id="",
        photo_group_id="",
        nextrun_ts="",
        user_nextrun_ts="",
    ):
        now = utils.now()
        self.main_collection.insert_one(
            {
                "created_ts": now,
                "last_update_ts": now,
                "created_by": user_id,
                "last_updated_by": user_id,
                "chat_id": chat_id,
                "channel_id": channel_id,
                "jobname": jobname,
                "crontab": crontab,
                "content": content,
                "content_type": content_type,
                "photo_id": photo_id,
                "photo_group_id": photo_group_id,
                "previous_message_id": "",
                "option_delete_previous": "",
                "nextrun_ts": nextrun_ts,
                "user_nextrun_ts": user_nextrun_ts,
                "removed_ts": "",
                "remarks": "",
            }
        )

        log.log_new_entry(jobname, chat_id)

    def retrieve_latest_entry(self, chat_id):
        result = list(
            self.main_collection.find(
                {"chat_id": float(chat_id), "removed_ts": ""}
            ).sort([("created_ts", DESCENDING)])
        )
        if len(result) <= 0:
            return None
        return result[0]

    def update_multiple_entries(self, filter, update):
        filter["removed_ts"] = ""
        update["last_update_ts"] = utils.now()
        return self.main_collection.update_many(filter, {"$set": update})

    def remove_entries_by_chat(self, chat_id):
        self.update_multiple_entries(
            {"chat_id": float(chat_id)}, {"removed_ts": utils.now()}
        )

    def update_entry(self, filter, update):
        filter["removed_ts"] = ""
        update["last_update_ts"] = utils.now()
        return self.main_collection.update_one(filter, {"$set": update})

    def get_one_entry(self, chat_id, jobname, include_removed=False):
        filter = {"chat_id": float(chat_id), "jobname": jobname}
        if not include_removed:
            filter["removed_ts"] = ""
        return self.main_collection.find_one(filter)

    def check_exists(self, chat_id, jobname):
        return self.get_one_entry(chat_id, jobname) is not None

    def get_entries_by_nextrun(self, ts):
        base_q = {"nextrun_ts": {"$lte": ts}, "removed_ts": "", "crontab": {"$ne": ""}}
        q = {
            "$or": [
                {"paused_ts": "", **base_q},
                {"paused_ts": {"$exists": False}, **base_q},
            ]
        }
        return list(self.main_collection.find(q).sort([("created_at", ASCENDING)]))

    def get_entries_by_chatid(self, chat_id):
        q = {
            "chat_id": float(chat_id),
            "removed_ts": "",
        }
        return list(self.main_collection.find(q))

    def count_entries_by_userid(self, user_id):
        q = {
            "created_by": user_id,
            "removed_ts": "",
        }
        return self.main_collection.count_documents(q)

    def retrieve_tz(self, chat_id):
        entry = self.get_chat_entry(chat_id)
        if entry is None:
            return None
        return float(entry.get("tz_offset", ""))

    def get_chat_entry(self, chat_id):
        return self.chat_data_collection.find_one({"chat_id": float(chat_id)})

    def update_chats_tz_by_type(self, user_id, tz_offset, utc_tz, chat_type):
        update = {
            "tz_offset": tz_offset,
            "utc_tz": "" if chat_type == "channel" else utc_tz,
            "updated_ts": utils.now(),
        }
        mongo_response = self.chat_data_collection.update_many(
            {"created_by": user_id, "chat_type": chat_type},
            {"$set": update},
        )
        modified_count = mongo_response.modified_count
        log.log_chats_tz_updated_by_type(modified_count, user_id, chat_type, tz_offset)

    def update_chat_entry(self, chat_id, update, updated_field="restriction"):
        q = {"chat_id": chat_id}
        self.chat_data_collection.update_one(q, {"$set": update})
        log.log_chat_entry_updated(chat_id, updated_field, update[updated_field])

    def check_chat_exists(self, chat_id):
        return self.get_chat_entry(chat_id) is not None

    def add_chat_data(
        self,
        chat_id,
        chat_title,
        chat_type,
        tz_offset,
        utc_tz,
        created_by,
        telegram_ts,
    ):
        new_doc = {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "chat_type": chat_type,
            "tz_offset": tz_offset,
            "utc_tz": utc_tz,
            "created_by": created_by,
            "telegram_ts": utils.parse_time_millis(telegram_ts),
            "updated_ts": utils.now(),
            "restriction": "",
        }
        self.chat_data_collection.insert_one(new_doc)
        log.log_new_chat(chat_id, chat_title)

    def add_user(self, user_id, username, first_name):
        now = utils.now()
        new_doc = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "created_at": now,
            "last_used_at": now,
            "superseded_at": "",
            "field_changed": "",
        }
        self.user_data_collection.insert_one(new_doc)
        log.log_new_user(user_id, username)

    def retrieve_user_data(self, user_id):
        q = {"user_id": float(user_id), "superseded_at": ""}
        result = self.user_data_collection.find_one(q)
        return result

    def supersede_user(self, entry, field_changed):
        # update previous entry
        update = {"superseded_at": utils.now(), "field_changed": field_changed}
        self.user_data_collection.update_one({"_id": entry["_id"]}, {"$set": update})
        log.log_user_updated(entry)

    def refresh_user(self, entry):
        entry["last_used_at"] = utils.now()
        obj = (
            self.user_data_collection.find({"user_id": float(entry.get("user_id", ""))})
            .sort([("created_at", DESCENDING)])
            .limit(1)
            .next()
        )
        self.user_data_collection.replace_one({"_id": obj["_id"]}, entry)

    def sync_user_data(self, update):
        if update.message is None:
            return
        user = self.retrieve_user_data(update.message.from_user.id)

        if user is None:
            # user is new, add to db
            return self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                update.message.from_user.first_name,
            )

        # check that username hasn't changed
        previous_username = (
            None if user.get("username", "") == "" else user.get("username", "")
        )  # username could be None
        if update.message.from_user.username != previous_username:
            self.supersede_user(user, "username")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                user.get("first_name", ""),
            )
            self.sync_user_data(update)

            return log.log_username_updated(update)

        # check that firstname hasn't changed
        if update.message.from_user.first_name != str(user.get("first_name", "")):
            self.supersede_user(user, "first_name")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                update.message.from_user.first_name,
            )

            return log.log_firstname_updated(update)

        self.refresh_user(user)

    def get_user_limit(self, user_id):
        current_job_count = self.count_entries_by_userid(user_id)

        result = self.user_whitelist_collection.find_one(
            {"user_id": float(user_id), "removed_ts": ""}
        )

        if result is None:
            return (
                current_job_count >= config.JOB_LIMIT_PER_PERSON,
                config.JOB_LIMIT_PER_PERSON,
            )

        new_limit = result.get("new_limit", 0)
        return (current_job_count, new_limit)


def entry_filter(entry):
    return {
        "created_ts": entry["created_ts"],
        "chat_id": entry["chat_id"],
        "jobname": entry["jobname"],
    }
