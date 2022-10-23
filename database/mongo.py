# TODO - clean db (if created > 1 month before, some fields are empty)

import config
from common import log, utils
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

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
    ):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
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
                "nextrun_ts": "",
                "user_nextrun_ts": "",
                "removed_ts": "",
                "remarks": "",
            }
        )

        log.log_new_entry(jobname, chat_id)

    def retrieve_latest_entry(self, chat_id):
        return (
            self.main_collection.find({"chat_id": chat_id, "removed_ts": ""})
            .sort([("created_ts", -1)])
            .limit(1)
            .next()
        )

    def update_entry(self, entry):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_single_field(entry, "last_update_ts", now)

        self.main_collection.replace_one(
            {
                "created_ts": utils.get_value(entry, "created_ts"),
                "chat_id": utils.get_value(entry, "chat_id"),
                "jobname": utils.get_value(entry, "jobname"),
            },
            entry,
            upsert=True,
        )

        log.log_entry_updated(entry)

    def retrieve_specific_entry(self, chat_id, jobname, include_removed=False):
        filter = {"chat_id": chat_id, "jobname": jobname}
        if not include_removed:
            filter["removed_ts"] = ""
        return self.main_collection.find_one(filter)

    def check_exists(self, chat_id, jobname):
        return self.retrieve_specific_entry(chat_id, jobname) is not None

    def get_entries_by_nextrun(self, ts):
        return list(
            self.main_collection.find(
                {"nextrun_ts": {"$lte": ts}, "removed_ts": "", "crontab": {"$ne": ""}}
            )
        )

    def get_entries_by_chatid(self, chat_id):
        return list(
            self.main_collection.find(
                {
                    "chat_id": chat_id,
                    "removed_ts": "",
                }
            )
        )

    def count_entries_by_userid(self, user_id):
        return self.main_collection.count_documents(
            {
                "created_by": user_id,
                "removed_ts": "",
            }
        )

    def retrieve_tz(self, chat_id):
        entry = self.get_chat_entry(chat_id)
        if entry is None:
            return None
        return float(utils.get_value(entry, "tz_offset"))

    def get_chat_entry(self, chat_id):
        return self.chat_data_collection.find_one({"chat_id": chat_id})

    def update_chat_entry(self, entry):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_multiple_fields(
            entry, {"updated_ts": now, "utc_tz": utils.get_value(entry, "utc_tz")}
        )

        self.chat_data_collection.replace_one(
            {"chat_id": utils.get_value(entry, "chat_id")}, entry
        )

        log.log_chat_entry_updated(entry)

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
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        self.chat_data_collection.insert_one(
            {
                "chat_id": chat_id,
                "chat_title": chat_title,
                "chat_type": chat_type,
                "tz_offset": tz_offset,
                "utc_tz": utc_tz,
                "created_by": created_by,
                "telegram_ts": utils.parse_time_millis(telegram_ts),
                "updated_ts": now,
                "restriction": "",
            }
        )

        log.log_new_chat(chat_id, chat_title)

    def add_user(self, user_id, username, first_name):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        self.user_data_collection.insert_one(
            {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "created_at": now,
                "last_used_at": now,
                "superseded_at": "",
                "field_changed": "",
            }
        )

        log.log_new_user(user_id, username)

    def retrieve_user_data(self, user_id):
        result = self.user_data_collection.find_one(
            {"user_id": user_id, "superseded_at": ""}
        )
        return result

    def supersede_user(self, entry, field_changed):
        # update previous entry
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_multiple_fields(
            entry,
            {
                "superseded_at": now,
                "field_changed": field_changed,
            },
        )

        self.user_data_collection.replace_one(
            {"user_id": utils.get_value(entry, "user_id")},
            entry,
        )

        log.log_user_updated(entry)

    def refresh_user(self, entry):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_single_field(entry, "last_used_at", now)

        obj = (
            self.user_data_collection.find(
                {"user_id": utils.get_value(entry, "user_id")}
            )
            .sort([("created_at", -1)])
            .limit(1)
            .next()
        )

        self.user_data_collection.replace_one(
            {"_id": obj["_id"]},
            entry,
        )

    def sync_user_data(self, update):
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
            None
            if utils.get_value(user, "username") == ""
            else utils.get_value(user, "username")
        )  # username could be None
        if update.message.from_user.username != previous_username:
            self.supersede_user(user, "username")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                utils.get_value(user, "first_name"),
            )
            self.sync_user_data(update)

            return log.log_username_updated(update)

        # check that firstname hasn't changed
        if update.message.from_user.first_name != str(
            utils.get_value(user, "first_name")
        ):
            self.supersede_user(user, "first_name")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                update.message.from_user.first_name,
            )

            return log.log_firstname_updated(update)

        self.refresh_user(user)

    def exceed_user_limit(self, user_id):
        current_job_count = self.count_entries_by_userid(user_id)

        if current_job_count < config.JOB_LIMIT_PER_PERSON:
            return False

        result = self.user_whitelist_collection.find_one(
            {"user_id": user_id, "removed_ts": ""}
        )

        if result is None:
            return True

        new_limit = utils.get_value(result, "new_limit")
        return current_job_count >= new_limit
