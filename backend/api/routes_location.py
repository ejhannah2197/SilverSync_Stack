from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database_engine import engine, RealtimeLocationData
from datetime import datetime, timedelta

router = APIRouter(prefix="/locations", tags=["locations"])

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
# GET RECENT LOCATIONS (LAST MIN)
# -----------------------------
@router.get("/")
def get_recent_locations(db: Session = Depends(get_db)):
    """Return recent location samples (past minute)."""

    since = datetime.utcnow() - timedelta(minutes=1)

    query = (
        db.query(
            RealtimeLocationData.id,
            RealtimeLocationData.recorded_at,
            RealtimeLocationData.x_coordinate,
            RealtimeLocationData.y_coordinate
        )
        .filter(RealtimeLocationData.recorded_at >= since)
        .order_by(RealtimeLocationData.recorded_at.desc())
        .limit(1000)
    )

    results = query.all()

    return [
        {
            "id": r.id,
            "recorded_at": r.recorded_at,
            "x": r.x_coordinate,
            "y": r.y_coordinate
        }
        for r in results
    ]
