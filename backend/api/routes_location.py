from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database_engine import engine, RealtimeLocationData
from datetime import datetime, timedelta

router = APIRouter(prefix="/locations", tags=["locations"])

def get_db():
    from sqlalchemy.orm import Session
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_recent_locations(db: Session = Depends(get_db)):
    """Return recent location samples (past minute)."""
    since = datetime.utcnow() - timedelta(minutes=1)
    query = (
        db.query(
            RealtimeLocationData.id,
            RealtimeLocationData.recorded_at,
            RealtimeLocationData.geom.ST_AsText().label("geom")
        )
        .filter(RealtimeLocationData.recorded_at >= since)
        .order_by(RealtimeLocationData.recorded_at.desc())
        .limit(1000)
    )
    results = query.all()
    return [
        {"id": r.id, "recorded_at": r.recorded_at, "geom": r.geom}
        for r in results
    ]
