import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.attributes import flag_modified

def get_database_url() -> str:
    """Get database URL from environment variable."""
    return os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5432/dashboard_db")

DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AgentModel(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    agent_name = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=False)
    llm_model = Column(String(50), default="moonshot-v1-8k")
    voice = Column(String(50), default="jessica")
    language = Column(String(10), default="en")
    twilio_number = Column(String(20), nullable=True)
    welcome_message_type = Column(String(50), default="user_speaks_first")
    welcome_message = Column(Text, nullable=True)
    max_call_duration = Column(Integer, default=1800)
    enable_recording = Column(Boolean, default=True)
    webhook_url = Column(String(500), nullable=True)
    custom_params = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CallModel(Base):
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(100), unique=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    room_name = Column(String(100), index=True)
    call_type = Column(String(20), default="web")
    direction = Column(String(20), default="outbound")
    status = Column(String(20), default="pending")
    from_number = Column(String(20), nullable=True)
    to_number = Column(String(20), nullable=True)
    twilio_call_sid = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    recording_url = Column(String(500), nullable=True)
    
    cost_usd = Column(Float, default=0.0)
    llm_cost = Column(Float, default=0.0)
    stt_cost = Column(Float, default=0.0)
    tts_cost = Column(Float, default=0.0)
    
    llm_tokens_in = Column(Integer, default=0)
    llm_tokens_out = Column(Integer, default=0)
    llm_model_used = Column(String(50), nullable=True)
    stt_duration_ms = Column(Integer, default=0)
    tts_characters = Column(Integer, default=0)
    
    transcript_summary = Column(Text, nullable=True)
    call_metadata = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_calls_status', 'status'),
        Index('idx_calls_agent_id', 'agent_id'),
    )


class TranscriptModel(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(100), index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_final = Column(Boolean, default=True)
    confidence = Column(Float, nullable=True)
    stt_latency_ms = Column(Integer, nullable=True)
    llm_latency_ms = Column(Integer, nullable=True)
    tts_latency_ms = Column(Integer, nullable=True)


class WebhookLogModel(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatAgentModel(Base):
    __tablename__ = "chat_agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=False)
    llm_model = Column(String(50), default="moonshot-v1-8k")
    language = Column(String(10), default="en")
    custom_params = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FunctionModel(Base):
    __tablename__ = "functions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    method = Column(String(10), default="POST")
    url = Column(String(500), nullable=False)
    timeout_ms = Column(Integer, default=120000)
    headers = Column(JSON, default={})
    query_params = Column(JSON, default={})
    parameters_schema = Column(JSON, default={})
    variables = Column(JSON, default={})
    speak_during_execution = Column(Boolean, default=False)
    speak_after_execution = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_functions_agent_id', 'agent_id'),
    )


class PhoneNumberModel(Base):
    __tablename__ = "phone_numbers"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    
    termination_uri = Column(String(100), nullable=True)
    sip_trunk_username = Column(String(50), nullable=True)
    sip_trunk_password = Column(String(100), nullable=True)
    
    twilio_account_sid = Column(String(50), nullable=True)
    twilio_auth_token = Column(String(100), nullable=True)
    twilio_sip_trunk_sid = Column(String(50), nullable=True)
    
    livekit_inbound_trunk_id = Column(String(50), nullable=True)
    livekit_outbound_trunk_id = Column(String(50), nullable=True)
    livekit_dispatch_rule_id = Column(String(50), nullable=True)
    livekit_sip_endpoint = Column(String(100), nullable=True)
    
    inbound_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    outbound_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    
    enable_inbound = Column(Boolean, default=True)
    enable_outbound = Column(Boolean, default=True)
    enable_krisp_noise_cancellation = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
__table_args__ = (
    Index('idx_phone_numbers_agent_id', 'inbound_agent_id'),
)


class SystemCapacity(Base):
    __tablename__ = "system_capacity"
    
    id = Column(Integer, primary_key=True, index=True)
    max_concurrent_calls = Column(Integer, default=10, nullable=False)
    current_concurrent_calls = Column(Integer, default=0, nullable=False)
    queue_enabled = Column(Boolean, default=True)
    max_queue_size = Column(Integer, default=50)
    current_queue_size = Column(Integer, default=0)
    avg_call_duration_seconds = Column(Float, default=120.0)
    peak_hours_start = Column(Integer, default=9)
    peak_hours_end = Column(Integer, default=18)
    auto_scale_enabled = Column(Boolean, default=False)
    scale_up_threshold = Column(Float, default=0.8)
    scale_down_threshold = Column(Float, default=0.3)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
