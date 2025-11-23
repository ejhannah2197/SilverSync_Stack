from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database_engine import (
    engine,
    NametoUID,
    UserEventSessions,
    Events,
    RealtimeLocationData
)
from sqlalchemy import func, text
from datetime import datetime, timedelta

router = APIRouter()

# -----------------------------
# DB SESSION DEPENDENCY
# -----------------------------
def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# LOOKUP USER ID BY NAME
# -----------------------------
@router.get("/lookup_user_id")
def lookup_user_id(name: str, db: Session = Depends(get_db)):
    user = db.query(NametoUID).filter(NametoUID.name.ilike(f"%{name}%")).first()
    if not user:
        return {"error": "User not found"}
    return {"user_id": user.id}


# -----------------------------
# USER INTERACTION LOOKUP
# -----------------------------
@router.get("/users")
def get_user_data(user_id: int, db: Session = Depends(get_db)):

    # Total interaction time
    total_time = (
        db.query(func.sum(func.extract('epoch', UserEventSessions.end_time - UserEventSessions.start_time)))
        .filter(UserEventSessions.id == user_id)
        .scalar()
    ) or 0

    # Last 3 interactions
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
            "x_event": event.x_event if event else None,
            "y_event": event.y_event if event else None,
        })

    return {
        "user_id": user_id,
        "total_interaction_minutes": round(total_time / 60, 2),
        "recent_interactions": results,
    }


# -----------------------------
# ACTIVE DEVICES (LAST HOUR)
# -----------------------------
@router.get("/active-devices")
def active_devices(db: Session = Depends(get_db)):
    one_hour_ago = datetime.now() - timedelta(hours=1)

    active_count = (
        db.query(func.count(func.distinct(RealtimeLocationData.id)))
            .filter(RealtimeLocationData.recorded_at >= one_hour_ago)
            .scalar()
    )

    return {"active_devices": active_count or 0}


# -----------------------------
# EVENTS TODAY
# -----------------------------
@router.get("/events-today")
def events_today(db: Session = Depends(get_db)):

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    event_count = (
        db.query(func.count(Events.event_id))
        .filter(Events.start_time >= today_start)
        .scalar()
    )

    return {"events_today": event_count or 0}


# -----------------------------
# SYSTEM STATUS
# -----------------------------
@router.get("/system-status")
def system_status(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1;"))
        return {"status": "online"}
    except Exception:
        return {"status": "offline"}


# -----------------------------
# LOW INTERACTION USERS
# -----------------------------
@router.get("/low-interaction")
def get_low_interaction_users(threshold_minutes: int = Query(5), db: Session = Depends(get_db)):

    # Build total-time subquery
    subq = (
        db.query(
            UserEventSessions.id.label("user_id"),
            func.sum(func.extract('epoch', UserEventSessions.end_time - UserEventSessions.start_time))
                .label("total_time")
        )
        .group_by(UserEventSessions.id)
        .subquery()
    )

    # Join with NametoUID to get names
    results = (
        db.query(
            NametoUID.name,
            subq.c.user_id,
            subq.c.total_time
        )
        .join(NametoUID, NametoUID.id == subq.c.user_id)
        .filter(subq.c.total_time < threshold_minutes * 60)
        .order_by(subq.c.total_time.asc())
        .all()
    )

    return [
        {
            "user_id": r.user_id,
            "name": r.name,
            "total_minutes": round((r.total_time or 0) / 60, 2)
        }
        for r in results
    ]
