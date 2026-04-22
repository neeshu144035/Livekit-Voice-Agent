ALTER TABLE agents ADD COLUMN welcome_message_type VARCHAR DEFAULT 'user_speaks_first';
ALTER TABLE agents ADD COLUMN welcome_message TEXT DEFAULT '';
