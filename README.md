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

3. Start services by running `python main.py`. You may toggle webhook/polling by setting/unsetting BOTHOST in [config.py](./config.py).

## Running in production
1. Configure environment variables. See [config.py](./config.py) for the required environment variables and how you can get them.
2. Entrypoint is `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --timeout 60`. No need to run bot and api separately.

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=cron-telebot&type=git&repository=hsdevelops%2Fcron-telebot&branch=main&run_command=gunicorn+main%3Aapp+-w+1+-k+uvicorn.workers.UvicornWorker+--timeout+60&instance_type=free&regions=fra&instances_min=0&autoscaling_sleep_idle_delay=3900&env%5BBOTHOST%5D=https%3A%2F%2Frequired-kariotta-hs-develops-fc48c295.koyeb.app&env%5BINFLUXDB_TOKEN%5D=3tI-RiLphNmnWXW71CPxw4gnvdDK98K82S5u-eqa2xzwfhT1ejeO9kcD3J113SmbAvaQfoVW1bwAKnTBViM9jA%3D%3D&env%5BMONGODB_CONNECTION_STRING%5D=mongodb%2Bsrv%3A%2F%2Fadmin%3Ay0valDcc9lj3abWk%40cluster0.owoprdx.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority&env%5BTELEGRAM_BOT_TOKEN%5D=5175096759%3AAAG3uu602aVQpZBWMwfHtMNOgNWHD2s9xo0)

## Contributing

If you're looking for a way to contribute, you can scan through our existing issues for something to work on. See [the contributing guide](./CONTRIBUTING.md) for detailed instructions on how to get started with our project.

## License

The project is licensed under a [GNU GENERAL PUBLIC LICENSE license](./LICENSE).
