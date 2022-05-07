from os import getenv
from dotenv import load_dotenv

load_dotenv()

""" General config """
ENV = getenv('ENV') # set this only in prod environment
TZ_OFFSET = 8.0  # (UTC+08:00)

""" Telegram config """ 

# configuration
TELEGARM_BOT_TOKEN = getenv("TELEGRAM_BOT_TOKEN")
BOTHOST = getenv("BOTHOST") # only required in prod environment

# custom messages
start_message = "*Thank you for using Recurring Messages\!*\n\nTo start, please tell me your UTC timezone\. For example, if your timezone is UTC\-8, enter \-8\."
help_message = "I can help you schedule recurring messages\.\n\nYou can control me by sending these commands\:\n\n\/add \- add a new job\n\/list \- list running jobs\n\/delete \- delete a job"
delete_message = "Hey, tell me the name of the job you want to delete. Get /list of available jobs."
request_jobname_message = "Give me your job name"
request_crontab_message = "Give me your crontab: \* \* \* \* \*"
request_text_message = "Now give me what you want to send"
simple_prompt_message = "\/add to create new job"
prompt_new_job_message = "The job already got this field\. Please \/add and create new job\. If you want to override, delete job and create again\."
invalid_new_job_message = "A job with this name already exists\. Please \/add and create new job\. If you want to override, \/delete job and create again\."
confirm_message = "Ok\. Done\. Added\. Now please wait\."
invalid_crontab_message = "Crontab is invalid\. Please provide a valid crontab\."
list_jobs_message = ""
delete_success_message = "Yeet\! This job is now gone\."
error_message = "You know that\'s not right\.\.\."


""" GSheets config """ 
# Create the Google Sheet manually. Set all values as plain text format.
# Remember to share the Google Sheet with SERVICE_ACCOUNT_INFO_CLIENT_EMAIL

SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
GSHEET_ID = getenv("GSHEET_ID") # can be found in the gsheet's url
MAIN_SHEETNAME = 'raw data' # depends on what you name your sheet, defaults to Sheet1.
TZ_LOOKUP_SHEETNAME = 'tz lookup' # depends on what you name your sheet, defaults to Sheet1.

# To use Google Sheets API,
# create a google cloud project: https://developers.google.com/workspace/guides/create-project
# create service account credentials: https://developers.google.com/workspace/guides/create-credentials#service-account
if ENV:
    SERVICE_ACCOUNT_INFO_TYPE = getenv('SERVICE_ACCOUNT_INFO_TYPE')
    SERVICE_ACCOUNT_INFO_PROJECT_ID = getenv('SERVICE_ACCOUNT_INFO_PROJECT_ID')
    SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID = getenv('SERVICE_ACCOUNT_INFO_PRIVATE_KEY_ID')
    SERVICE_ACCOUNT_INFO_PRIVATE_KEY = getenv('SERVICE_ACCOUNT_INFO_PRIVATE_KEY').replace('\\n', '\n')
    SERVICE_ACCOUNT_INFO_CLIENT_EMAIL = getenv('SERVICE_ACCOUNT_INFO_CLIENT_EMAIL')
    SERVICE_ACCOUNT_INFO_CLIENT_ID = getenv('SERVICE_ACCOUNT_INFO_CLIENT_ID')
    SERVICE_ACCOUNT_INFO_AUTH_URI = getenv('SERVICE_ACCOUNT_INFO_AUTH_URI')
    SERVICE_ACCOUNT_INFO_TOKEN_URI = getenv('SERVICE_ACCOUNT_INFO_TOKEN_URI')
    SERVICE_ACCOUNT_INFO_AUTH_PROVIDER_X509_CERT_URL = getenv('SERVICE_ACCOUNT_INFO_AUTH_PROVIDER_X509_CERT_URL')
    SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL = getenv('SERVICE_ACCOUNT_INFO_CLIENT_X509_CERT_URL')
