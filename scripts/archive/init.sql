CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    llm_model VARCHAR(50) DEFAULT 'moonshot-v1-8k',
    twilio_number VARCHAR(20) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
