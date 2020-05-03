import os
import sys

import sqlalchemy
from sqlalchemy import (create_engine, Table, Column, Integer, 
        String, Date)
from sqlalchemy.ext.declarative import declarative_base

from bot_api.models import Event

database_url = os.environ.get("DATABASE_URL")
engine = create_engine(database_url, echo=True)
table_name = "events"

if __name__ == "__main__":
    try:
        Event.__table__.drop(engine)
    except sqlalchemy.exc.ProgrammingError as e:
        print(e)

    Event.metadata.create_all(engine)
