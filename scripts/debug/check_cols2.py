from sqlalchemy import create_engine, text

engine = create_engine("postgresql://admin:admin123@localhost:5432/dashboard_db")
with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'phone_numbers'"))
    print([row[0] for row in result])
