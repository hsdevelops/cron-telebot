# Recurring Messages Telebot

Recurring Messages Telebot is a Telegram bot. It's available at https://t.me/cron_telebot. :sparkles:

One project, two deployments/entrypoints. [bot.py](./bot.py) runs the Telegram bot, while [app.py](./app.py) runs the Flask application.

## Noteworthy files
1. [app.py](./app.py) — flask app, ping the endpoint to trigger check and send all required messages
2. [bot.py](./bot.py) — telegram bot, to add/delete/view the recurring jobs
3. [config.py](./config.py) — all the configurations you need to change for the bot
4. [sheets.py](./sheets.py) — handles calls to the gsheet we currently use as our database, and can be easily tweaked to link to other databases like MongoDB.
5. [Procfile](./Procfile) — defines entrypoint for deployment on Heroku

## Running locally

### Prerequisites
1. Python, pip
2. Telegram bot created with [@botfather](https://telegram.me/botfather)
3. A Google Cloud Console Account
4. Existing Google Sheet

### 1. Configure environment variables 
Check out [config.py](./config.py) to find out what environment variables are required and how you can get them.

### 2. Set up virtual environment
```
virtualenv venv
source venv/bin/activate
pip install -r requirements-all.txt
```

### 3. Start services
Run `python bot.py` to start the telegram bot. On another terminal, run `python app.py` to start the Flask endpoint.

## Running in production
More environment variables need to be set. See [config.py](./config.py) and [Procfile](./Procfile) for these variables.

## Contributing

If you're looking for a way to contribute, you can scan through our existing issues for something to work on. See [the contributing guide](./CONTRIBUTING.md) for detailed instructions on how to get started with our project.

## License

The project is licensed under a [GNU GENERAL PUBLIC LICENSE license](./LICENSE).