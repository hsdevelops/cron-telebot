from http import HTTPStatus
from fastapi import Request, Response
from telegram import Update
import uvicorn
from api import app
from common import log

# For bot webhook
@app.post("/")
async def process_update(request: Request):
    ptb = request.app.state.ptb
    req = await request.json()
    update = Update.de_json(req, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)


if __name__ == "__main__":
    # Instructions for how to set up local webhook at https://dev.to/ibrarturi/how-to-test-webhooks-on-your-localhost-3b4f
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log.log_config)
