#!/bin/bash

# Script to update the database schema on the VPS
# Adds cost tracking and usage metrics columns to the calls table

echo "Adding columns to the calls table..."

# Added cost columns
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS llm_cost DOUBLE PRECISION DEFAULT 0.0;"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS stt_cost DOUBLE PRECISION DEFAULT 0.0;"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS tts_cost DOUBLE PRECISION DEFAULT 0.0;"

# Added usage metrics columns
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS llm_tokens_in INTEGER DEFAULT 0;"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS llm_tokens_out INTEGER DEFAULT 0;"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS llm_model_used VARCHAR(50);"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS stt_duration_ms INTEGER DEFAULT 0;"
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS tts_characters INTEGER DEFAULT 0;"

# Added transcript summary
sudo docker exec postgres psql -U admin -d dashboard_db -c "ALTER TABLE calls ADD COLUMN IF NOT EXISTS transcript_summary TEXT;"

echo "Database update complete!"
echo "Showing updated calls table structure:"
sudo docker exec postgres psql -U admin -d dashboard_db -c "\d calls"
