sudo docker exec postgres psql -U admin -d dashboard_db -c "UPDATE agents SET agent_name = LOWER(REPLACE(name, ' ', '_')) WHERE agent_name IS NULL OR agent_name = '';"
