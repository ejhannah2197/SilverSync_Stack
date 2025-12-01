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

    # Total interaction time from new column
    total_hours = (
        db.query(func.coalesce(func.sum(UserEventSessions.duration_hours), 0.0))
        .filter(UserEventSessions.id == user_id)
        .scalar()
    )

    # Last 3 interactions
    recent_interactions = (
        db.query(
            UserEventSessions,
            Events.x_event,
            Events.y_event
        )
        .join(Events, Events.event_id == UserEventSessions.event_id, isouter=True)
        .filter(UserEventSessions.id == user_id)
        .order_by(UserEventSessions.end_time.desc())
        .limit(3)
        .all()
    )

    # Format interactions
    results = []
    for row in recent_interactions:
        session = row[0]
        x_event = row[1]
        y_event = row[2]

        results.append({
            "event_id": session.event_id,
            "start_time": str(session.start_time),
            "end_time": str(session.end_time),
            "duration_hours": session.duration_hours,
            "duration_minutes": round(session.duration_hours * 60),
            "x_event": x_event,
            "y_event": y_event,
        })

    return {
        "user_id": user_id,
        "total_hours": round(total_hours, 2),
        "total_minutes": round(total_hours * 60, 2),
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
def get_low_interaction_users(threshold_hours: float = Query(0.01), db: Session = Depends(get_db)):

    subq = (
        db.query(
            UserEventSessions.id.label("user_id"),
            func.coalesce(func.sum(UserEventSessions.duration_hours), 0.0).label("total_hours"),
        )
        .group_by(UserEventSessions.id)
        .subquery()
    )

    # VERY IMPORTANT: force threshold_hours to float
    threshold = float(threshold_hours)

    results = (
        db.query(
            NametoUID.name,
            subq.c.user_id,
            subq.c.total_hours,
        )
        .join(NametoUID, NametoUID.id == subq.c.user_id)
        .filter(subq.c.total_hours < threshold)        # <-- MUST be a comparison
        .order_by(subq.c.total_hours.asc())
        .all()
    )

    return [
        {
            "user_id": r.user_id,
            "name": r.name,
            "total_hours": round(r.total_hours, 2),
        }
        for r in results
    ]



# -----------------------------
# LIST OF ALL USERS
# -----------------------------
@router.get("/all-users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(NametoUID).order_by(NametoUID.name.asc()).all()
    return [{"id": u.id, "name": u.name} for u in users]
