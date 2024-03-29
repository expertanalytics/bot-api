import os
import sys

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import yaml

from bot_api.models import Event


database_url = os.environ.get("DATABASE_URL")
if len(sys.argv) > 1:
    schedules_filepath = sys.argv[1]
else:
    sys.exit("Usage: python yaml_to_db.py /path/to/schedules.yaml")

table_name = "schedule"

if __name__ == "__main__":
    engine = create_engine(database_url, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    conn = engine.connect()

    with open(schedules_filepath, "rb") as fs:
        schedule_dict = yaml.safe_load(fs)

    for x in session.query(Event).all():
        print(x.when, x.event_type, x.what, x.who)

    values = [
        Event(event_type=vals["event"], when=date, what=vals["what"], who=vals["who"])
        for date, vals in schedule_dict.items()
    ]

    session.add_all(values)
    session.commit()
