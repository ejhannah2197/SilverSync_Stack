"""
Optimized Event Detection for SilverSync
- Uses SQLAlchemy models and sessions
- Leverages in-database operations where possible
- Handles duration filtering and centroid calculation
- Compatible with current backend structure
"""

import time
import pandas as pd
import networkx as nx
from sqlalchemy import select, func
from geoalchemy2 import WKTElement
from backend.database import SessionLocal, RealtimeLocationData, Events, UserEventSessions

# Thresholds
DISTANCE_THRESHOLD_FEET = 6.0      # Proximity distance threshold
DURATION_THRESHOLD_SECONDS = 10    # Minimum session duration

def get_proximity_data_bucketed(session, time_window='7 days', downsample_interval=1):
    """
    Query proximity pairs using downsampled timestamps to reduce data volume.
    Returns a DataFrame of user pairs and recorded_at.
    """
    # Inline the bucket, interval, and distance safely
    bucket = int(downsample_interval)
    interval = str(time_window)
    dist = float(DISTANCE_THRESHOLD_FEET)

    query = f"""
        WITH downsampled AS (
            SELECT DISTINCT ON (id, floor(extract(epoch FROM recorded_at) / {bucket}))
                id,
                recorded_at,
                geom,
                floor(extract(epoch FROM recorded_at) / {bucket}) AS bucket_group
            FROM realtime_location_data
            WHERE recorded_at >= NOW() - INTERVAL '{interval}'
        )
        SELECT a.id AS user_a, b.id AS user_b, a.recorded_at
        FROM downsampled a
        JOIN downsampled b
          ON a.bucket_group = b.bucket_group
         AND a.id < b.id
         AND ST_DWithin(a.geom, b.geom, {dist})
        ORDER BY a.recorded_at
    """
    df = pd.read_sql(query, session.bind)
    return df

def group_connected_events(df):
    """Build connected graphs per timestamp to identify user groups."""
    grouped = df.groupby('recorded_at')
    events = []
    event_counter = 1

    for ts, group in grouped:
        G = nx.Graph()
        G.add_edges_from(zip(group['user_a'], group['user_b']))

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

def consolidate_events(events, gap_seconds=5):
    """
    Merge sequential events with the same users if timestamps are within gap_seconds.
    Returns a list of consolidated sessions.
    """
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
            if (e["timestamp"] - last_time).total_seconds() <= gap_seconds:
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

def get_event_centroid(session, start_time, end_time, user_ids):
    """Compute centroid WKT of points for given users and time range."""
    if not user_ids:
        return None

    stmt = select(func.ST_AsText(func.ST_Centroid(func.ST_Collect(RealtimeLocationData.geom)))).\
        where(
            RealtimeLocationData.id.in_(user_ids),
            RealtimeLocationData.recorded_at.between(start_time, end_time)
        )
    result = session.execute(stmt).scalar()
    return result

def insert_events(session, consolidated_events):
    """Insert filtered events and corresponding user sessions into DB."""
    event_objects = []
    session_objects = []

    for e in consolidated_events:
        duration = (e['end_time'] - e['start_time']).total_seconds()
        if duration < DURATION_THRESHOLD_SECONDS:
            continue

        centroid_wkt = get_event_centroid(session, e['start_time'], e['end_time'], e['users'])
        centroid_geom = WKTElement(centroid_wkt, srid=2277) if centroid_wkt else None

        event_obj = Events(
            start_time=e['start_time'],
            end_time=e['end_time'],
            location_geom=centroid_geom
        )
        event_objects.append(event_obj)

    if not event_objects:
        print("No events to insert after duration filter.")
        return

    # Insert events and get assigned IDs
    session.add_all(event_objects)
    session.commit()

    # Prepare user-event session entries
    for event_obj, e in zip(event_objects, consolidated_events):
        duration = (e['end_time'] - e['start_time']).total_seconds()
        if duration < DURATION_THRESHOLD_SECONDS:
            continue

        for uid in e['users']:
            session_objects.append(UserEventSessions(
                id=uid,
                event_id=event_obj.event_id,
                start_time=e['start_time'],
                end_time=e['end_time']
            ))

    if session_objects:
        session.add_all(session_objects)
        session.commit()

def run_event_detection(time_window='7 days', downsample_interval=1):
    """Top-level function to process events end-to-end."""
    session = SessionLocal()
    try:
        df = get_proximity_data_bucketed(session, time_window, downsample_interval)
        if df.empty:
            print(f"No proximity data in the past {time_window}.")
            return

        raw_events = group_connected_events(df)
        consolidated = consolidate_events(raw_events)
        insert_events(session, consolidated)

        print(f"Inserted {len(consolidated)} consolidated events.")
    finally:
        session.close()

if __name__ == '__main__':
    start = time.time()
    run_event_detection()
    print(f"Event detection completed in {time.time() - start:.2f} seconds.")
