from http import HTTPStatus
from fastapi import Request, Response
from telegram import Update
import uvicorn
from bot.ptb import ptb
from api import app

# For bot webhook
@app.post("/")
async def process_update(request: Request):
    req = await request.json()
    update = Update.de_json(req, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)


# Run bot only
if __name__ == "__main__":
    # Instructions for how to set up local webhook at https://dev.to/ibrarturi/how-to-test-webhooks-on-your-localhost-3b4f
    uvicorn.run(app, host="0.0.0.0", port=8000)
