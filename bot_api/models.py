from sqlalchemy import (Column, Integer, String, Date)
from sqlalchemy.ext.declarative import declarative_base

from .database import Base


class Event(Base):
    __tablename__ = "events"

    when = Column("when", Date, primary_key=True, autoincrement=False)
    event_type = Column("event_type", String) 
    who = Column("who", String)
    what = Column("what", String)


def prettify_date(date):
    return date.strftime('%a %-d %b')


def get_formatted_event(event: Event):
    is_fagdag = event.event_type == "fagdag"

    if not event.what:
        response = f"{prettify_date(event.when)}: No presentation scheduled."
    elif not event.who:
        return (
                f"{prettify_date(event.when)}: "
                f"Event is cancelled due to {event.what}!")
    else:
        response = (
                f"{prettify_date(event.when)}: "
                f"Presentation *{event.what}* by *{event.who}*.")

    fagdag_tag = f" :busts_in_silhouette: Fagdag" if is_fagdag else ""
    return f">{response}{fagdag_tag}"
