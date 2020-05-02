from fastapi import FastAPI, Request
import json

app = FastAPI()

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


@app.get("/")
async def root():
    return {"Hello": "world"}

@app.post("/events")
async def events(request: Request):
    req = await request.json()
    print(json.dumps(req, indent=4))
    if "challenge" in req:
        return {"challenge": req["challenge"]}

    return {
            "token": SLACK_BOT_TOKEN,
            "channel": req["event"]["channel"],
            "text": "hello world"
            }
