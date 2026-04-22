#!/bin/bash
sudo docker exec postgres psql -U admin -d dashboard_db -c "UPDATE phone_numbers SET livekit_outbound_trunk_id='ST_tf7YSZP47YE7' WHERE id=4;"
echo "Updated trunk ID for +442038287227"

sudo docker exec postgres psql -U admin -d dashboard_db -c "SELECT id, phone_number, termination_uri, livekit_outbound_trunk_id FROM phone_numbers WHERE id=4;"
