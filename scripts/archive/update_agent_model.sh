sudo docker exec postgres psql -U admin -d dashboard_db -c "UPDATE agents SET llm_model='gpt-4o-mini' WHERE id=5;"
