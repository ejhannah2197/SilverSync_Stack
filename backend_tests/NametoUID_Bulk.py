# Direct insertion into DB using SQLAlchemy ORM
# No CSV intermediate file

import names
from backend.database_engine import SessionLocal, NametoUID

# -----------------------------
# Config
# -----------------------------
x = 100  # number of names to generate

# -----------------------------
# Generate and insert directly
# -----------------------------
def insert_new_names(count=x):
    print(f"Generating and inserting {count} names directly into DB...")

    session = SessionLocal()
    try:
        # Get current max ID in DB
        max_id_obj = session.query(NametoUID).order_by(NametoUID.id.desc()).first()
        max_id = max_id_obj.id if max_id_obj else 0
        print("Current max ID in DB:", max_id)

        new_entries = []
        for i in range(1, count + 1):
            new_id = max_id + i
            full_name = names.get_full_name().upper()
            new_entries.append(NametoUID(id=new_id, name=full_name))

        # Bulk insert
        session.add_all(new_entries)
        session.commit()
        print(f"✅ {len(new_entries)} records inserted successfully.")

    except Exception as e:
        session.rollback()
        print("❌ Error during DB insertion:", e)
    finally:
        session.close()

# -----------------------------
# Run the function
# -----------------------------
insert_new_names()
