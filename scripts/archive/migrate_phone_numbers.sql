-- Migration script to add missing columns to phone_numbers table

ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS twilio_account_sid VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS twilio_auth_token VARCHAR(100);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS twilio_sip_trunk_sid VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS livekit_inbound_trunk_id VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS livekit_outbound_trunk_id VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS livekit_dispatch_rule_id VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS livekit_sip_endpoint VARCHAR(100);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS inbound_agent_id INTEGER REFERENCES agents(id);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS outbound_agent_id INTEGER REFERENCES agents(id);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS enable_inbound BOOLEAN DEFAULT true;
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS enable_outbound BOOLEAN DEFAULT true;
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS enable_krisp_noise_cancellation BOOLEAN DEFAULT true;
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
