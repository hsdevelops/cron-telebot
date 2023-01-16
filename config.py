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


""" DB config """
MONGODB_CONNECTION_STRING = getenv("MONGODB_CONNECTION_STRING")
MONGODB_DB = "rm_bot"
MONGODB_JOB_DATA_COLLECTION = "job_data"
MONGODB_CHAT_DATA_COLLECTION = "chat_data"
MONGODB_USER_DATA_COLLECTION = "user_data"
MONGODB_USER_WHITELIST_COLLECTION = "whitelist"
