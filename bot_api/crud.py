import datetime
from datetime import date, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from . import models, schemas


def _nearest(items, pivot):
    """Returns the item x closest to the pivot, for example date times."""
    if not items:
        return None

    return min(items, key=lambda x: abs(x.when - pivot))


def create_event(db: Session, when: date, event_type: str):
    db_event = models.Event(when=when, event_type=event_type)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


def remove_event(db: Session, when: date):
    db_event = get_event_by_date(db, when)
    db.delete(db_event)
    db.commit()

    return db_event


def update_event(db: Session, db_event: models.Event, who: str, what: str):
    db_event.who = who
    db_event.what = what
    db.commit()

    return db_event


def get_event_by_date(db: Session, when: str):
    return db.query(models.Event).filter(models.Event.when == when).first()


def get_closest_event(db: Session, when: str):
    now = datetime.datetime.now().date()

    greater = db.query(models.Event).filter(
            models.Event.when >= when).order_by(
                    models.Event.when.asc()).limit(1).first()

    lesser = db.query(models.Event).filter(
        and_(models.Event.when <= when, models.Event.when >= now)).order_by(models.Event.when.desc()).limit(1).first()

    items = [x for x in (lesser, greater) if x]
    db_event = _nearest(items, when)

    return db_event


def get_upcoming_events(db: Session, when: str):
    return db.query(models.Event).filter(models.Event.when >= when).order_by(models.Event.when).all()
