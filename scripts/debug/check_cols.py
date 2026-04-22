import os
from sqlalchemy import create_engine, text

# Using the database URL from .env or default testing
url = os.environ.get("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/dashboard_db")

engine = create_engine(url)
with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'phone_numbers'"))
    for row in result:
        print(row.column_name)
