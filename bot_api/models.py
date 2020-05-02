from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Schedule(Base):
    __tablename__ = table_name

    when = Column("when", Date, primary_key=True, autoincrement=False)
    event = Column("event", String) 
    who = Column("who", String)
    what = Column("what", String)
