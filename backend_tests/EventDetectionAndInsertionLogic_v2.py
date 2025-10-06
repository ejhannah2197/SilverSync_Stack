import time
import pandas as pd
import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import text
from geoalchemy2 import WKTElement
from datetime import datetime, timedelta
import random

# Import your ORM models from database.py
from backend.database import RealtimeLocationData, Events, UserEventSessions, engine

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
    bucket = int(downsample_interval)
    dist = float(DISTANCE_THRESHOLD_FEET)

    query = f"""
        WITH downsampled AS (
            SELECT
                id,
                recorded_at,
                geom,
                floor(extract(epoch FROM recorded_at) / {bucket}) AS bucket_group
            FROM realtime_location_data
            WHERE recorded_at >= NOW() - INTERVAL '{time_window}'
        )
        SELECT a.id AS user_a, b.id AS user_b, a.recorded_at
        FROM downsampled a
        JOIN downsampled b
          ON a.bucket_group = b.bucket_group
         AND a.id < b.id
         AND ST_DWithin(a.geom, b.geom, {dist})
        ORDER BY a.recorded_at
    """
    df = pd.read_sql(text(query), session.bind)
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
        RealtimeLocationData.geom.ST_Collect().ST_Centroid().ST_AsText()
    ).filter(
        RealtimeLocationData.id.in_(ids),
        RealtimeLocationData.recorded_at.between(start_time, end_time)
    ).scalar()
    return result

# --- Insert events and sessions using ORM ---
def insert_events(session, consolidated_events):
    for event in consolidated_events:
        duration = (event["end_time"] - event["start_time"]).total_seconds()
        if duration < DURATION_THRESHOLD_SECONDS:
            continue

        centroid_wkt = get_event_centroid(session, event["start_time"], event["end_time"], event["users"])
        centroid_geom = WKTElement(centroid_wkt, srid=2277) if centroid_wkt else None

        orm_event = Events(
            start_time=event["start_time"],
            end_time=event["end_time"],
            location_geom=centroid_geom
        )
        session.add(orm_event)
        session.flush()  # get event_id

        # Add all user sessions
        for user_id in event["users"]:
            session.add(UserEventSessions(
                id=user_id,
                event_id=orm_event.event_id,
                start_time=event["start_time"],
                end_time=event["end_time"]
            ))

    session.commit()

# --- Main runner ---
def run_event_detection(time_window='7 days', downsample_interval=1, test_data=False):
    if test_data:
        insert_test_data(num_users=10, num_timestamps=5)

    with Session(engine) as session:
        df = get_proximity_data_bucketed(session, time_window, downsample_interval)
        if df.empty:
            print(f"No proximity data found in the past {time_window}.")
            return

        raw_events = group_connected_events(df)
        consolidated = consolidate_events(raw_events)
        insert_events(session, consolidated)
        print(f"Inserted {len(consolidated)} consolidated events.")

# --- Execute ---
if __name__ == "__main__":
    run_event_detection(test_data=True)
