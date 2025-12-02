import json
import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime

# --------------------------------------------------------------------
# PostgreSQL Connection
# --------------------------------------------------------------------
conn = psycopg2.connect(
    host = "192.168.137.2",
    port = 5432,
    dbname="demoDB",
    user="postgres",
    password="WAKE419!"
)
cursor = conn.cursor()

# --------------------------------------------------------------------
# CONFIG: Map BLE Tag Names → User IDs
# Add all your tags here
# --------------------------------------------------------------------
TAG_ID_MAP = {
    "ble-pd-6C5CB1CCE905": { "id" : 1 , "name" : "MIKE WILLEY"},
    "ble-pd-6C5CB1C217CF": { "id" : 2 , "name" : "CLINT SMITH"},
    "ble-pd-6C5CB1CCD95A": { "id" : 3 , "name" : "LEE HUDSON"},
    "ble-pd-6C5CB1CCD2C5": { "id" : 4 , "name" : "DOUG BARNETT"},
    # "ble-pd-6C5CB1CCD310": { "id" : 5 , "name" : "ROSANNE GUEGUEN"},
    "ble-pd-6C5CB1CCD310": { "id" : 6 , "name" : "COLBY RYAN"},
    # Add more mappings as needed
}

def sync_tag_map_to_database(tag_map):
    """
    Syncs hard-coded TAG_ID_MAP into the nametouid table.
    Adds new entries or updates names as needed.
    """

    for tag_id, user in tag_map.items():
        user_id = user["id"]
        name = user["name"]

        cursor.execute("""
            INSERT INTO nametouid (id, tag_id, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                tag_id = EXCLUDED.tag_id,
                name = EXCLUDED.name;
        """, (user_id, tag_id, name))


        conn.commit()

# --------------------------------------------------------------------
# Parse MQTT Messages
# --------------------------------------------------------------------
def on_message(client, userdata, msg):

    # Example topic:
    # silabs/aoa/position/positioning-test_room/ble-pd-6C5CB1CCD310
    topic_parts = msg.topic.split("/")
    tag_name = topic_parts[-1]   # "ble-pd-6C5CB1CCD310"

    if tag_name not in TAG_ID_MAP:
        print(f"Unknown tag: {tag_name} (add to TAG_ID_MAP)")
        return

    user_id = TAG_ID_MAP[tag_name]["id"]

    # Decode JSON payload
    payload = json.loads(msg.payload.decode())

    x = payload.get("x")
    y = payload.get("y")

    # Use server-side timestamp
    recorded_at = datetime.utcnow()

    # Insert into database
    cursor.execute("""
        INSERT INTO realtime_location_data (id, x_coordinate, y_coordinate, recorded_at)
        VALUES (%s, %s, %s, %s)
    """, (user_id, x, y, recorded_at))

    conn.commit()

    print(f"Inserted: user={id} x={x} y={y} time={recorded_at} tag={tag_name}")


# --------------------------------------------------------------------
# MQTT Setup
# --------------------------------------------------------------------
client = mqtt.Client()
sync_tag_map_to_database(TAG_ID_MAP)
client.on_message = on_message

# IP from your screenshot is likely 192.168.137.1
client.connect("192.168.137.1", 1883, 60)

# Subscribe to all BLE position topics
# From screenshot: silabs / aoa / position / positioning-test_room / <tag>
client.subscribe("silabs/aoa/position/#")

client.loop_forever()
