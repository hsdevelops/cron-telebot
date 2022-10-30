import config
import pygsheets
import numpy as np
from common import log, utils
from google.oauth2 import service_account
from datetime import datetime, timedelta, timezone

# define service
class SheetsService:
    def __init__(self, update=None):
        # if config.ENV:
        service_account_info = {
            "type": config.SERVICE_ACCOUNT_INFO_TYPE,
            "project_id": config.SERVICE_ACCOUNT_INFO_PROJECT_ID,
            "private_key_id": config.SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID,
            "private_key": config.SERVICE_ACCOUNT_INFO_PRIVATE_KEY,
            "client_email": config.SERVICE_ACCOUNT_INFO_CLIENT_EMAIL,
            "client_id": config.SERVICE_ACCOUNT_INFO_CLIENT_ID,
            "auth_uri": config.SERVICE_ACCOUNT_INFO_AUTH_URI,
            "token_uri": config.SERVICE_ACCOUNT_INFO_TOKEN_URI,
            "auth_provider_x509_cert_url": config.SERVICE_ACCOUNT_INFO_AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": config.SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL,
        }
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=config.SCOPES
        )
        self.gc = pygsheets.authorize(custom_credentials=creds)
        # else:
        #     self.gc = pygsheets.authorize(service_file="keys.json")

        gsheet = self.gc.open_by_key(config.GSHEET_ID)
        self.main_worksheet = gsheet.worksheet_by_title(config.JOB_DATA_SHEETNAME)
        self.chat_data_worksheet = gsheet.worksheet_by_title(config.CHAT_DATA_SHEETNAME)
        self.user_data_worksheet = gsheet.worksheet_by_title(config.USER_DATA_SHEETNAME)
        self.user_whitelist_worksheet = gsheet.worksheet_by_title(
            config.USER_WHITELIST_SHEETNAME
        )

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
        self.main_worksheet.insert_rows(
            row=1,
            values=[
                now,
                now,
                user_id,
                user_id,
                str(chat_id),
                str(channel_id),
                jobname,
                crontab,
                content,
                content_type,
                photo_id,
                photo_group_id,
            ],
            inherit=True,
        )

        log.log_new_entry(jobname, chat_id)

    def retrieve_latest_entry(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[(df["chat_id"] == chat_id) & (df["removed_ts"] == "")]
        result = filtered_df[
            filtered_df["created_ts"] == filtered_df["created_ts"].max()
        ]
        if len(result) < 1:
            return None
        return result

    def update_entry(self, entry):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_single_field(entry, "last_update_ts", now)
        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")
        self.main_worksheet.update_row(
            row_number, entry.astype(str).iloc[0].tolist()
        )  # source of bug
        log.log_entry_updated(entry)

    def retrieve_specific_entry(self, chat_id, jobname, include_removed=False):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        running_filter = df["removed_ts"] == ""
        if include_removed:
            running_filter = True
        result = df[
            (df["chat_id"] == chat_id) & (df["jobname"] == jobname) & running_filter
        ]
        if len(result) < 1:
            return None
        return result

    def check_exists(self, chat_id, jobname):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")

        return (
            len(
                df[
                    (df["chat_id"] == chat_id)
                    & (df["jobname"] == jobname)
                    & (df["removed_ts"] == "")
                ]
            )
            > 0
        )

    def get_entries_by_nextrun(self, ts):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[
            (df["nextrun_ts"] <= ts) & (df["removed_ts"] == "") & (df["crontab"] != "")
        ].iterrows()
        return [row for _, row in filtered_df]

    def get_entries_by_chatid(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = (
            df[(df["chat_id"] == chat_id) & (df["removed_ts"] == "")]
            .reset_index(drop=True)
            .iterrows()
        )
        return list(filtered_df)

    def count_entries_by_userid(self, user_id):
        df = self.main_worksheet.get_as_df()
        df["jobname"] = df["jobname"].astype("str")
        filtered_df = df[(df["created_by"] == user_id) & (df["removed_ts"] == "")]
        return len(filtered_df)

    def retrieve_tz(self, chat_id):
        df = self.chat_data_worksheet.get_as_df()
        result = df[df["chat_id"] == chat_id]
        if len(result) < 1:
            return None
        return float(utils.get_value(result, "tz_offset"))

    def get_chat_entry(self, chat_id):
        df = self.chat_data_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        df["chat_id"] = df["chat_id"].astype("str")
        result = df[df["chat_id"] == str(chat_id)]
        if len(result) < 1:
            return None
        return result

    def update_chat_entry(self, entry, updated_field="restriction"):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_multiple_fields(
            entry,
            {"updated_ts": now, "utc_tz": "'%s" % utils.get_value(entry, "utc_tz")},
        )
        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")
        self.chat_data_worksheet.update_row(
            row_number, entry.astype(str).iloc[0].tolist()
        )  # source of bug
        log.log_chat_entry_updated(entry, updated_field)

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
        self.chat_data_worksheet.insert_rows(
            row=1,
            values=[
                str(chat_id),
                chat_title,
                chat_type,
                tz_offset,
                "'%s" % utc_tz,
                created_by,
                utils.parse_time_millis(telegram_ts),
                now,
            ],
            inherit=True,
        )

        log.log_new_chat(chat_id, chat_title)

    def add_user(self, user_id, username, first_name):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        self.user_data_worksheet.insert_rows(
            row=1, values=[str(user_id), username, first_name, now, now], inherit=True
        )
        log.log_new_user(user_id, username)

    def retrieve_user_data(self, user_id):
        df = self.user_data_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        result = df[(df["user_id"] == user_id) & (df["superseded_at"] == "")]
        if len(result) < 1:
            return None
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

        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")

        entry["user_id"] = entry["user_id"].astype(str)  # type check

        self.user_data_worksheet.update_row(row_number, entry.iloc[0].tolist())
        log.log_user_updated(entry)

    def refresh_user(self, entry):
        now = utils.parse_time_millis(
            datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))
        )
        entry = utils.edit_entry_single_field(entry, "last_used_at", now)

        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")

        entry["user_id"] = entry["user_id"].astype(str)  # type check

        self.user_data_worksheet.update_row(row_number, entry.iloc[0].tolist())

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

        df = self.user_whitelist_worksheet.get_as_df()
        result = df[(df["user_id"] == user_id) & (df["removed_ts"] == "")]

        if len(result) < 1:
            return True

        new_limit = utils.get_value(result, "new_limit")
        return current_job_count >= new_limit
