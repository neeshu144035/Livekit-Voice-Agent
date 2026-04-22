ALTER TABLE calls ADD COLUMN room_name VARCHAR(100);
ALTER TABLE calls ADD COLUMN call_type VARCHAR(20) DEFAULT 'web';
ALTER TABLE calls ADD COLUMN direction VARCHAR(20) DEFAULT 'outbound';
ALTER TABLE transcripts ADD COLUMN stt_latency_ms INTEGER;
ALTER TABLE transcripts ADD COLUMN llm_latency_ms INTEGER;
ALTER TABLE transcripts ADD COLUMN tts_latency_ms INTEGER;
CREATE TABLE IF NOT EXISTS functions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    method VARCHAR(10) DEFAULT 'POST',
    url VARCHAR(500) NOT NULL,
    timeout_ms INTEGER DEFAULT 120000,
    headers JSON DEFAULT '{}'::json,
    query_params JSON DEFAULT '{}'::json,
    parameters_schema JSON DEFAULT '{}'::json,
    variables JSON DEFAULT '{}'::json,
    speak_during_execution BOOLEAN DEFAULT FALSE,
    speak_after_execution BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_functions_agent_id ON functions(agent_id);
