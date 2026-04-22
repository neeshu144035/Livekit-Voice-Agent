-- Add new columns for Twilio SIP Trunk configuration
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS termination_uri VARCHAR(100);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS sip_trunk_username VARCHAR(50);
ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS sip_trunk_password VARCHAR(100);
