import json
import os
import datetime
from datetime import date

import requests
from fastapi import (FastAPI, Request, Form, Depends, HTTPException) 
from fastapi.responses import JSONResponse
        
from sqlalchemy.orm import Session

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
async def schedule(*, channel_id: str = Form(...)):

    response = {
            "response_type": "in_channel",
            "text": "Scheduling is not yet setup."
            }
   
    return response
@app.post("/api/v1.0/next", response_model=schemas.Event)
def read_event(db: Session = Depends(get_db)):
    db_event = crud.get_closest_event(db, when=date.today())
@app.post("/api/v1.0/next")
async def read_event(db: Session = Depends(get_db)):
    db_event = crud.get_closest_event(db, when=when)
    if db_event is None or not db_event.who:
        return JSONResponse({
            "text": "No upcoming events.",
            "response_type": "ephemeral"})

    return models.get_formatted_event(db_event)


@app.post("/api/v1.0/upcoming")
async def read_events(db: Session = Depends(get_db)):
    db_events = crud.get_upcoming_events(db, when=date.today())
    if db_events is None:
        return JSONResponse({
            "text": "No upcoming events.",
            "response_type": "ephemeral"})

    return "\n".join([models.get_formatted_event(event) for event in db_events])
