from sqlalchemy import (
    create_engine, Column, Integer, SmallInteger,
    String, DateTime, Sequence, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry

# Base class for ORM models
Base = declarative_base()

# -------------------------
# TABLE DEFINITIONS
# -------------------------

class NametoUID(Base):
    __tablename__ = "nametouid"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(30), nullable=False)


class RealtimeLocationData(Base):
    __tablename__ = "realtime_location_data"

    id = Column(SmallInteger, primary_key=True, nullable=False)
    geom = Column(Geometry("POINT"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)


class UserEventSessions(Base):
    __tablename__ = "user_event_sessions"

    session_id = Column(
        Integer,
        Sequence("user_event_sessions_session_id_seq"),
        primary_key=True,
        nullable=False
    )
    id = Column(Integer, nullable=False)        # user id
    event_id = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=False), nullable=False)
    end_time = Column(DateTime(timezone=False), nullable=False)
    duration_sec = Column(
        Integer,
        default=func.extract("epoch", (func.cast(func.now(), DateTime) - func.cast(func.now(), DateTime)))
    )


class Events(Base):
    __tablename__ = "events"

    event_id = Column(
        Integer,
        Sequence("events_event_id_seq"),
        primary_key=True,
        nullable=False
    )
    start_time = Column(DateTime(timezone=False), nullable=False)
    end_time = Column(DateTime(timezone=False), nullable=False)
    duration_sec = Column(
        Integer,
        default=func.extract("epoch", (func.cast(func.now(), DateTime) - func.cast(func.now(), DateTime)))
    )
    location_geom = Column(Geometry("POINT"))

# -------------------------
# DATABASE CONNECTION
# -------------------------

# adjust connection string for your setup
engine = create_engine("postgresql+psycopg2://postgres:WAKE419!@100.123.22.7:5432/demoDB")

# Create tables if they don’t already exist
Base.metadata.create_all(engine)

# Session factory
SessionLocal = sessionmaker(bind=engine)
