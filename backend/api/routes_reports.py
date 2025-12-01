from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import text

from backend.database_engine import (
    engine, 
    UserEventSessions, 
    Events, 
    RealtimeLocationData, 
    NametoUID
)
from sqlalchemy import func

router = APIRouter(tags=["reports"])

def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

@router.get("/{user_id}")
def full_report(user_id: int, db: Session = Depends(get_db)):
    return {
        "user_id": user_id,
        "name": get_user_name(db, user_id),
        "socialization": socialization_report(db, user_id),
        "events": event_report(db, user_id),
        "mobility": mobility_report(db, user_id),
        "butterfly": butterfly_report(db, user_id),
        "friends": friend_report(db, user_id)
    }

def get_user_name(db, user_id):
    user = db.query(NametoUID).filter(NametoUID.id == user_id).first()
    return user.name if user else "Unknown User"

def socialization_report(db, user_id):
    now = datetime.now()

    def duration_since(dt):
        return (
            db.query(
                func.sum(
                    func.extract("epoch", UserEventSessions.end_time - UserEventSessions.start_time)
                )
            )
            .filter(
                UserEventSessions.id == user_id,
                UserEventSessions.end_time >= dt
            )
            .scalar() or 0
        ) / 3600  # return hours

    return {
        "today_hours": round(duration_since(now.replace(hour=0, minute=0, second=0, microsecond=0)), 2),
        "week_hours": round(duration_since(now - timedelta(days=7)), 2),
        "month_hours": round(duration_since(now - timedelta(days=30)), 2)
    }

def event_report(db, user_id):
    sql = """
        SELECT 
            e.event_id,
            e.start_time,
            e.end_time,
            (
                SELECT COUNT(DISTINCT id)
                FROM user_event_sessions
                WHERE event_id = e.event_id
            ) AS participants
        FROM user_event_sessions ue
        JOIN events e ON ue.event_id = e.event_id
        WHERE ue.id = :uid
        ORDER BY e.start_time DESC;
    """
  
    rows = db.execute(text(sql), {"uid": user_id}).fetchall()

    # Remove duplicates by event_id
    events_map = {}
    for r in rows:
        events_map[r.event_id] = r

    unique_rows = list(events_map.values())

    # Format output just like before
    return [
        {
            "event_id": r.event_id,
            "start": str(r.start_time),
            "end": str(r.end_time),
            "participants": r.participants
        }
        for r in unique_rows
    ]

def mobility_report(db, user_id):
    rows = (
        db.query(
            RealtimeLocationData.x_coordinate,
            RealtimeLocationData.y_coordinate,
            RealtimeLocationData.recorded_at
        )
        .filter(RealtimeLocationData.id == user_id)
        .order_by(RealtimeLocationData.recorded_at)
        .all()
    )

    points = [
        {"x": r.x_coordinate, "y": r.y_coordinate, "timestamp": str(r.recorded_at)}
        for r in rows
    ]

    # -------- GRID BUCKET SIZE --------
    BUCKET = 20  # group into 20x20 unit squares

    heatmap = {}
    for p in points:
        bx = round(p['x'] / BUCKET) * BUCKET
        by = round(p['y'] / BUCKET) * BUCKET
        key = f"{bx},{by}"
        heatmap[key] = heatmap.get(key, 0) + 1

    zones = list(heatmap.keys())

    return {
        "zones_visited": zones,
        "heatmap": heatmap,   # <----- NEW
        "movement_path": points
    }


def butterfly_report(db, user_id):
    total_minutes = (
        db.query(func.sum(
            func.extract("epoch", UserEventSessions.end_time - UserEventSessions.start_time)
        ))
        .filter(UserEventSessions.id == user_id)
        .scalar() or 0
    ) / 60

    status = "Isolated" if total_minutes < 30 else "Moderate" if total_minutes < 120 else "Social"

    return {
        "total_minutes": round(total_minutes, 1),
        "isolation_level": status
    }

def friend_report(db, user_id):
    sql = """
        SELECT 
            CASE WHEN ue.id = :uid THEN u2.id ELSE ue.id END AS other_user,
            SUM(EXTRACT(EPOCH FROM (LEAST(ue.end_time, u2.end_time) - GREATEST(ue.start_time, u2.start_time)))) AS overlap
        FROM user_event_sessions ue
        JOIN user_event_sessions u2 ON ue.event_id = u2.event_id
        WHERE ue.id = :uid AND u2.id != :uid
        GROUP BY other_user
        ORDER BY overlap DESC
        LIMIT 3;
    """

    rows = db.execute(text(sql), {"uid": user_id}).fetchall()
    results = []

    for r in rows:
        name = db.query(NametoUID.name).filter(NametoUID.id == r.other_user).scalar()
        results.append({
            "user_id": r.other_user,
            "name": name,
            "overlap_minutes": round((r.overlap or 0) / 60, 2)
        })

    return results
