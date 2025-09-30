# RTL Live Data Generator (Optimized)

from psycopg2 import sql
import psycopg2, random, time, sys, calendar, argparse
from datetime import datetime, timedelta

"""
import time
import argparse
import sys
"""

# Configuration
DB_CONFIG = {
    'dbname': 'demoDB',
    'user': 'postgres',
    'password': 'WAKE419!',
    'host': 'localhost',
    'port': '5432'
}

# Constants
USER_IDS = list(range(1, 201))  # Simulate 200 users
MAX_STEP = 1

def ensure_partition(cursor, recorded_at):
    """Ensure a monthly partition exists for the given timestamp."""
    year = recorded_at.year
    month = recorded_at.month

    month_start = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    partition_name = f"realtime_location_data_{month_start.strftime('%Y%m')}"

    create_partition_sql = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {partition} PARTITION OF realtime_location_data
        FOR VALUES FROM (%s) TO (%s);
    """).format(partition=sql.Identifier(partition_name))

    cursor.execute(create_partition_sql, [month_start, next_month])


def insert_location_data(cursor, data):
    """Insert location records into the database."""
    
    insert_query = """
        INSERT INTO realtime_location_data (id, geom, recorded_at)
        VALUES (%s, ST_GeomFromText(%s, 2277), %s);
    """
    
    cursor.executemany(insert_query, data)

def live_simulation(duration_seconds):
    """Simulate real-time location updates and insert them into the database."""
    user_positions = {
        uid: [random.randint(0, 100), random.randint(0, 100)] for uid in USER_IDS
    }

    print(f"Starting live simulation for {duration_seconds} seconds...")

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                seen_partitions = set()
                start_time = time.time()

                while time.time() - start_time < duration_seconds:
                    recorded_at = datetime.now()
                    date_str = recorded_at.date().isoformat()

                    # Create partition if not already seen
                    if date_str not in seen_partitions:
                        ensure_partition(cursor, recorded_at)
                        seen_partitions.add(date_str)

                    # Update positions and collect data
                    data = []
                    for uid in USER_IDS:
                        x, y = user_positions[uid]
                        x += random.randint(-MAX_STEP, MAX_STEP)
                        y += random.randint(-MAX_STEP, MAX_STEP)

                        # Clamp to bounds 0..100
                        x = max(0, min(100, x))
                        y = max(0, min(100, y))

                        user_positions[uid] = [x, y]
                        point_wkt = f'POINT({x} {y})'
                        data.append((uid, point_wkt, recorded_at))

                    insert_location_data(cursor, data)
                    conn.commit()
                    print(f"[{recorded_at.strftime('%H:%M:%S')}] Inserted {len(data)} records.")

                    time.sleep(1)

    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    except Exception as e:
        print("Error during simulation:", e)
    finally:
        print("Simulation complete. Database connection closed.")


def main():
    parser = argparse.ArgumentParser(description="Simulate real-time location data insertion.")
    parser.add_argument('--duration', type=int, default=86400, help='Simulation duration in seconds')
    args = parser.parse_args()

    if args.duration <= 0:
        print("Duration must be a positive integer.")
        sys.exit(1)

    live_simulation(args.duration)

if __name__ == '__main__':
    main()
