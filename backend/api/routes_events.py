from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database_engine import engine, Events, UserEventSessions
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/events", tags=["events"])

# Dependency for DB sessions
def get_db():
    from sqlalchemy.orm import Session
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_recent_events(db: Session = Depends(get_db)):
    """Return the last 50 events with participant counts."""
    query = (
        db.query(
            Events.event_id,
            Events.start_time,
            Events.end_time,
            func.count(UserEventSessions.id).label("user_count"),
        )
        .join(UserEventSessions, Events.event_id == UserEventSessions.event_id)
        .group_by(Events.event_id)
        .order_by(Events.start_time.desc())
        .limit(50)
    )
    results = query.all()

    # Convert to dicts for JSON serialization
    return [
        {
            "event_id": r.event_id,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "user_count": r.user_count,
        }
        for r in results
    ]
