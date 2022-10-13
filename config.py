from os import getenv
from dotenv import load_dotenv

load_dotenv()

""" General config """
# Set ENV to any value to use webhook instead of polling for bot. Must be set in prod environment.
ENV = getenv("ENV")
TZ_OFFSET = 8.0  # (UTC+08:00)
JOB_LIMIT_PER_PERSON = 10

""" Telegram config """
TELEGRAM_BOT_TOKEN = getenv("TELEGRAM_BOT_TOKEN")
BOTHOST = getenv("BOTHOST")  # only required in prod environment

""" GSheets config """
# Create the Google Sheet manually. Set all values as plain text format.
# Remember to share the Google Sheet with SERVICE_ACCOUNT_INFO_CLIENT_EMAIL

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GSHEET_ID = getenv("GSHEET_ID")  # can be found in the gsheet's url
JOB_DATA_SHEETNAME = "job data"  # defaults to Sheet1.
CHAT_DATA_SHEETNAME = "chat data"  # defaults to Sheet2.
USER_DATA_SHEETNAME = "user data"  # defaults to Sheet3.
USER_WHITELIST_SHEETNAME = "whitelist"  # defaults to Sheet4.


# To use Google Sheets API,
# create a google cloud project: https://developers.google.com/workspace/guides/create-project
# create service account credentials: https://developers.google.com/workspace/guides/create-credentials#service-account
SERVICE_ACCOUNT_INFO_TYPE = getenv("SERVICE_ACCOUNT_INFO_TYPE")
SERVICE_ACCOUNT_INFO_PROJECT_ID = getenv("SERVICE_ACCOUNT_INFO_PROJECT_ID")
SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID = getenv("SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID")
SERVICE_ACCOUNT_INFO_PRIVATE_KEY = getenv("SERVICE_ACCOUNT_INFO_PRIVATE_KEY").replace(
    "\\n", "\n"
)
SERVICE_ACCOUNT_INFO_CLIENT_EMAIL = getenv("SERVICE_ACCOUNT_INFO_CLIENT_EMAIL")
SERVICE_ACCOUNT_INFO_CLIENT_ID = getenv("SERVICE_ACCOUNT_INFO_CLIENT_ID")
SERVICE_ACCOUNT_INFO_AUTH_URI = getenv("SERVICE_ACCOUNT_INFO_AUTH_URI")
SERVICE_ACCOUNT_INFO_TOKEN_URI = getenv("SERVICE_ACCOUNT_INFO_TOKEN_URI")
SERVICE_ACCOUNT_INFO_AUTH_PROVIDER_X509_CERT_URL = getenv(
    "SERVICE_ACCOUNT_INFO_AUTH_PROVIDER_X509_CERT_URL"
)
SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL = getenv(
    "SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL"
)
