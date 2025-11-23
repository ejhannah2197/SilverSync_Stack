import pandas as pd
import networkx as nx
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, cast, text, Interval
from fastapi import APIRouter, Depends, BackgroundTasks
from backend.database_engine import (
    RealtimeLocationData,
    Events,
    UserEventSessions,
    engine,
)

router = APIRouter()

# Dependency for DB session
def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


# --- Thresholds ---
DISTANCE_THRESHOLD_FEET = 6.0
DURATION_THRESHOLD_SECONDS = 60
EVENT_GAP_SECONDS = 60


# --------------------------- PROXIMITY LOGIC (NO POSTGIS) ---------------------------
def get_proximity_data_bucketed(session, time_window='7 days', downsample_interval=1):

    bucket = int(downsample_interval)
    dist = float(DISTANCE_THRESHOLD_FEET)

    a = aliased(RealtimeLocationData)
    b = aliased(RealtimeLocationData)

    bucket_a = func.floor(func.extract('epoch', a.recorded_at) / bucket).label("bucket_group_a")
    bucket_b = func.floor(func.extract('epoch', b.recorded_at) / bucket).label("bucket_group_b")

    sub_a = (
        session.query(
            a.id.label("id"),
            a.x_coordinate.label("x"),
            a.y_coordinate.label("y"),
            a.recorded_at.label("recorded_at"),
            bucket_a,
        )
        .filter(a.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    sub_b = (
        session.query(
            b.id.label("id"),
            b.x_coordinate.label("x"),
            b.y_coordinate.label("y"),
            b.recorded_at.label("recorded_at"),
            bucket_b,
        )
        .filter(b.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    # Euclidean distance
    distance_expr = func.sqrt(
        func.pow(sub_a.c.x - sub_b.c.x, 2) +
        func.pow(sub_a.c.y - sub_b.c.y, 2)
    )

    query = (
        session.query(
            sub_a.c.id.label("user_a"),
            sub_b.c.id.label("user_b"),
            sub_a.c.recorded_at.label("recorded_at"),
        )
        .join(
            sub_b,
            and_(
                sub_a.c.bucket_group_a == sub_b.c.bucket_group_b,
                sub_a.c.id < sub_b.c.id,
                distance_expr <= dist,
            )
        )
        .order_by(sub_a.c.recorded_at)
    )

    return pd.read_sql(query.statement, session.bind)


# --------------------------- EVENT GROUPING ---------------------------
def group_connected_events(df):
    grouped = df.groupby("recorded_at")
    event_counter = 1
    events = []

    for ts, group in grouped:
        G = nx.Graph()
        G.add_edges_from(zip(group["user_a"], group["user_b"]))

        for component in nx.connected_components(G):
            if len(component) < 2:
                continue
            events.append({
                "event_id": event_counter,
                "timestamp": ts,
                "users": list(component)
            })
            event_counter += 1

    return events


# --------------------------- EVENT CONSOLIDATION ---------------------------
def consolidate_events(events):
    consolidated = []
    active = {}

    for e in events:
        key = tuple(sorted(e["users"]))

        if key not in active:
            active[key] = {
                "event_id": e["event_id"],
                "start_time": e["timestamp"],
                "end_time": e["timestamp"],
                "users": e["users"],
            }
        else:
            last = active[key]["end_time"]
            if (e["timestamp"] - last).total_seconds() <= EVENT_GAP_SECONDS:
                active[key]["end_time"] = e["timestamp"]
            else:
                consolidated.append(active.pop(key))
                active[key] = {
                    "event_id": e["event_id"],
                    "start_time": e["timestamp"],
                    "end_time": e["timestamp"],
                    "users": e["users"],
                }

    consolidated.extend(active.values())
    return consolidated


# --------------------------- NEW CENTROID (X/Y AVERAGE) ---------------------------
def get_numeric_centroid(session, start_time, end_time, user_ids):

    result = session.query(
        func.avg(RealtimeLocationData.x_coordinate),
        func.avg(RealtimeLocationData.y_coordinate),
    ).filter(
        RealtimeLocationData.id.in_(user_ids),
        RealtimeLocationData.recorded_at.between(start_time, end_time),
    ).first()

    if result and result[0] and result[1]:
        return float(result[0]), float(result[1])
    return None, None


# --------------------------- INSERT EVENTS ---------------------------
def insert_events(session, consolidated_events):

    valid_events = [
        e for e in consolidated_events
        if (e["end_time"] - e["start_time"]).total_seconds() >= DURATION_THRESHOLD_SECONDS
    ]

    for event in valid_events:

        x_centroid, y_centroid = get_numeric_centroid(
            session,
            event["start_time"],
            event["end_time"],
            event["users"],
        )

        if x_centroid is None:
            continue

        orm_event = Events(
            start_time=event["start_time"],
            end_time=event["end_time"],
            x_event=x_centroid,
            y_event=y_centroid,
        )

        session.add(orm_event)
        session.flush()

        for user_id in event["users"]:
            session.add(
                UserEventSessions(
                    id=user_id,
                    event_id=orm_event.event_id,
                    start_time=event["start_time"],
                    end_time=event["end_time"],
                )
            )

    session.commit()


# --------------------------- MAIN ---------------------------
def run_event_detection(time_window="7 days", downsample_interval=1):
    with Session(engine) as db:
        df = get_proximity_data_bucketed(db, time_window, downsample_interval)
        if df.empty:
            return "no_data"

        raw = group_connected_events(df)
        consolidated = consolidate_events(raw)

        if not consolidated:
            return "no_events"

        insert_events(db, consolidated)
        return "success"


# --------------------------- API ROUTE ---------------------------
@router.post("/run-event-detection")
async def run_event_detection_route(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_event_detection)
    return {"message": "Event detection started!"}
