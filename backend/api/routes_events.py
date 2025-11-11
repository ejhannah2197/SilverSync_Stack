from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database_engine import engine, NametoUID, UserEventSessions, Events, RealtimeLocationData
from sqlalchemy import func, text, distinct
from datetime import datetime, timedelta
from backend.api.event_detection import run_event_detection, Session

router = APIRouter()

# Dependency to get DB session
def get_db():
    from sqlalchemy.orm import Session
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

@router.get("/lookup_user_id")
def lookup_user_id(name: str, db: Session = Depends(get_db)):
    """
    Return a user's ID based on their name.
    This assumes there's a Users table or similar to look up from.
    """

    user = db.query(NametoUID).filter(NametoUID.name.ilike(f"%{name}%")).first()
    if not user:
        return {"error": "User not found"}
    return {"user_id": user.id}



@router.get("/users")
def get_user_data(user_id: int, db: Session = Depends(get_db)):
    """Return total interaction time and last 3 interactions for a user."""
    total_time = (
        db.query(func.sum(func.extract('epoch', UserEventSessions.end_time - UserEventSessions.start_time)))
        .filter(UserEventSessions.id == user_id)
        .scalar()
    ) or 0

    recent_interactions = (
        db.query(UserEventSessions)
        .filter(UserEventSessions.id == user_id)
        .order_by(UserEventSessions.end_time.desc())
        .limit(3)
        .all()
    )

    results = []
    for r in recent_interactions:
        event = db.query(Events).filter(Events.event_id == r.event_id).first()
        results.append({
            "event_id": r.event_id,
            "start_time": str(r.start_time),
            "end_time": str(r.end_time),
            "location": str(event.location_geom) if event else None
        })

    return {
        "user_id": user_id,
        "total_interaction_minutes": round(total_time / 60, 2),
        "recent_interactions": results
    }

@router.get("/active-devices")
def active_devices(db: Session = Depends(get_db)):
    """Return number of unique devices that have sent data within the last hour."""
    one_hour_ago = datetime.now() - timedelta(hours=1)

    active_count = (
        db.query(func.count(func.distinct(RealtimeLocationData.id)))
        .filter(RealtimeLocationData.recorded_at >= one_hour_ago)
        .scalar()
    )

    return {"active_devices": active_count or 0}


@router.get("/events-today")
def events_today(db: Session = Depends(get_db)):
    """Return total number of events for the current day."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    event_count = (
        db.query(func.count(Events.event_id))
        .filter(Events.start_time >= today_start)
        .scalar()
    )

    return {"events_today": event_count or 0}


@router.get("/system-status")
def system_status(db: Session = Depends(get_db)):
    """Check database connection status."""
    try:
        db.execute(text("SELECT 1;"))
        return {"status": "online"}
    except Exception:
        return {"status": "offline"}
 

@router.get("/low-interaction")
def get_low_interaction_users(threshold_minutes: int = Query(5), db: Session = Depends(get_db)):
    
    """Return users with less than threshold minutes of interaction."""
    subq = (
        db.query(
            UserEventSessions.id,
            func.sum(func.extract('epoch', UserEventSessions.end_time - UserEventSessions.start_time)).label("total_time")
        )
        .group_by(UserEventSessions.id)
        .subquery()
    )

    """ Join with Users to get names """
    results = (
        db.query(NametoUID.name, subq.c.id, subq.c.total_time)
        .join(NametoUID, NametoUID.id == subq.c.id)
        .filter(subq.c.total_time < threshold_minutes * 60)
        .order_by(subq.c.total_time.asc())
        .all()
    )

    return [
        {
            "user_id": r.id,
            "name": r.name,
            "total_minutes": round((r.total_time or 0) / 60, 2)
        }
        for r in results
    ]
    low_users = db.query(subq.c.id, subq.c.total_time).filter(subq.c.total_time < threshold_minutes * 60).all()

    return [{"user_id": u.id, "total_minutes": round((u.total_time or 0) / 60, 2)} for u in low_users]
