import time
import pandas as pd
import networkx as nx
from sqlalchemy.orm import Session, aliased
from sqlalchemy import text, func, and_, cast, Interval
from geoalchemy2 import WKTElement
from datetime import datetime, timedelta
import random
from tqdm import tqdm  # <-- NEW: for progress bar

# Import your ORM models from database.py
from backend.database_engine import RealtimeLocationData, Events, UserEventSessions, engine

# --- Configurable thresholds ---
DISTANCE_THRESHOLD_FEET = 6.0
DURATION_THRESHOLD_SECONDS = 60
EVENT_GAP_SECONDS = 60

# --- Optional: insert clustered test data ---
def insert_test_data(num_users=10, num_timestamps=5):
    """Insert clustered location data for testing purposes."""
    with Session(engine) as session:
        for uid in range(1, num_users + 1):
            for t in range(num_timestamps):
                x = 50 + random.random() * 5
                y = 50 + random.random() * 5
                point = WKTElement(f'POINT({x} {y})', srid=2277)
                session.add(RealtimeLocationData(id=uid, geom=point, recorded_at=datetime.now() - timedelta(seconds=t)))
        session.commit()

# --- Query proximity pairs using downsampled timestamps ---
def get_proximity_data_bucketed(session, time_window='7 days', downsample_interval=1):
    """
    ORM-based query that downsamples timestamps and finds nearby users.
    """
    bucket = int(downsample_interval)
    dist = float(DISTANCE_THRESHOLD_FEET)

    a = aliased(RealtimeLocationData)
    b = aliased(RealtimeLocationData)

    bucket_a = func.floor(func.extract('epoch', a.recorded_at) / bucket).label('bucket_group_a')
    bucket_b = func.floor(func.extract('epoch', b.recorded_at) / bucket).label('bucket_group_b')

    sub_a = (
        session.query(
            a.id.label('id'),
            a.geom.label('geom'),
            a.recorded_at.label('recorded_at'),
            bucket_a
        )
        .filter(a.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    sub_b = (
        session.query(
            b.id.label('id'),
            b.geom.label('geom'),
            b.recorded_at.label('recorded_at'),
            bucket_b
        )
        .filter(b.recorded_at >= func.now() - cast(text(f"INTERVAL '{time_window}'"), Interval))
        .subquery()
    )

    query = (
        session.query(
            sub_a.c.id.label('user_a'),
            sub_b.c.id.label('user_b'),
            sub_a.c.recorded_at.label('recorded_at')
        )
        .join(
            sub_b,
            and_(
                sub_a.c.bucket_group_a == sub_b.c.bucket_group_b,
                sub_a.c.id < sub_b.c.id,
                func.ST_DWithin(sub_a.c.geom, sub_b.c.geom, dist)
            )
        )
        .order_by(sub_a.c.recorded_at)
    )

    df = pd.read_sql(query.statement, session.bind)
    return df

# --- Group users into connected events ---
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

# --- Consolidate sequential events ---
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

# --- Compute event centroid using ORM ---
def get_event_centroid(session, start_time, end_time, ids):
    result = session.query(
        func.ST_AsText(
            func.ST_Centroid(
                func.ST_Collect(RealtimeLocationData.geom)
            )
        )
    ).filter(
        RealtimeLocationData.id.in_(ids),
        RealtimeLocationData.recorded_at.between(start_time, end_time)
    ).scalar()
    return result

# --- Insert events and sessions using ORM (with progress bar) ---
def insert_events(session, consolidated_events):
    valid_events = [
        e for e in consolidated_events
        if (e["end_time"] - e["start_time"]).total_seconds() >= DURATION_THRESHOLD_SECONDS
    ]

    print(f"\nPreparing to insert {len(valid_events)} valid events...\n")
    time.sleep(0.5)

    for event in tqdm(valid_events, desc="Inserting events", unit="evt"):
        centroid_wkt = get_event_centroid(session, event["start_time"], event["end_time"], event["users"])
        centroid_geom = WKTElement(centroid_wkt, srid=2277) if centroid_wkt else None

        orm_event = Events(
            start_time=event["start_time"],
            end_time=event["end_time"],
            location_geom=centroid_geom
        )
        session.add(orm_event)
        session.flush()  # get generated event_id

        for user_id in event["users"]:
            session.add(UserEventSessions(
                id=user_id,
                event_id=orm_event.event_id,
                start_time=event["start_time"],
                end_time=event["end_time"]
            ))

    session.commit()
    print(f"\nSuccessfully inserted {len(valid_events)} events.\n")

# --- Main runner ---
def run_event_detection(time_window='7 days', downsample_interval=1, test_data=False):
    if test_data:
        insert_test_data(num_users=10, num_timestamps=5)

    with Session(engine) as session:
        start_time = time.time()
        df = get_proximity_data_bucketed(session, time_window, downsample_interval)
        if df.empty:
            print(f"No proximity data found in the past {time_window}.")
            return

        raw_events = group_connected_events(df)
        consolidated = consolidate_events(raw_events)

        if not consolidated:
            print("No events to insert after consolidation.")
            return

        insert_events(session, consolidated)
        elapsed = time.time() - start_time
        print(f"Event detection completed in {elapsed:.2f} seconds.")

# --- Execute ---
if __name__ == "__main__":
    run_event_detection(test_data=True)
