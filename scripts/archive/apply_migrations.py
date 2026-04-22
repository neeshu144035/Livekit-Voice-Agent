import os
import psycopg2
from sqlalchemy import create_engine, MetaData, Table, Column, Float, Integer, String, Text

DATABASE_URL = "postgresql://admin:password123@localhost:5432/dashboard_db"

def update_db():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect("host=localhost dbname=dashboard_db user=admin password=password123")
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Checking for missing columns in 'calls' table...")
        
        columns_to_add = [
            ("llm_cost", "DOUBLE PRECISION DEFAULT 0.0"),
            ("stt_cost", "DOUBLE PRECISION DEFAULT 0.0"),
            ("tts_cost", "DOUBLE PRECISION DEFAULT 0.0"),
            ("llm_tokens_in", "INTEGER DEFAULT 0"),
            ("llm_tokens_out", "INTEGER DEFAULT 0"),
            ("llm_model_used", "VARCHAR(50)"),
            ("stt_duration_ms", "INTEGER DEFAULT 0"),
            ("tts_characters", "INTEGER DEFAULT 0"),
            ("transcript_summary", "TEXT")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cur.execute(f"ALTER TABLE calls ADD COLUMN {col_name} {col_type};")
                print(f"Added column: {col_name}")
            except psycopg2.errors.DuplicateColumn:
                print(f"Column {col_name} already exists.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                
        cur.close()
        conn.close()
        print("Database update complete.")
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    update_db()
