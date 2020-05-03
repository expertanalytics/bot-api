import json
import os
import datetime
from datetime import date
import logging

import requests
from fastapi import (FastAPI, Request, Form, Depends) 
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import engine, SessionLocal
from .errors import *


models.Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = logging.getLogger(__name__)

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.post("/api/v1.0/events")
async def events(request: Request):
    req = await request.json()
    logger.info(json.dumps(req, sort_keys=True, indent=4))
    if "challenge" in req:
        return {"challenge": req["challenge"]}

    response = {
            "token": SLACK_BOT_TOKEN,
            "channel": req["event"]["channel"],
            "text": "hello world"
            }
    
    requests.post(POST_MESSAGE_URL, data=response)


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
