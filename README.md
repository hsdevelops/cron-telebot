# Recurring Messages

Recurring Messages ([@cron_telebot](https://t.me/cron_telebot)) is a Telegram bot that schedules recurring Telegram messages. :sparkles:

Refer to our [user guide](https://github.com/hsdevelops/cron-telebot/wiki/User-Guide) for usage instructions.

## Noteworthy files
1. [main.py](./main.py) — telegram bot, to add/delete/view the recurring jobs
2. [api.py](./api.py) — fast api app, ping the endpoint to trigger check and send all required messages
3. [config.py](./config.py) — all the configurations you need to change for the bot
4. [mongo.py](./database/mongo.py) — handles interaction with the mongo database

## Prerequisites
1. Telegram bot created with [@botfather](https://telegram.me/botfather)
2. Existing MongoDB

Note: The latest version does not support Google Sheets as a database anymore. Please refer to the [gsheets branch](https://github.com/hsdevelops/cron-telebot/tree/gsheets) (no longer maintained) if you would like to use Google Sheets for your database.

## Running locally

1. Configure environment variables. See [config.py](./config.py) for the required environment variables and how you can get them.

2. Install Python and pip and set up virtual environment. 
   ```
   virtualenv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Start services. Run `python main.py` to start the telegram bot. On another terminal, run `python api.py` to initialize the FastAPI endpoints (base path is `/api`).

## Running in production
1. Configure environment variables. See [config.py](./config.py) for the required environment variables and how you can get them.
   * Remember to set the ENV environment variable to any value of your choice (e.g. `dev`, `uat`, `prod`)
2. Entrypoint is `gunicorn main:app -k uvicorn.workers.UvicornWorker --timeout 60`. No need to run bot and api separately.

## Contributing

If you're looking for a way to contribute, you can scan through our existing issues for something to work on. See [the contributing guide](./CONTRIBUTING.md) for detailed instructions on how to get started with our project.

## License

The project is licensed under a [GNU GENERAL PUBLIC LICENSE license](./LICENSE).
