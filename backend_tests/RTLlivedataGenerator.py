# RTL Live Data Generator (SQLAlchemy Version)

import random
import time
from datetime import datetime
import argparse
from backend.database import SessionLocal, RealtimeLocationData, NametoUID

# Constants
MAX_STEP = 1  # maximum movement per update

def insert_location_data(session, data):
    """Bulk insert location records using SQLAlchemy session."""
    session.add_all(data)
    session.commit()

def live_simulation(duration_seconds):
    """Simulate real-time location updates for all users in NametoUID."""
    session = SessionLocal()

    try:
        # Get all user IDs from the database
        user_ids = [user.id for user in session.query(NametoUID.id).all()]
        print(f"Found {len(user_ids)} users in NametoUID table.")

        # Initialize random positions for each user
        user_positions = {uid: [random.randint(0, 100), random.randint(0, 100)] for uid in user_ids}

        start_time = time.time()
        print(f"Starting live simulation for {duration_seconds} seconds...")

        while time.time() - start_time < duration_seconds:
            recorded_at = datetime.now()

            data_batch = []
            for uid in user_ids:
                x, y = user_positions[uid]

                # Random movement
                x += random.randint(-MAX_STEP, MAX_STEP)
                y += random.randint(-MAX_STEP, MAX_STEP)

                # Clamp to 0..100
                x = max(0, min(100, x))
                y = max(0, min(100, y))

                user_positions[uid] = [x, y]

                # Create SQLAlchemy object
                point_wkt = f'POINT({x} {y})'
                data_batch.append(
                    RealtimeLocationData(id=uid, geom=point_wkt, recorded_at=recorded_at)
                )

            # Insert batch into DB
            insert_location_data(session, data_batch)
            print(f"[{recorded_at.strftime('%H:%M:%S')}] Inserted {len(data_batch)} records.")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    except Exception as e:
        session.rollback()
        print("Error during simulation:", e)
    finally:
        session.close()
        print("Simulation complete. Database connection closed.")

def main():
    parser = argparse.ArgumentParser(description="Simulate real-time location data insertion.")
    parser.add_argument('--duration', type=int, default=60, help='Simulation duration in seconds')
    args = parser.parse_args()

    if args.duration <= 0:
        print("Duration must be a positive integer.")
        return

    live_simulation(args.duration)

if __name__ == '__main__':
    main()
