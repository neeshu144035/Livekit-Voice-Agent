"""
Migration script to add TTS fallback tracking columns to the calls table.
Run this script to apply the migration.
"""

from sqlalchemy import create_engine, text
import os

# Get DATABASE_URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5432/dashboard_db")

def apply_migration():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'calls' 
            AND column_name IN ('tts_fallback_used', 'tts_original_model', 'tts_actual_model')
        """))
        existing_cols = [row[0] for row in result]
        
        if 'tts_fallback_used' in existing_cols:
            print("✓ Columns already exist, skipping migration.")
            return
        
        # Add columns
        print("Adding TTS fallback columns to 'calls' table...")
        
        conn.execute(text("""
            ALTER TABLE calls 
            ADD COLUMN tts_fallback_used BOOLEAN DEFAULT FALSE,
            ADD COLUMN tts_original_model VARCHAR(50),
            ADD COLUMN tts_actual_model VARCHAR(50)
        """))
        
        conn.commit()
        print("✓ Migration applied successfully!")

if __name__ == "__main__":
    apply_migration()