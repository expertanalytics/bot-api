import json
import os
import datetime
from datetime import date
import logging

import requests
from fastapi import (FastAPI, Request, Form, Depends) 
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from . import crud, models, schemas
from .database import engine, SessionLocal
from .errors import *


models.Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = logging.getLogger(__name__)

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
FAGDAG_CHANNEL_ID = "C0YMPPHT6"
TEST_CHANNEL_ID = "CP3SWEVHT"
PING_ENDPOINT_URL = "http://slackbot-api.herokuapp.com/api/v1.0/ping"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# Keep Heroku server alive
def ping_server():
    req = requests.get(PING_ENDPOINT_URL)
    logger.info(f"Pinged server, response: {req}")


def post_msg_if_no_presenter():
    db = next(get_db())
    channel = TEST_CHANNEL_ID
    # channel = FAGDAG_CHANNEL_ID
    message = {
            "channel": channel,
            "text": "",
            "token": SLACK_BOT_TOKEN,
            }

    now = datetime.datetime.now().date()
    db_event = crud.get_closest_event(db, when=datetime.date.today())

    if not db_event.when:
        return

    td = db_event.when - now
    if db_event.who:
        if td < datetime.timedelta(days=7):
            message["text"] = models.list_next_event(None)
            return requests.post(POST_MESSAGE_URL, data=message)
        return

    # If what but not who: event is cancelled so we return
    if db_event.what and not db_event.who:
        return

    if td > datetime.timedelta(days=14):
        return
    elif td > datetime.timedelta(days=7):
        message["text"] = models.default_responses["CALL_TO_ACTION"].format(
                models.prettify_date(db_event.when), "in one week")

        return requests.post(POST_MESSAGE_URL, data=message)
        
    message["text"] = models.default_responses["CALL_TO_ACTION"].format(
            models.prettify_date(db_event.when), "tonight")

    return requests.post(POST_MESSAGE_URL, data=message)


@app.get("/api/v1.0/ping")
async def ping():
    return 200


@app.post("/api/v1.0/events")
async def events(request: Request):
    req = await request.json()
    logger.info(json.dumps(req, sort_keys=True, indent=4))
    if "challenge" in req:
        return {"challenge": req["challenge"]}


@app.post("/api/v1.0/command")
async def command(text: str = Form(...), db: Session = Depends(get_db)):
    """Executes bot command if the command is known."""

    if not text:
        return models.default_responses["INVALID_COMMAND"] 

    try:
        args = models.get_args_from_request(text)
    except ArgumentError as e:
        return {"text": str(e), "response_type": "ephemeral"}
    
    # Switch a potential shorthand with the corresponding command
    cmd = models.shorthands.get(args.command, args.command)

    was_raised = True
    try:
        response = models.commands[cmd]["command"](args, db)
        was_raised = False
    except KeyError as e:
        response = models.default_responses["INVALID_COMMAND"] 
    except UsageError:
        response = f"Usage error: {models.commands[cmd]['usage']}"
    except InvalidDateError:
        response = models.default_responses["INVALID_DATE_ERROR"]
    except InvalidEventError:
        response = models.default_responses["INVALID_EVENT_ERROR"]
    except MissingDateError:
        response = models.default_responses["MISSING_DATE_ERROR"]
    except PastDateError:
        response = models.default_responses["PAST_DATE_ERROR"]
    except ExistingDateError:
        response = models.default_responses["EXISTING_DATE_ERROR"]
    except AlreadyScheduledError:
        response = models.default_responses["ALREADY_SCHEDULED_ERROR"]
    except AlreadyClearedError:
        response = models.default_responses["ALREADY_CLEARED_ERROR"]
    except AlreadyCancelledError:
        response = models.default_responses["ALREADY_CANCELLED_ERROR"]


    response_type = "ephemeral" if args.silent or was_raised else "in_channel"
    return {"text": response, "response_type": response_type}


sched = BackgroundScheduler()
sched.add_job(ping_server, trigger="cron", minute="*/25")
# sched.add_job(post_msg_if_no_presenter, trigger="cron", day_of_week=3, hour=12)
sched.add_job(post_msg_if_no_presenter, trigger="cron", second="*/20")
sched.start()
