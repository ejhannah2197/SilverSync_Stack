from datetime import datetime, timedelta
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from database import SessionLocal, NametoUID, RealtimeLocationData, UserEventSessions, Events

# Create session
session = SessionLocal()

try:
    # -------------------------
    # INSERT INTO NametoUID
    # -------------------------
    user1 = NametoUID(id=1, name="Alice")
    user2 = NametoUID(id=2, name="Bob")
    session.add_all([user1, user2])

    # -------------------------
    # INSERT INTO RealtimeLocationData
    # -------------------------
    loc1 = RealtimeLocationData(
        id=1,
        geom=from_shape(Point(10, 20), srid=2277),  # WGS84 point
        recorded_at=datetime.now()
    )
    loc2 = RealtimeLocationData(
        id=2,
        geom=from_shape(Point(15, 25), srid=2277),
        recorded_at=datetime.now() - timedelta(minutes=5)
    )
    session.add_all([loc1, loc2])

    # -------------------------
    # INSERT INTO Events
    # -------------------------
    event = Events(
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
        location_geom=from_shape(Point(12, 22), srid=2277)
    )
    session.add(event)
    session.flush()  # flush so we can reference event.event_id

    # -------------------------
    # INSERT INTO UserEventSessions
    # -------------------------
    session1 = UserEventSessions(
        id=1,  # Alice
        event_id=event.event_id,
        start_time=datetime.now() - timedelta(minutes=45),
        end_time=datetime.now() - timedelta(minutes=15),
    )
    session.add(session1)

    # Commit everything
    session.commit()
    print("Sample data inserted successfully!")

except Exception as e:
    session.rollback()
    print(f"Error: {e}")

finally:
    session.close()
