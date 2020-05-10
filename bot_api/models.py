from sqlalchemy import (Column, Integer, String, Date)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    when = Column("when", Date, primary_key=True, autoincrement=False)
    event_type = Column("event_type", String) 
    who = Column("who", String)
    what = Column("what", String)
