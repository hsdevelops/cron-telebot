from flask import Flask, Response
from config import TELEGARM_BOT_TOKEN, TZ_OFFSET
from datetime import datetime, timedelta, timezone
import logging
from croniter import croniter
from sheets import SheetsService, edit_entry_multiple_fields, parse_time
import requests
from helper import calc_next_run

app = Flask(__name__)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

@app.route("/", methods=['GET', 'POST'])
def run():
    # TODO - allow only POST
    # TODO - add authentication
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))
    sheets_service = SheetsService()
    entries = retrieve_entries_from_db(sheets_service, now)
    for index, row in entries:
        chat_id = row["chat_id"]
        content = row["content"]
        crontab = row["crontab"]
        send_message(chat_id, content)

        # calculate and update next run time
        user_tz_offset = sheets_service.retrieve_tz(chat_id)
        user_nextrun_ts, db_nextrun_ts = calc_next_run(crontab, user_tz_offset)

        updated_entry = edit_entry_multiple_fields(row.to_frame().T, {
            "nextrun_ts": db_nextrun_ts,
            "user_nextrun_ts": user_nextrun_ts})
        sheets_service.update_entry(updated_entry)

    return Response(status=200)

def retrieve_entries_from_db(sheets_service, nextrun_ts):
    parsed_time = parse_time(nextrun_ts)
    return sheets_service.get_entries_by_nextrun(parsed_time)

def send_message(chat_id, content):
    # TODO - if feature request: photo
    telebot_api_endpoint = "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&parse_mode=markdown".format(
        TELEGARM_BOT_TOKEN, chat_id, content)
    response = requests.get(telebot_api_endpoint)
    logger.info('Message sent, chat_id="%s", message="%s", response_status="%s"', chat_id, content, response.status_code)

if __name__ == '__main__':
    app.run(debug=True)
