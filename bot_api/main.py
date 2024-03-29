import json
import os
import time
import hmac
import hashlib
import datetime
import logging

import requests
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from bot_api import crud, commands, models
from bot_api.database import engine, SessionLocal
from bot_api.errors import (
    AlreadyCancelledError,
    AlreadyClearedError,
    AlreadyScheduledError,
    ArgumentError,
    ExistingDateError,
    InvalidDateError,
    InvalidEventError,
    MissingDateError,
    PastDateError,
    UsageError,
)


models.Base.metadata.create_all(bind=engine)

app = FastAPI(use_reloader=False)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename="/home/c-bot/bot_log.log", filemode="w")

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SET_TOPIC_URL = "https://slack.com/api/conversations.setTopic"
CHANNEL_INFO_URL = "https://slack.com/api/conversations.info"

FAGDAG_CHANNEL_ID = "C0YMPPHT6"
TEST_CHANNEL_ID = "CP3SWEVHT"
CURRENT_CHANNEL = FAGDAG_CHANNEL_ID

PING_ENDPOINT_URL = "http://cbot.xal.no/api/v1.0/ping"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_BOT_OAUTH_TOKEN = os.environ.get("SLACK_BOT_OAUTH_TOKEN")
SLACK_USER_TOKEN = os.environ.get("SLACK_USER_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def validate_request(request_body, timestamp, slack_signature):
    if not timestamp or not slack_signature:
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        # The request timestamp is more than five minutes from local time.
        # It could be a replay attack, so let's ignore it.
        return False

    if SLACK_SIGNING_SECRET is None:
        raise ValueError("SLACK_SIGNING_SECRET must be set")

    sig_basestring = f"v0:{timestamp}:{request_body.decode()}".encode("utf-8")
    computed_hash = hmac.new(
        bytes(SLACK_SIGNING_SECRET, encoding="utf-8"), sig_basestring, digestmod=hashlib.sha256
    ).hexdigest()
    my_signature = f"v0={computed_hash}"

    if hmac.compare_digest(my_signature, slack_signature):
        return True
    else:
        logger.error(f"Request failed: {my_signature} != {slack_signature}")
        return False


# Keep Heroku server alive
def ping_server():
    req = requests.get(PING_ENDPOINT_URL)
    logger.info(f"Pinged server, response: {req}")


def post_msg_if_no_presenter():
    db = SessionLocal()
    db_event = crud.get_closest_event(db, when=datetime.date.today())
    if db_event is None:
        return

    channel = CURRENT_CHANNEL
    message = {
        "channel": channel,
        "text": "",
        "token": SLACK_BOT_OAUTH_TOKEN,
    }

    now = datetime.datetime.now().date()
    if not db_event.when:
        return

    td = db_event.when - now
    if db_event.who:
        if td < datetime.timedelta(days=7):
            message["text"] = commands.list_next_event(None)
            return requests.post(POST_MESSAGE_URL, data=message)
        return

    # If what but not who: event is cancelled so we return
    if db_event.what and not db_event.who:
        return

    if td > datetime.timedelta(days=14):
        return
    elif td > datetime.timedelta(days=7):
        message["text"] = commands.default_responses["CALL_TO_ACTION"].format(
            commands.prettify_date(db_event.when), "in one week"
        )

        return requests.post(POST_MESSAGE_URL, data=message)

    message["text"] = commands.default_responses["CALL_TO_ACTION"].format(
        commands.prettify_date(db_event.when), "tonight"
    )

    db.close()
    return requests.post(POST_MESSAGE_URL, data=message)


def set_new_topic_if_not_set():
    db = SessionLocal()
    db_event = crud.get_closest_event(db, when=datetime.date.today())
    if db_event is None:
        return

    channel = CURRENT_CHANNEL

    if db_event is None or not bool(db_event.who) or not bool(db_event.when):
        new_channel_topic = "No formiddag events scheduled :("
    else:
        new_channel_topic = commands.get_formatted_event(db_event)

    message = {
        "token": SLACK_BOT_OAUTH_TOKEN,
        "topic": new_channel_topic,
        "channel": channel,
    }

    channel_info = requests.post(CHANNEL_INFO_URL, data=message).json()
    if channel_info["channel"]["topic"]["value"] != new_channel_topic:
        return requests.post(SET_TOPIC_URL, data=message)


@app.get("/api/v1.0/ping")
async def ping():
    return 200


@app.post("/api/v1.0/events")
async def events(request: Request):
    req = await request.json()
    logger.info(json.dumps(req, sort_keys=True, indent=4))
    if "challenge" in req:
        return {"challenge": req["challenge"]}


@app.post("/api/v1.0/upcoming")
async def upcoming(db: Session = Depends(get_db)):
    """Endpoint for the /upcoming command"""
    return {"text": commands.commands["upcoming"]["command"](None, db), "response_type": "ephemeral"}


@app.post("/api/v1.0/command")
async def command(request: Request, db: Session = Depends(get_db)):
    """Endpoint for general bot commands"""

    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    request_body = await request.body()
    form = await request.form()
    text = form.get("text")

    if not text:
        return commands.default_responses["INVALID_COMMAND"]

    if not validate_request(request_body, timestamp, slack_signature):
        return {"text": "Invalid request."}

    try:
        args = commands.get_args_from_request(text)
    except ArgumentError as e:
        return {"text": str(e), "response_type": "ephemeral"}

    # Switch a potential shorthand with the corresponding command
    cmd = commands.shorthands.get(args.command, args.command)

    was_raised = True
    try:
        response = commands.commands[cmd]["command"](args, db)
        was_raised = False
    except KeyError:
        response = commands.default_responses["INVALID_COMMAND"]
    except UsageError:
        response = f"Usage error: {commands.commands[cmd]['usage']}"
    except InvalidDateError:
        response = commands.default_responses["INVALID_DATE_ERROR"]
    except InvalidEventError:
        response = commands.default_responses["INVALID_EVENT_ERROR"]
    except MissingDateError:
        response = commands.default_responses["MISSING_DATE_ERROR"]
    except PastDateError:
        response = commands.default_responses["PAST_DATE_ERROR"]
    except ExistingDateError:
        response = commands.default_responses["EXISTING_DATE_ERROR"]
    except AlreadyScheduledError:
        response = commands.default_responses["ALREADY_SCHEDULED_ERROR"]
    except AlreadyClearedError:
        response = commands.default_responses["ALREADY_CLEARED_ERROR"]
    except AlreadyCancelledError:
        response = commands.default_responses["ALREADY_CANCELLED_ERROR"]

    response_type = "ephemeral" if args.silent or was_raised else "in_channel"
    return {"text": response, "response_type": response_type}


sched = BackgroundScheduler(timezone="Europe/Oslo")
# sched.add_job(ping_server, trigger="cron", minute="*/5")
sched.add_job(post_msg_if_no_presenter, trigger="cron", day_of_week=3, hour=12)
sched.add_job(set_new_topic_if_not_set, trigger="cron", day="*", hour="*/10", minute=30)
sched.start()
