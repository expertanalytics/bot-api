from datetime import date

from sqlalchemy.orm import Session

from . import models, schemas


def create_event(db: Session, when: date, event_type: str):
    db_event = models.Event(when=when, event_type=event_type)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def remove_event(db: Session, when: date):
    db_event = db.query(models.Event).filter(models.Event.when == when).first()
    db.delete(db_event)
    db.commit()
    return db_event


def get_event_by_date(db: Session, when: str):
    return db.query(models.Event).filter(models.Event.when == when).first()


def get_closest_event(db: Session, when: str):
    return db.query(models.Event).filter(
            models.Event.when >= when).order_by(
                    models.Event.when).limit(1).first()


def get_upcoming_events(db: Session, when: str):
    return db.query(models.Event).filter(
            models.Event.when >= when).order_by(
                    models.Event.when).all()
