"""
generate_week_data.py

Generate 1 week of synthetic realtime_location_data using x/y coordinates
(no geometry, no PostGIS). Compatible with updated SilverSync schema.
"""

import random
from datetime import datetime, timedelta
from math import cos, sin, radians
from sqlalchemy import insert
from sqlalchemy.orm import Session
from tqdm import tqdm   # optional

from backend.database_engine import (
    SessionLocal, 
    RealtimeLocationData, 
    NametoUID, 
    engine
)

# ---------------------------
# CONFIG
# ---------------------------
NUM_USERS = 100
WEEK_START = datetime.now() - timedelta(days=7)
WEEK_END = WEEK_START + timedelta(days=7)

EVENTS_PER_USER = 10
AVG_EVENT_DURATION_MIN = 10
EVENT_DURATION_JITTER_MIN = 5
AVG_PARTICIPANTS = 4
SAMPLING_INTERVAL_SEC = 5
BACKGROUND_SAMPLES_PER_DAY = 6
BATCH_SIZE = 2000

FACILITY_CENTER = (5000, 5000)
FACILITY_SPREAD = 200


# ---------------------------
# Helpers
# ---------------------------

def random_point_around(center_x, center_y, radius):
    """Return random (x,y) within radius of center."""
    r = radius * (random.random() ** 0.5)
    theta = random.random() * 360
    x = center_x + r * cos(radians(theta))
    y = center_y + r * sin(radians(theta))
    return x, y


def ensure_users_exist(num_users):
    """Make sure NametoUID contains at least `num_users` entries."""
    with Session(engine) as session:
        existing = session.query(NametoUID.id).order_by(NametoUID.id.desc()).first()
        max_id = existing.id if existing else 0

        to_create = []
        for uid in range(max_id + 1, num_users + 1):
            to_create.append(NametoUID(id=uid, name=f"SIM_USER_{uid}"))

        if to_create:
            session.add_all(to_create)
            session.commit()
            print(f"Created {len(to_create)} names.")
        else:
            print("NametoUID already populated.")


def generate_event_schedule(num_users, events_per_user, avg_participants, start, end):
    """
    Create artificial social events:
        { start, end, participants[], center(x,y) }
    """
    total_events = max(1, int((num_users * events_per_user) / avg_participants))

    events = []
    total_seconds = int((end - start).total_seconds())

    for _ in range(total_events):
        offset = random.randint(0, total_seconds - 60)
        ev_start = start + timedelta(seconds=offset)

        duration = max(1, int(random.gauss(AVG_EVENT_DURATION_MIN, EVENT_DURATION_JITTER_MIN)))
        ev_end = ev_start + timedelta(minutes=duration)

        # choose random cluster center
        cx, cy = random_point_around(FACILITY_CENTER[0], FACILITY_CENTER[1], FACILITY_SPREAD)

        # participants
        size = max(2, int(random.gauss(avg_participants, 1)))
        participants = random.sample(range(1, num_users + 1), size)

        events.append({
            "start": ev_start,
            "end": ev_end,
            "participants": participants,
            "center": (cx, cy)
        })

    return events


def generate_location_points_for_event(event, sampling_interval_sec):
    """
    Return [(uid, x, y, recorded_at), ...]
    """
    pts = []
    start = event["start"]
    end = event["end"]
    center_x, center_y = event["center"]

    total_seconds = int((end - start).total_seconds())
    if total_seconds <= 0:
        return pts

    timestamps = [start + timedelta(seconds=i)
                  for i in range(0, total_seconds + 1, sampling_interval_sec)]

    for uid in event["participants"]:
        # each user offset a little so timestamps differ
        offset_us = random.randint(0, 999_999)

        for t in timestamps:
            t_adj = t + timedelta(microseconds=offset_us)
            x, y = random_point_around(center_x, center_y, radius=random.uniform(0, 3))
            pts.append((uid, x, y, t_adj))

    return pts


def generate_background_samples_for_user(uid, start, end, samples_per_day):
    """
    Sparse non-event data: [(uid, x, y, recorded_at)]
    """
    pts = []
    total_samples = samples_per_day * 7  # 1 per day

    for _ in range(total_samples):
        offset = random.randint(0, int((end - start).total_seconds()))
        t = start + timedelta(seconds=offset)
        x, y = random_point_around(FACILITY_CENTER[0], FACILITY_CENTER[1], FACILITY_SPREAD * 2)

        t = t + timedelta(microseconds=random.randint(0, 999_999))
        pts.append((uid, x, y, t))

    return pts


def bulk_insert_location_points(rows, batch_size=BATCH_SIZE):
    """
    Insert rows: (uid, x, y, timestamp) into RealtimeLocationData
    """
    if not rows:
        return 0

    table = RealtimeLocationData.__table__
    inserted = 0

    with engine.begin() as conn:
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            dicts = [
                {
                    "id": uid,
                    "x_coordinate": int(x),
                    "y_coordinate": int(y),
                    "recorded_at": ts
                }
                for uid, x, y, ts in chunk
            ]
            conn.execute(insert(table), dicts)
            inserted += len(dicts)

    return inserted


# ---------------------------
# Main driver
# ---------------------------

def generate_week_of_data(
    num_users=NUM_USERS,
    events_per_user=EVENTS_PER_USER,
    avg_participants=AVG_PARTICIPANTS,
    sampling_interval_sec=SAMPLING_INTERVAL_SEC,
    background_samples_per_day=BACKGROUND_SAMPLES_PER_DAY,
    week_start=WEEK_START,
    week_end=WEEK_END
):
    print("Ensuring NametoUID users exist...")
    ensure_users_exist(num_users)

    print("Generating event schedule...")
    events = generate_event_schedule(num_users, events_per_user, avg_participants, week_start, week_end)
    print(f"{len(events)} events planned")

    all_rows = []

    print("Generating event points...")
    for ev in tqdm(events):
        pts = generate_location_points_for_event(ev, sampling_interval_sec)
        all_rows.extend(pts)

    print("Generating background samples...")
    for uid in tqdm(range(1, num_users + 1)):
        pts = generate_background_samples_for_user(uid, week_start, week_end, background_samples_per_day)
        all_rows.extend(pts)

    random.shuffle(all_rows)

    print(f"Inserting {len(all_rows)} rows into realtime_location_data...")
    inserted = bulk_insert_location_points(all_rows)
    print(f"Inserted {inserted} rows successfully.")


if __name__ == "__main__":
    generate_week_of_data()
    print("Week data generation complete.")
