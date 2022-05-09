# TODO - clean db (if created > 1 month before, some fields are empty)

import logging
import config
from google.oauth2 import service_account
import pygsheets
from datetime import datetime, timedelta, timezone
import numpy as np


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# define service
class SheetsService:
    def __init__(self, update=None):
        if config.ENV:
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
        else:
            self.gc = pygsheets.authorize(service_file="keys.json")

        gsheet = self.gc.open_by_key(config.GSHEET_ID)
        self.main_worksheet = gsheet.worksheet_by_title(config.JOB_DATA_SHEETNAME)
        self.chat_data_worksheet = gsheet.worksheet_by_title(config.CHAT_DATA_SHEETNAME)
        self.user_data_worksheet = gsheet.worksheet_by_title(config.USER_DATA_SHEETNAME)

        if update is not None:
            self.sync_user_data(update)

    def add_new_entry(self, chat_id, jobname, username):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        self.main_worksheet.insert_rows(
            row=1, values=[now, now, username, str(chat_id), jobname], inherit=True
        )

    def retrieve_latest_entry(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[(df["chat_id"] == chat_id) & (df["removed_ts"] == "")]
        result = filtered_df[
            filtered_df["created_ts"] == filtered_df["created_ts"].max()
        ]
        if len(result) < 1:
            return None
        return result

    def update_entry(self, entry):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        entry = edit_entry_single_field(entry, "last_update_ts", now)
        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")
        entry["chat_id"] = entry["chat_id"].astype(str)
        self.main_worksheet.update_row(row_number, entry.iloc[0].tolist())

    def retrieve_specific_entry(self, chat_id, jobname, include_removed=False):
        df = self.main_worksheet.get_as_df()
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
        if (
            len(
                df[
                    (df["chat_id"] == chat_id)
                    & (df["jobname"] == jobname)
                    & (df["removed_ts"] == "")
                ]
            )
            > 0
        ):
            return True
        return False

    def get_entries_by_nextrun(self, ts):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[
            (df["nextrun_ts"] <= ts) & (df["removed_ts"] == "") & (df["crontab"] != "")
        ].iterrows()
        return list(filtered_df)

    def get_entries_by_chatid(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = (
            df[(df["chat_id"] == chat_id) & (df["removed_ts"] == "")]
            .reset_index(drop=True)
            .iterrows()
        )
        return list(filtered_df)

    def retrieve_tz(self, chat_id):
        df = self.chat_data_worksheet.get_as_df()
        result = df[df["chat_id"] == chat_id]
        if len(result) < 1:
            return None
        return int(get_value(result, "tz_offset"))

    def add_chat_data(
        self,
        chat_id,
        chat_title,
        chat_type,
        tz_offset,
        created_by_username,
        telegram_ts,
    ):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        self.chat_data_worksheet.insert_rows(
            row=1,
            values=[
                str(chat_id),
                chat_title,
                chat_type,
                tz_offset,
                created_by_username,
                parse_time(telegram_ts),
                now,
            ],
            inherit=True,
        )
        return

    def add_user(self, user_id, username, first_name):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        self.user_data_worksheet.insert_rows(
            row=1, values=[str(user_id), username, first_name, now, now], inherit=True
        )

    def retrieve_user_data(self, user_id):
        df = self.user_data_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        result = df[(df["user_id"] == user_id) & (df["superseded_at"] == "")]
        if len(result) < 1:
            return None
        return result

    def supersede_user(self, entry, field_changed):
        # update previous entry
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        entry = edit_entry_multiple_fields(
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

    def refresh_user(self, entry):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        entry = edit_entry_single_field(entry, "last_used_at", now)

        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")

        entry["user_id"] = entry["user_id"].astype(str)  # type check

        self.user_data_worksheet.update_row(row_number, entry.iloc[0].tolist())

    def sync_user_data(self, update):
        user = self.retrieve_user_data(update.message.from_user.id)

        if user is None:
            # user is new, add to db
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                update.message.from_user.first_name,
            )

            logger.info(
                "New user added, username=%s, user_id=%s",
                update.message.from_user.username,
                update.message.from_user.id,
            )

            return

        # check that username hasn't changed
        if update.message.from_user.username != get_value(user, "username"):
            self.supersede_user(user, "username")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                get_value(user, "first_name"),
            )
            self.sync_user_data(update)

            logger.info(
                "username updated, new username=%s, user_id=%s",
                update.message.from_user.username,
                update.message.from_user.id,
            )
            return

        # check that firstname hasn't changed
        if update.message.from_user.first_name != get_value(user, "first_name"):
            self.supersede_user(user, "first_name")
            self.add_user(
                update.message.from_user.id,
                update.message.from_user.username,
                update.message.from_user.first_name,
            )

            logger.info(
                "first_name updated, new first_name=%s, username=%s, user_id=%s",
                update.message.from_user.first_name,
                update.message.from_user.username,
                update.message.from_user.id,
            )
            return

        self.refresh_user(user)


def edit_entry_single_field(entry, key, value):
    entry = entry.reset_index(drop=True)
    entry.at[0, key] = value
    return entry


def edit_entry_multiple_fields(entry, key_value_pairs):
    entry = entry.reset_index(drop=True)
    for key in key_value_pairs:
        entry.at[0, key] = key_value_pairs[key]
    return entry


def get_value(entry, key):
    return entry.iloc[0][key]


def parse_time(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%d %H:%M")
