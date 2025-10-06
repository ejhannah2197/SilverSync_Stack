"""
generate_week_data.py

Generate 1 week of synthetic realtime_location_data for testing SilverSync event detection.

Usage:
    python generate_week_data.py

Adjust parameters in the CONFIG section as needed.
"""

import random
from datetime import datetime, timedelta
from math import cos, sin, radians
from geoalchemy2 import WKTElement
from sqlalchemy import insert
from sqlalchemy.orm import Session
from tqdm import tqdm   # optional progress bar; install with pip if desired

# Import your ORM session & model
# Adjust the import path if your database.py is not at top-level
from backend.database import SessionLocal, RealtimeLocationData, NametoUID, engine

# ---------------------------
# CONFIG - tweak these values
# ---------------------------
NUM_USERS = 100
WEEK_START = datetime.now() - timedelta(days=7)  # week window start
WEEK_END = WEEK_START + timedelta(days=7)

EVENTS_PER_USER = 10                 # target average events per user during the week
AVG_EVENT_DURATION_MIN = 10         # average event duration in minutes
EVENT_DURATION_JITTER_MIN = 5       # +/- jitter in minutes
AVG_PARTICIPANTS = 4                # average number of users per event
SAMPLING_INTERVAL_SEC = 5           # how frequently to sample points during events
BACKGROUND_SAMPLES_PER_DAY = 6      # how many background samples each user has per day
BATCH_SIZE = 2000                   # DB insert batch size to avoid huge transactions

FACILITY_CENTER = (5000, 5000)      # arbitrary coordinate center for facility (units consistent with SRID)
FACILITY_SPREAD = 200                # how big the facility area is (meters / units)

# GEOMETRY SRID you use (your DB uses 2277 earlier)
SRID = 2277

# ---------------------------
# Helpers
# ---------------------------

def random_point_around(center_x, center_y, radius):
    """Return a (x,y) point randomly placed within radius of center."""
    # uniform distribution over circle
    r = radius * (random.random() ** 0.5)
    theta = random.random() * 360
    x = center_x + r * cos(radians(theta))
    y = center_y + r * sin(radians(theta))
    return x, y

def ensure_users_exist(num_users):
    """Ensure NametoUID contains at least num_users entries. Creates missing ones (IDs start at 1)."""
    with Session(engine) as session:
        # get existing max id
        existing = session.query(NametoUID.id).order_by(NametoUID.id.desc()).first()
        max_id = existing.id if existing else 0
        to_create = []
        for uid in range(max_id + 1, num_users + 1):
            to_create.append(NametoUID(id=uid, name=f"SIM_USER_{uid}"))
        if to_create:
            session.add_all(to_create)
            session.commit()
            print(f"Created {len(to_create)} NametoUID entries (ids {max_id+1}..{num_users}).")
        else:
            print("NametoUID already has sufficient users.")

def round_to_nearest_second(dt: datetime) -> datetime:
    """Round a datetime to the nearest second."""
    return (dt + timedelta(microseconds=500_000)).replace(microsecond=0)


def generate_event_schedule(num_users, events_per_user, avg_participants, start, end):
    """
    Return a list of event dicts:
      { 'start': datetime, 'end': datetime, 'participants': [uid, ...], 'center': (x,y) }
    We produce total_events ~ (num_users * events_per_user) / avg_participants
    """
    total_events = max(1, int((num_users * events_per_user) / avg_participants))
    events = []
    total_seconds = int((end - start).total_seconds())
    for _ in range(total_events):
        event_start_offset = random.randint(0, total_seconds - 60)  # ensure at least 1 min before end
        event_start = start + timedelta(seconds=event_start_offset)
        dur_min = max(1, int(random.gauss(avg_minutes := AVG_EVENT_DURATION_MIN, EVENT_DURATION_JITTER_MIN)))
        event_end = event_start + timedelta(minutes=dur_min)
        # choose random participants (no duplicates), size ~ Poisson-like around avg_participants
        size = max(2, int(random.poissonvariate(avg_participants) if hasattr(random, "poissonvariate") else
                         max(2, int(random.gauss(avg_participants, 1)))))
        # fallback if size < 2
        size = max(2, size)
        participants = random.sample(range(1, num_users + 1), size)
        # choose cluster center
        cx, cy = random_point_around(FACILITY_CENTER[0], FACILITY_CENTER[1], FACILITY_SPREAD)
        events.append({
            "start": event_start,
            "end": event_end,
            "participants": participants,
            "center": (cx, cy)
        })
    return events

def generate_location_points_for_event(event, sampling_interval_sec):
    """
    For one event, generate a list of tuples (user_id, wkt_point, recorded_at)
    for every participant, sampling at sampling_interval_sec intervals across event duration.
    """
    pts = []
    start = event["start"]
    end = event["end"]
    center_x, center_y = event["center"]
    total_seconds = int((end - start).total_seconds())
    if total_seconds <= 0:
        return pts
    timestamps = [start + timedelta(seconds=i) for i in range(0, total_seconds + 1, sampling_interval_sec)]
    # small individual offsets so different users don't have same recorded_at for composite pk
    for uid in event["participants"]:
        user_offset_micros = random.randint(0, 999_999)
        # participants cluster near center but each on slightly different radius
        radius = random.uniform(0, 3)  # small radius in same units
        for t in timestamps:
            # slightly jitter t by microseconds unique per user to avoid identical timestamps
            t_adj = t + timedelta(microseconds=user_offset_micros)
            x, y = random_point_around(center_x, center_y, radius)
            wkt = f"POINT({x} {y})"
            pts.append((uid, wkt, t_adj))
    return pts

def generate_background_samples_for_user(uid, start, end, samples_per_day):
    """Generate sparse non-event background samples for a single user across the week."""
    pts = []
    total_days = (end.date() - start.date()).days or 1
    total_samples = samples_per_day * total_days
    day_seconds = 24 * 3600
    for i in range(total_samples):
        # random timestamp in week
        offset = random.randint(0, int((end - start).total_seconds()))
        t = start + timedelta(seconds=offset)
        # random location across facility
        x, y = random_point_around(FACILITY_CENTER[0], FACILITY_CENTER[1], FACILITY_SPREAD * 2)
        # microsecond jitter to avoid collisions
        t = t + timedelta(microseconds=random.randint(0, 999_999))
        pts.append((uid, f"POINT({x} {y})", t))
    return pts

def bulk_insert_location_points(rows, batch_size=BATCH_SIZE):
    """
    Insert list of tuples (user_id, wkt_point, recorded_at) into realtime_location_data in batches.
    Uses SQLAlchemy core insert for speed.
    """
    if not rows:
        return 0
    inserted = 0
    table = RealtimeLocationData.__table__
    with engine.begin() as conn:
        # convert to dicts for executemany
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i+batch_size]
            dicts = [
                {"id": uid, "geom": WKTElement(wkt, srid=SRID), "recorded_at": recorded_at}
                for uid, wkt, recorded_at in chunk
            ]
            conn.execute(insert(table), dicts)
            inserted += len(dicts)
    return inserted

# ---------------------------
# Main generator function
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
    print("Ensuring users exist...")
    ensure_users_exist(num_users)

    print("Generating event schedule...")
    events = generate_event_schedule(num_users, events_per_user, avg_participants, week_start, week_end)
    print(f"Planned {len(events)} events for week.")

    all_rows = []

    # Generate event points
    print("Generating event location points...")
    for ev in tqdm(events, desc="events"):
        pts = generate_location_points_for_event(ev, sampling_interval_sec)
        all_rows.extend(pts)

    # Generate background samples for all users
    print("Generating background samples for users...")
    for uid in tqdm(range(1, num_users + 1), desc="users"):
        pts = generate_background_samples_for_user(uid, week_start, week_end, background_samples_per_day)
        all_rows.extend(pts)

    # Shuffle (so insert order isn't all events then background)
    random.shuffle(all_rows)

    print(f"Total rows to insert: {len(all_rows)}")
    inserted = bulk_insert_location_points(all_rows)
    print(f"Inserted {inserted} location rows.")

# ---------------------------
# CLI / Run
# ---------------------------
if __name__ == "__main__":
    # Quick run: produce week of data (takes time based on rows)
    generate_week_of_data()
    print("Generation complete.")
