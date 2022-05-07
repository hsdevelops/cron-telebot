# TODO - clean db (if created > 1 month before, some fields are empty)

import config
from google.oauth2 import service_account
import pygsheets
from datetime import datetime, timedelta, timezone
import numpy as np

# define service
class SheetsService:
    def __init__(self):
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
                "client_x509_cert_url": config.SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL
            }
            creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=config.SCOPES)
            self.gc = pygsheets.authorize(custom_credentials=creds)
        else:
            self.gc = pygsheets.authorize(service_file='keys.json')
        
        self.gsheet = self.gc.open_by_key(config.GSHEET_ID)
        self.main_worksheet = self.gsheet.worksheet_by_title(config.MAIN_SHEETNAME)
        self.tz_lookup_worksheet = self.gsheet.worksheet_by_title(config.TZ_LOOKUP_SHEETNAME)

    def add_new_entry(self, chat_id, jobname):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        self.main_worksheet.insert_rows(row=1, values=[now, now, str(chat_id), jobname], inherit=True)

    def retrieve_latest_entry(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[(df["chat_id"]==chat_id)&(df["removed_ts"]=="")]
        entry_df = filtered_df[filtered_df["created_ts"] == filtered_df["created_ts"].max()]
        return entry_df
    
    def update_entry(self, entry):
        now = parse_time(datetime.now(timezone(timedelta(hours=config.TZ_OFFSET))))
        entry.at[0, "last_update_ts"] = now
        row_number = entry["gsheet_row_number"]
        entry = entry.drop(columns="gsheet_row_number")
        entry["chat_id"]= entry["chat_id"].astype(str)
        self.main_worksheet.update_row(row_number, entry.iloc[0].tolist())

    def retrieve_specific_entry(self, chat_id, jobname):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        return df[(df["chat_id"]==chat_id) & (df["jobname"]==jobname)]
    
    def check_exists(self, chat_id, jobname):
        df = self.main_worksheet.get_as_df()
        if len(df[(df["chat_id"]==chat_id) & (df["jobname"]==jobname)]) > 0:
            return True
        return False

    def get_entries_by_nextrun(self, ts):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[(df["nextrun_ts"]<=ts) & (df["removed_ts"]=="")]
        return filtered_df.iterrows()

    def get_entries_by_chatid(self, chat_id):
        df = self.main_worksheet.get_as_df()
        df["gsheet_row_number"] = np.arange(df.shape[0]) + 2
        filtered_df = df[(df["chat_id"]==chat_id) & (df["removed_ts"]=="")].reset_index(drop=True)
        return filtered_df.iterrows()
    
    def retrieve_tz(self, chat_id):
        df = self.tz_lookup_worksheet.get_as_df()
        result = df[df["chat_id"]==chat_id]
        if len(result) < 1:
            return None
        return int(get_value(result, "timezone"))
    
    def add_tz(self, chat_id, tz_offset):
        self.tz_lookup_worksheet.insert_rows(row=1, values=[str(chat_id), tz_offset], inherit=True)
        return

def edit_entry_single_field(entry, key, value):
    entry = entry.reset_index(drop=True)
    entry.at[0, key] = value
    return entry

def edit_entry_multiple_fields(entry, key_value_pairs):
    for key in key_value_pairs:
        entry.at[0, key] = key_value_pairs[key]
    return entry

def get_value(entry, key):
    return entry.iloc[0][key]

def parse_time(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%d %H:%M")