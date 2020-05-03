import json
import os
import datetime
from datetime import date

import requests
from fastapi import (FastAPI, Request, Form, Depends, HTTPException) 
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import dateparser

from . import crud, models, schemas
from .database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")


@app.post("/api/v1.0/events")
async def events(request: Request):
    req = await request.json()
    print(json.dumps(req, sort_keys=True, indent=4))
    if "challenge" in req:
        return {"challenge": req["challenge"]}

    response = {
            "token": SLACK_BOT_TOKEN,
            "channel": req["event"]["channel"],
            "text": "hello world"
            }
    
    requests.post(POST_MESSAGE_URL, data=response)


@app.post("/api/v1.0/schedule")
async def schedule(text: str = Form(...)):

    args = models.get_args_from_request(text)

    if not args.who or not args.what or not args.what:
        return {
                "text": models.default_responses["USAGE_ERROR"],
                "response_type": "ephemeral"}

    when = dateparser.parse(args.when) 
    if not when:
        return models.default_responses["DATE_ERROR"]

   
    return "Scheduling is not yet setup."



@app.post("/api/v1.0/add")
async def create_event(text: str = Form(...), db: Session = Depends(get_db)):

    args = models.get_args_from_request(text)

    when = dateparser.parse(
            args.when, 
            settings={'STRICT_PARSING': True})


    if args.event not in models.event_types:
        return models.default_responses["MISSING_EVENT_ERROR"]

    if not when:
        return models.default_responses["DATE_ERROR"]

    when = when.date()
    if datetime.datetime.now().date() > when:
        return models.default_responses["PAST_DATE_ERROR"]
    
    db_event = crud.get_event_by_date(db, when=when)
    if db_event:
        return models.default_responses["EXISTING_DATE_ERROR"]

    crud.create_event(
            db=db, event_type=args.event, when=when)

    return (f"{models.prettify_date(when)}"
            f" successfully added to the schedule.")


@app.post("/api/v1.0/remove")
async def delete_event(
        text: str = Form(...), 
        db: Session = Depends(get_db)):

    args = models.get_args_from_request(text)
    when = dateparser.parse(
            args.when, 
            settings={'STRICT_PARSING': True})

    if not when:
        return "Error: Unable to parse date."

    when = when.date()
    if datetime.datetime.now().date() > when:
        return "Error: Date is in the past."
    
    db_event = crud.get_event_by_date(db, when=when)
    if not db_event:
        return "Error: Date not in schedule.",

    crud.remove_event(
            db=db, when=when)

    return (f"{models.prettify_date(when)} "
            f"successfully removed from the schedule.")


@app.post("/api/v1.0/next")
async def read_event(db: Session = Depends(get_db)):
    db_event = crud.get_closest_event(db, when=date.today())
    if db_event is None or not db_event.who:
        return models.default_responses["NO_EVENTS"]

    return models.get_formatted_event(db_event)


@app.post("/api/v1.0/upcoming")
async def read_events(db: Session = Depends(get_db)):
    db_events = crud.get_upcoming_events(db, when=date.today())
    if db_events is None:
        return models.default_responses["NO_EVENTS"]

    return "\n".join(
            [models.get_formatted_event(event) for event in db_events])
