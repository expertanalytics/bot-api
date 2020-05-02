from typing import List
from datetime import date

from pydantic import BaseModel


class EventBase(BaseModel):
    when: date
    event_type: str = None


class EventCreate(EventBase):
    pass


class Event(EventBase):
    who: str = None
    what: str = None

    class Config:
        orm_mode = True
