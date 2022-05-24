from os import getenv
from dotenv import load_dotenv

load_dotenv()

""" General config """
ENV = getenv("ENV")  # set this only in prod environment
TZ_OFFSET = 8.0  # (UTC+08:00)

""" Telegram config """

# configuration
TELEGARM_BOT_TOKEN = getenv("TELEGRAM_BOT_TOKEN")
BOTHOST = getenv("BOTHOST")  # only required in prod environment

# custom messages
start_message = "*Thank you for using Recurring Messages\!*\n\nTo start, please tell me your UTC timezone\. For example, if your timezone is UTC\-8, enter \-8\.\n\n\(swipe left to reply to this message\)"
help_message = "I can help you schedule recurring messages using <a href='https://crontab.guru/'>cron schedule expressions</a> (min. 1 minute intervals).\n\n<b>Available commands</b>\n/add - add a new job\n/list - list running jobs\n/delete - delete a job\n/options - view advanced job options\n/checkcron - check the validity/meaning of a cron expression\n\n<b>Found a bug?</b>\nPlease contact the bot owner at hs.develops.1@gmail.com."  # html
delete_message = "Hey, tell me the name of the job you want to delete. Get /list of available jobs.\n\n(swipe left to reply to this message)"
request_jobname_message = (
    "Give me your job name\n\n(swipe left to reply to this message)"
)
request_crontab_message = "Give me your cron schedule expression (e.g. 4 5 * * *), click <a href='https://crontab.guru/'>here</a> if you need help. Use /checkcron to check your cron expression.\n\n(swipe left to reply to this message)"  # html
request_text_message = (
    "Now give me what you want to send\n\n(swipe left to reply to this message)"
)
simple_prompt_message = "\/add to create a new job"
prompt_new_job_message = "The job already got this field\. Please \/add and create a new job\. If you want to override, \/delete job and create again\."
invalid_new_job_message = "A job with this name already exists\. Please \/add and create a new job\. If you want to override, \/delete job and create again\."
confirm_message_prepend = "Ok. Done. Added."
confirm_message_append = "To set advanced options, please use /options."
invalid_crontab_message = "This expression is invalid. Please provide a valid expression. Click <a href='https://crontab.guru/'>here</a> if you need help. Use /checkcron to check your cron expression."  # html
list_jobs_message = "Hey, choose the job you are interested to know more about.\n\n(swipe left to reply to this message)"
delete_success_message = "Yeet! This job is now gone."
error_message = "You know that's not right..."
checkcron_message = "Hey, send me your cron expression, I'll decrypt it for you.\n\n(swipe left to reply to this message)"
checkcron_invalid_message = "Alright, that's not a valid cron. Click <a href='https://crontab.guru/'>here</a> if you need help."
checkcron_meaning_message = "Ok, that means: "
list_options_message = "Currently I only have one advanced option available LOL.\n\n/deleteprevious - Delete the previous message when the next message is sent. Ensures that only one message per job is in the chat at a time. Disabled by default. Note that this option is subject to the limitations mentioned in the <a href='https://core.telegram.org/bots/api#deletemessage'>Telegram API documentation</a>.\n\nTo request for a new feature, please open an issue <a href='https://github.com/huishun98/recurring-messages-telebot/issues'>here</a>."  # html
option_delete_previous_message = "Tell me the name of the job you want to toggle the /deleteprevious option for.\n\n(swipe left to reply to this message)"

""" GSheets config """
# Create the Google Sheet manually. Set all values as plain text format.
# Remember to share the Google Sheet with SERVICE_ACCOUNT_INFO_CLIENT_EMAIL

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GSHEET_ID = getenv("GSHEET_ID")  # can be found in the gsheet's url
JOB_DATA_SHEETNAME = (
    "job data"  # depends on what you name your sheet, defaults to Sheet1.
)
CHAT_DATA_SHEETNAME = (
    "chat data"  # depends on what you name your sheet, defaults to Sheet2.
)
USER_DATA_SHEETNAME = (
    "user data"  # depends on what you name your sheet, defaults to Sheet3.
)


# To use Google Sheets API,
# create a google cloud project: https://developers.google.com/workspace/guides/create-project
# create service account credentials: https://developers.google.com/workspace/guides/create-credentials#service-account
if ENV:
    SERVICE_ACCOUNT_INFO_TYPE = getenv("SERVICE_ACCOUNT_INFO_TYPE")
    SERVICE_ACCOUNT_INFO_PROJECT_ID = getenv("SERVICE_ACCOUNT_INFO_PROJECT_ID")
    SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID = getenv("SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID")
    SERVICE_ACCOUNT_INFO_PRIVATE_KEY = getenv(
        "SERVICE_ACCOUNT_INFO_PRIVATE_KEY"
    ).replace("\\n", "\n")
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
