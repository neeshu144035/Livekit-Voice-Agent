from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://admin:password123@localhost:5432/dashboard_db"
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE phone_numbers ADD COLUMN termination_uri VARCHAR(255);"))
        conn.execute(text("ALTER TABLE phone_numbers ADD COLUMN sip_username VARCHAR(100);"))
        conn.execute(text("ALTER TABLE phone_numbers ADD COLUMN sip_password VARCHAR(100);"))
        conn.execute(text("ALTER TABLE phone_numbers ADD COLUMN nickname VARCHAR(100);"))
        conn.commit()
        print("Columns added successfully.")
except Exception as e:
    print("Error:", e)
