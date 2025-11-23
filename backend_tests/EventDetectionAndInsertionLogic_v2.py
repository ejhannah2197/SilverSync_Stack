import time
import pandas as pd
import networkx as nx
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, text, cast, Interval
from datetime import datetime, timedelta
import random
import math

# ORM models
from backend.database_engine import (
    RealtimeLocationData,
    Events,
    UserEventSessions,
    engine
)

# --- Configurable thresholds ---
DISTANCE_THRESHOLD_FEET = 6.0
DURATION_THRESHOLD_SECONDS = 60
EVENT_GAP_SECONDS = 60


# -------------------------------------------------------------
# Optional test data generator
# -------------------------------------------------------------
def insert_test_data(num_users=10, num_timestamps=5):
    """Insert clustered test data (no geometry)."""
    with Session(engine) as session:
        for uid in range(1, num_users + 1):
            for t in range(num_timestamps):
                x = 50 + random.random() * 5
                y = 50 + random.random() * 5
                session.add(
                    RealtimeLocationData(
                        id=uid,
                        x_coordinate=x,
                        y_coordinate=y,
                        recorded_at=datetime.now() - timedelta(seconds=t)
                    )
                )
        session.commit()


# -------------------------------------------------------------
# Manual distance calculation (replaces ST_DWithin)
# -------------------------------------------------------------
def euclidean_distance(a, b):
    return math.sqrt((a.x_coordinate - b.x_coordinate)**2 + (a.y_coordinate - b.y_coordinate)**2)


# -------------------------------------------------------------
# Bucketing & proximity detection (no geom)
# -------------------------------------------------------------
def get_proximity_data_bucketed(session, time_window='7 days', downsample_interval=1):
    bucket = int(downsample_interval)

    a = aliased(RealtimeLocationData)
    b = aliased(RealtimeLocationData)

    bucket_a = func.floor(func.extract('epoch', a.recorded_at) / bucket).label('bucket_group')
    bucket_b = func.floor(func.extract('epoch', b.recorded_at) / bucket).label('bucket_group')

    # get downsampled points
    sub_a = (
        session.query(
            a.id.label('id'),
            a.x_coordinate,
            a.y_coordinate,
            a.recorded_at,
            bucket_a
        )
        .filter(a.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    sub_b = (
        session.query(
            b.id.label('id'),
            b.x_coordinate,
            b.y_coordinate,
            b.recorded_at,
            bucket_b
        )
        .filter(b.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    # pull as Python rows
    rows_a = session.execute(sub_a.select()).fetchall()
    rows_b = session.execute(sub_b.select()).fetchall()

    records = []
    for a_row in rows_a:
        for b_row in rows_b:
            if a_row.bucket_group == b_row.bucket_group and a_row.id < b_row.id:
                dx = a_row.x_coordinate - b_row.x_coordinate
                dy = a_row.y_coordinate - b_row.y_coordinate
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= DISTANCE_THRESHOLD_FEET:
                    records.append({
                        "user_a": a_row.id,
                        "user_b": b_row.id,
                        "recorded_at": a_row.recorded_at
                    })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


# -------------------------------------------------------------
# Group into proximity graph events
# -------------------------------------------------------------
def group_connected_events(df):
    grouped = df.groupby('recorded_at')
    event_counter = 1
    events = []

    for timestamp, group in grouped:
        G = nx.Graph()
        G.add_edges_from(zip(group['user_a'], group['user_b']))

        for component in nx.connected_components(G):
            if len(component) < 2:
                continue

            events.append({
                "event_id": event_counter,
                "timestamp": timestamp,
                "users": list(component)
            })
            event_counter += 1

    return events


# -------------------------------------------------------------
# Merge sequential events
# -------------------------------------------------------------
def consolidate_events(events):
    consolidated = []
    active_events = {}

    for e in events:
        key = tuple(sorted(e['users']))

        if key not in active_events:
            active_events[key] = {
                "event_id": e["event_id"],
                "start_time": e["timestamp"],
                "end_time": e["timestamp"],
                "users": e["users"]
            }
        else:
            last_time = active_events[key]["end_time"]

            if (e["timestamp"] - last_time).total_seconds() <= EVENT_GAP_SECONDS:
                active_events[key]["end_time"] = e["timestamp"]
            else:
                consolidated.append(active_events.pop(key))
                active_events[key] = {
                    "event_id": e["event_id"],
                    "start_time": e["timestamp"],
                    "end_time": e["timestamp"],
                    "users": e["users"]
                }

    consolidated.extend(active_events.values())
    return consolidated


# -------------------------------------------------------------
# Compute centroid (average X/Y)
# -------------------------------------------------------------
def compute_centroid(session, ids, start_time, end_time):
    rows = (
        session.query(
            RealtimeLocationData.x_coordinate,
            RealtimeLocationData.y_coordinate
        )
        .filter(
            RealtimeLocationData.id.in_(ids),
            RealtimeLocationData.recorded_at.between(start_time, end_time)
        )
        .all()
    )

    if not rows:
        return None, None

    x_vals = [r.x_coordinate for r in rows]
    y_vals = [r.y_coordinate for r in rows]

    return sum(x_vals) / len(x_vals), sum(y_vals) / len(y_vals)


# -------------------------------------------------------------
# Insert events into SQL
# -------------------------------------------------------------
def insert_events(session, consolidated_events):
    for ev in consolidated_events:
        duration = (ev["end_time"] - ev["start_time"]).total_seconds()
        if duration < DURATION_THRESHOLD_SECONDS:
            continue

        x_cent, y_cent = compute_centroid(session, ev["users"], ev["start_time"], ev["end_time"])

        orm_event = Events(
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            x_event=int(x_cent),
            y_event=int(y_cent)
        )
        session.add(orm_event)
        session.flush()

        # Insert user sessions
        for uid in ev["users"]:
            session.add(UserEventSessions(
                id=uid,
                event_id=orm_event.event_id,
                start_time=ev["start_time"],
                end_time=ev["end_time"]
            ))

    session.commit()


# -------------------------------------------------------------
# Main pipeline
# -------------------------------------------------------------
def run_event_detection(time_window='7 days', downsample_interval=1, test_data=False):

    if test_data:
        insert_test_data()

    with Session(engine) as session:
        start = time.time()

        df = get_proximity_data_bucketed(session, time_window, downsample_interval)
        if df.empty:
            print("No proximity data.")
            return

        raw_events = group_connected_events(df)
        consolidated = consolidate_events(raw_events)

        if not consolidated:
            print("No events after consolidation.")
            return

        insert_events(session, consolidated)

        print(f"Event detection completed in {time.time() - start:.2f} sec")


# Run manually for testing
if __name__ == "__main__":
    run_event_detection(test_data=True)
