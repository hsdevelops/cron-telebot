import gc
import json
import requests
from common import log, utils
from database import mongo
from flask import Flask, Response
from urllib.parse import urlencode
from config import TELEGRAM_BOT_TOKEN, TZ_OFFSET
from datetime import datetime, timedelta, timezone


app = Flask(__name__)


@app.route("/api", methods=["GET", "POST"])
def run():
    db_service = mongo.MongoService()
    now = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))
    parsed_time = utils.parse_time_mins(now)
    entries = db_service.get_entries_by_nextrun(parsed_time)

    log.log_entry_count(len(entries))

    if len(entries) < 1:
        log.log_completion(0, len(entries))
        gc.collect()
        return Response(status=200)

    count = 0
    for row in entries:
        channel_id = row.get("channel_id", "")
        chat_id = row.get("chat_id", "")
        if channel_id != "":
            chat_id = channel_id
        content = row.get("content", "")
        content_type = row.get("content_type", "")
        photo_id = row.get("photo_id", "")
        photo_group_id = str(row.get("photo_group_id", ""))
        crontab = row.get("crontab", "")
        previous_message_id = str(row.get("previous_message_id", ""))

        bot_message_id, err = send_message(
            chat_id, content, content_type, photo_id, photo_group_id
        )
        if row.get("option_delete_previous", "") != "" and previous_message_id != "":
            delete_message(chat_id, previous_message_id)

        # calculate and update next run time
        user_tz_offset = db_service.retrieve_tz(chat_id)
        user_nextrun_ts, db_nextrun_ts = utils.calc_next_run(crontab, user_tz_offset)

        db_service.update_entry(
            {
                "created_ts": row.get("created_ts", ""),
                "chat_id": row.get("chat_id", ""),
                "jobname": row.get("jobname", ""),
            },
            {
                "nextrun_ts": db_nextrun_ts,
                "user_nextrun_ts": user_nextrun_ts,
                "previous_message_id": str(bot_message_id),
                "remarks": "" if err is None else err,
                "removed_ts": "" if err is None else parsed_time,
            },
        )
        count = count + 1

    gc.collect()  # https://github.com/googleapis/google-api-python-client/issues/535

    log.log_completion(count, len(entries))

    return Response(status=200)


def prepare_photos(photo_id, content):
    photo_ids = photo_id.split(";")
    media = []
    files = {}
    for i, photo_id in enumerate(photo_ids):
        file_details_endpoint = (
            "https://api.telegram.org/bot{}/getFile?file_id={}".format(
                TELEGRAM_BOT_TOKEN, photo_id
            )
        )
        file_details_response = requests.get(file_details_endpoint)
        file_url = "https://api.telegram.org/file/bot{}/{}".format(
            TELEGRAM_BOT_TOKEN, file_details_response.json()["result"]["file_path"]
        )
        file_response = requests.get(file_url)
        open("photo-%d" % i, "wb").write(file_response.content)
        files["photo-%d" % i] = open("photo-%d" % i, "rb")

        media.append(
            {
                "type": "photo",
                "media": "attach://photo-%d" % i,
                "caption": content if i <= 0 else "",
            }
        )
    return json.dumps(media), files


def send_message(chat_id, content, content_type, photo_id, photo_group_id):
    if photo_group_id != "":  # media group
        media, files = prepare_photos(photo_id, content)
        query_string = urlencode({"chat_id": chat_id, "media": media})
        telebot_api_endpoint = (
            "https://api.telegram.org/bot{}/sendMediaGroup?{}".format(
                TELEGRAM_BOT_TOKEN, query_string
            )
        )
        response = requests.post(telebot_api_endpoint, files=files)
    elif photo_id != "":  # single photo
        query = {
            "chat_id": chat_id,
            "photo": photo_id,
            "caption": content,
            "parse_mode": "html",
        }
        query_string = urlencode(query)
        telebot_api_endpoint = "https://api.telegram.org/bot{}/sendPhoto?{}".format(
            TELEGRAM_BOT_TOKEN, query_string
        )
        response = requests.get(telebot_api_endpoint)
    elif content_type == "poll":
        poll_content = json.loads(content)
        telebot_api_endpoint = "https://api.telegram.org/bot{}/sendPoll".format(
            TELEGRAM_BOT_TOKEN
        )
        parameters = {
            "chat_id": chat_id,
            "question": poll_content.get("question"),
            "options": json.dumps(
                [option.get("text") for option in poll_content.get("options")]
            ),
            "type": poll_content.get("type"),
            "is_anonymous": poll_content.get("is_anonymous"),
            "allows_multiple_answers": poll_content.get("allows_multiple_answers"),
            "correct_option_id": poll_content.get("correct_option_id"),
            "explanation": poll_content.get("explanation"),
            "explanation_parse_mode": "html",
            "is_closed": poll_content.get("is_closed"),
            "close_date": poll_content.get("close_date"),
        }
        response = requests.get(telebot_api_endpoint, data=parameters)
    else:  # text message
        query = {"chat_id": chat_id, "text": content, "parse_mode": "html"}
        query_string = urlencode(query)
        telebot_api_endpoint = "https://api.telegram.org/bot{}/sendMessage?{}".format(
            TELEGRAM_BOT_TOKEN, query_string
        )
        response = requests.get(telebot_api_endpoint)

    log.log_api_send_message(chat_id, content, response.status_code)

    if response.status_code != 200:
        return "", "Error {}: {}".format(
            response.status_code, response.json()["description"]
        )

    if photo_group_id != "":
        return (
            ";".join(
                [str(message["message_id"]) for message in response.json()["result"]]
            ),
            None,
        )

    return response.json()["result"]["message_id"], None


def delete_message(chat_id, previous_message_id):
    for message_id in previous_message_id.split(";"):
        telebot_api_endpoint = "https://api.telegram.org/bot{}/deleteMessage?chat_id={}&message_id={}".format(
            TELEGRAM_BOT_TOKEN, chat_id, message_id
        )
        response = requests.get(telebot_api_endpoint)
        log.log_api_previous_message_deletion(chat_id, message_id, response.status_code)
    return response.json()["ok"]


if __name__ == "__main__":
    app.run(debug=True)
