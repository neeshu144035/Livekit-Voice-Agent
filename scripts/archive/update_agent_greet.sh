sudo docker exec postgres psql -U admin -d dashboard_db -c "UPDATE agents SET welcome_message_type='agent_greets', welcome_message='Hello, this is Sarah. How can I help you today?' WHERE id=5;"
