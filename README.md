# RM Bot

RM Bot ([@cron_telebot](https://t.me/cron_telebot)) is a Telegram bot that schedules recurring Telegram messages. :sparkles:

Refer to our [user guide](https://github.com/hsdevelops/rm-bot/wiki/User-Guide) for usage instructions.

## Noteworthy files
1. [main.py](./main.py) — telegram bot, to add/delete/view the recurring jobs
2. [api.py](./api.py) — flask app, ping the endpoint to trigger check and send all required messages
3. [config.py](./config.py) — all the configurations you need to change for the bot
4. [mongo.py](./database/mongo.py) — handles interaction with the mongo database

## Prerequisites
1. Telegram bot created with [@botfather](https://telegram.me/botfather)
2. A Google Cloud Service Account ([documentation](https://cloud.google.com/iam/docs/creating-managing-service-accounts#creating))
3. Existing Google Sheet OR MongoDB. If using Google Sheets,
   * Copy this [Google Sheet template](https://docs.google.com/spreadsheets/d/1FKfdxax5hDHdCZ1K1TTI1G8pO4hES1oloK6ob0Spk-w/edit?usp=sharing)
   * Share the Google Sheet with the `SERVICE_ACCOUNT_INFO_CLIENT_EMAIL` of the Google Cloud Service Account

## Running locally

1. Configure environment variables. See [config.py](./config.py) for the required environment variables and how you can get them.

2. Install Python and pip and set up virtual environment. 
   ```
   virtualenv venv
   source venv/bin/activate
   pip install -r requirements-all.txt
   ```

3. Start services. Run `python main.py` to start the telegram bot. On another terminal, run `python api.py` to start the Flask endpoint (base path is `/api`).

## Running in production
1. Configure environment variables. See [config.py](./config.py) for the required environment variables and how you can get them.
   * Remember to set the ENV environment variable to any value of your choice (e.g. `dev`, `uat`, `prod`)
2. Entrypoint is `gunicorn main:app`. No need to run bot and api separately.

## Contributing

If you're looking for a way to contribute, you can scan through our existing issues for something to work on. See [the contributing guide](./CONTRIBUTING.md) for detailed instructions on how to get started with our project.

## License

The project is licensed under a [GNU GENERAL PUBLIC LICENSE license](./LICENSE).
