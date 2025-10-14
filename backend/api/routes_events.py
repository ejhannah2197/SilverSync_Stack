from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database_engine import engine, NametoUID, UserEventSessions, Events
from sqlalchemy import func

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

    low_users = db.query(subq.c.id, subq.c.total_time).filter(subq.c.total_time < threshold_minutes * 60).all()

    return [{"user_id": u.id, "total_minutes": round((u.total_time or 0) / 60, 2)} for u in low_users]
