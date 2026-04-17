import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
# Default LiveKit settings
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
import json
import re
import uuid
import logging
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON, Index, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.attributes import flag_modified
import redis.asyncio as aioredis
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend-api")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5432/dashboard_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "ws://localhost:7880")

AUTH_ADMIN_EMAIL = (
    os.getenv("DASHBOARD_ADMIN_EMAIL")
    or os.getenv("ADMIN_EMAIL")
    or "team.oyik@gmail.com"
).strip().lower()
AUTH_ADMIN_PASSWORD = (
    os.getenv("DASHBOARD_ADMIN_PASSWORD")
    or os.getenv("ADMIN_PASSWORD")
    or os.getenv("AUTH_PASSWORD")
    or os.getenv("LIVEKIT_API_SECRET")
    or ""
)
AUTH_SESSION_SECRET = (
    os.getenv("AUTH_SESSION_SECRET")
    or os.getenv("DASHBOARD_SESSION_SECRET")
    or LIVEKIT_API_SECRET
    or "change-me"
)
AUTH_SESSION_COOKIE = os.getenv("AUTH_SESSION_COOKIE", "session_token")
AUTH_SESSION_MAX_AGE = int(os.getenv("AUTH_SESSION_MAX_AGE", "604800"))
AUTH_SECURE_COOKIES = os.getenv("AUTH_SECURE_COOKIES", "true").strip().lower() in {"1", "true", "yes", "on"}
STRICT_PROMPT_TOOL_FILTER = os.getenv("STRICT_PROMPT_TOOL_FILTER", "1").strip().lower() not in {"0", "false", "no", "off"}

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
    agent_name = Column(String(100), nullable=True)  # LiveKit agent name for dispatch
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
    call_type = Column(String(20), default="web")  # web, phone
    direction = Column(String(20), default="outbound")  # inbound, outbound
    status = Column(String(20), default="pending")  # pending, in-progress, completed, failed, error
    from_number = Column(String(20), nullable=True)
    to_number = Column(String(20), nullable=True)
    twilio_call_sid = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    recording_url = Column(String(500), nullable=True)
    
    # Cost tracking
    cost_usd = Column(Float, default=0.0)
    llm_cost = Column(Float, default=0.0)
    stt_cost = Column(Float, default=0.0)
    tts_cost = Column(Float, default=0.0)
    
    # Usage metrics
    llm_tokens_in = Column(Integer, default=0)
    llm_tokens_out = Column(Integer, default=0)
    llm_model_used = Column(String(50), nullable=True)
    stt_duration_ms = Column(Integer, default=0)
    tts_characters = Column(Integer, default=0)
    
    # Transcript summary (stored for quick display without joining)
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
    llm_model = Column(String(50), default="gpt-4o-mini")
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
    """Model for storing phone numbers with Twilio SIP configuration"""
    __tablename__ = "phone_numbers"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)  # E.164 format: +1234567890
    description = Column(String(255), nullable=True)
    
    # Twilio SIP Trunk Configuration (Retell-style)
    termination_uri = Column(String(100), nullable=True)  # e.g., yourcompany.pstn.twilio.com
    sip_trunk_username = Column(String(50), nullable=True)  # e.g., osteo-twilio
    sip_trunk_password = Column(String(100), nullable=True)  # e.g., twilio123456
    
    # Legacy Twilio credentials (for outbound calls via Twilio REST)
    twilio_account_sid = Column(String(50), nullable=True)
    twilio_auth_token = Column(String(100), nullable=True)
    twilio_sip_trunk_sid = Column(String(50), nullable=True)
    
    # LiveKit SIP Configuration
    livekit_inbound_trunk_id = Column(String(50), nullable=True)
    livekit_outbound_trunk_id = Column(String(50), nullable=True)
    livekit_dispatch_rule_id = Column(String(50), nullable=True)
    livekit_sip_endpoint = Column(String(100), nullable=True)
    
    # Agent assignments
    inbound_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    outbound_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, configured, active, error
    error_message = Column(Text, nullable=True)
    
    # Settings
    enable_inbound = Column(Boolean, default=True)
    enable_outbound = Column(Boolean, default=True)
    enable_krisp_noise_cancellation = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_phone_numbers_agent_id', 'inbound_agent_id'),
    )


Base.metadata.create_all(bind=engine)


VALID_LLM_MODELS = [
    'moonshot-v1-8k',
    'moonshot-v1-32k',
    'moonshot-v1-128k',
    'kimi-k2.5',
    'kimi-k2-thinking',
    'kimi-k2-instruct',
    'moonlight-16b-a3b',
    'gpt-4',
    'gpt-4.1',
    'gpt-4.1-mini',
    'gpt-4.1-nano',
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-3.5-turbo',
    'gpt-5.4',
    'gpt-5.4-pro',
    'gpt-5.2',
    'gpt-5.2-pro',
    'gpt-5.1',
    'gpt-5',
    'gpt-5-pro',
    'gpt-5-mini',
    'gpt-5-nano',
    'o1',
    'o1-pro',
    'o3',
    'o3-mini',
    'o4-mini',
]

VALID_VOICES = [
    'jessica', 'mark', 'sarah', 'michael', 'emma', 'james',
    'aura-asteria-en', 'aura-luna-en', 'aura-hera-en',
    'aura-orion-en', 'aura-perseus-en', 'aura-zeus-en',
]

VALID_LANGUAGES = [
    'en', 'en-US', 'en-GB', 'en-AU', 'en-IN', 'es', 'fr', 'de', 'it',
]

VALID_TTS_PROVIDERS = ["deepgram", "elevenlabs"]
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_v3"
VALID_CALL_DIRECTIONS = {"inbound", "outbound"}
DEFAULT_CALL_DIRECTION = "outbound"
ACTIVE_CALL_STATUSES = ("pending", "in-progress", "initiating", "dialing")
STALE_ACTIVE_CALL_SECONDS = int(os.getenv("STALE_ACTIVE_CALL_SECONDS", "7200"))
DEFAULT_LIVEKIT_WORKER_AGENT_NAME = (os.getenv("LIVEKIT_WORKER_AGENT_NAME", "sarah") or "sarah").strip() or "sarah"
PREFER_AGENT_SPECIFIC_DISPATCH = os.getenv("PREFER_AGENT_SPECIFIC_DISPATCH", "0").strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_AGENT_LLM_TEMPERATURE = 0.2
DEFAULT_AGENT_VOICE_SPEED = 1.0
MIN_AGENT_LLM_TEMPERATURE = 0.0
MAX_AGENT_LLM_TEMPERATURE = 1.5
MIN_AGENT_VOICE_SPEED = 0.8
MAX_AGENT_VOICE_SPEED = 1.2
FALLBACK_ELEVENLABS_TTS_RATE_PER_1K_CHARS = {
    # Fallback only, real billed cost should come from ElevenLabs usage API.
    "eleven_v3": 0.10,
    "eleven_flash_v2_5": 0.015,
    "eleven_turbo_v2_5": 0.030,
    "eleven_multilingual_v2": 0.030,
}

DEEPGRAM_VOICE_OPTIONS = [
    {"id": "aura-asteria-en", "name": "Asteria", "label": "Jessica (Asteria)", "accent": "UK", "gender": "Female"},
    {"id": "aura-luna-en", "name": "Luna", "label": "Sarah (Luna)", "accent": "UK", "gender": "Female"},
    {"id": "aura-hera-en", "name": "Hera", "label": "Emma (Hera)", "accent": "US", "gender": "Female"},
    {"id": "aura-orion-en", "name": "Orion", "label": "Mark (Orion)", "accent": "US", "gender": "Male"},
    {"id": "aura-perseus-en", "name": "Perseus", "label": "Michael (Perseus)", "accent": "US", "gender": "Male"},
    {"id": "aura-zeus-en", "name": "Zeus", "label": "James (Zeus)", "accent": "US", "gender": "Male"},
]

DEEPGRAM_VOICE_ALIASES = {
    "jessica": "aura-asteria-en",
    "mark": "aura-orion-en",
    "sarah": "aura-luna-en",
    "michael": "aura-perseus-en",
    "emma": "aura-hera-en",
    "james": "aura-zeus-en",
}


def get_elevenlabs_api_key() -> Optional[str]:
    return os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY")


def normalize_tts_provider(provider: Optional[str], voice: Optional[str]) -> str:
    candidate = (provider or "").strip().lower()
    if candidate in VALID_TTS_PROVIDERS:
        return candidate
    if voice and voice.startswith("eleven_"):
        return "elevenlabs"
    if voice and len(voice) >= 20 and voice.replace("_", "").replace("-", "").isalnum():
        return "elevenlabs"
    return DEFAULT_TTS_PROVIDER


def ensure_custom_params(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict(data or {})


def normalize_runtime_vars(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in data.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        normalized[key] = raw_value
    return normalized


def normalize_call_direction(value: Optional[str], default: str = DEFAULT_CALL_DIRECTION) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in VALID_CALL_DIRECTIONS:
        return candidate
    return default


def resolve_display_name(name: Optional[str], display_name: Optional[str]) -> str:
    candidate = (display_name if display_name is not None else name) or ""
    normalized = candidate.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="name/display_name must not be empty")
    return normalized


def normalize_phone_lookup(phone_number: Optional[str]) -> Optional[str]:
    candidate = str(phone_number or "").strip()
    if not candidate:
        return None

    candidate = re.sub(r"(?i)^phone\s+", "", candidate)
    candidate = re.sub(r"(?i)^(sip:|tel:)", "", candidate)
    candidate = candidate.split(";", 1)[0].split("?", 1)[0]
    if "@" in candidate:
        candidate = candidate.split("@", 1)[0]

    candidate = candidate.strip()
    if candidate.startswith("00"):
        candidate = f"+{candidate[2:]}"

    if candidate.startswith("+"):
        digits = re.sub(r"\D", "", candidate[1:])
        normalized = f"+{digits}" if digits else ""
    else:
        digits = re.sub(r"\D", "", candidate)
        normalized = f"+{digits}" if digits else ""

    return normalized or None


def find_phone_record_by_number(db: Session, phone_number: Optional[str]) -> tuple[Optional["PhoneNumberModel"], Optional[str]]:
    normalized_phone = normalize_phone_lookup(phone_number)
    if not normalized_phone:
        return None, None

    exact_match = (
        db.query(PhoneNumberModel)
        .filter(PhoneNumberModel.phone_number == normalized_phone)
        .first()
    )
    if exact_match:
        return exact_match, normalized_phone

    for row in db.query(PhoneNumberModel).all():
        if normalize_phone_lookup(row.phone_number) == normalized_phone:
            return row, normalized_phone

    return None, normalized_phone


def resolve_inbound_agent_id(
    db: Session,
    *,
    called_number: Optional[str] = None,
    sip_trunk_id: Optional[str] = None,
    room_name: Optional[str] = None,
    fallback_agent_id: Optional[int] = None,
) -> Dict[str, Any]:
    agent_id: Optional[int] = None
    source = ""
    phone_record: Optional["PhoneNumberModel"] = None
    normalized_called_number = normalize_phone_lookup(called_number)
    normalized_trunk_id = str(sip_trunk_id or "").strip()

    if normalized_called_number:
        phone_record, normalized_called_number = find_phone_record_by_number(db, normalized_called_number)
        if phone_record and phone_record.enable_inbound and phone_record.inbound_agent_id:
            agent_id = int(phone_record.inbound_agent_id)
            source = "phone_number"

    if not agent_id and normalized_trunk_id:
        phone_record = (
            db.query(PhoneNumberModel)
            .filter(PhoneNumberModel.livekit_inbound_trunk_id == normalized_trunk_id)
            .first()
        )
        if phone_record and phone_record.enable_inbound and phone_record.inbound_agent_id:
            agent_id = int(phone_record.inbound_agent_id)
            source = "inbound_trunk"

    if not agent_id:
        inbound_candidates = (
            db.query(PhoneNumberModel)
            .filter(
                PhoneNumberModel.enable_inbound == True,  # noqa: E712
                PhoneNumberModel.inbound_agent_id.isnot(None),
            )
            .all()
        )
        unique_candidates = sorted({int(row.inbound_agent_id) for row in inbound_candidates if row.inbound_agent_id is not None})
        if len(unique_candidates) == 1:
            agent_id = unique_candidates[0]
            source = "single_inbound_mapping"

    if not agent_id and room_name:
        try:
            parts = str(room_name).replace("-", "_").split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                agent_id = int(parts[1])
                source = "room_name"
        except Exception:
            pass

    if not agent_id and fallback_agent_id:
        try:
            agent_id = int(fallback_agent_id)
            source = "fallback_agent"
        except Exception:
            pass

    if not agent_id:
        default_agent = db.query(AgentModel).first()
        agent_id = default_agent.id if default_agent else 1
        source = "default_first_agent"

    return {
        "agent_id": agent_id,
        "source": source,
        "phone_record": phone_record,
        "normalized_called_number": normalized_called_number,
        "normalized_trunk_id": normalized_trunk_id or None,
    }


def normalize_call_direction_for_row(call: "CallModel") -> str:
    current = normalize_call_direction(getattr(call, "direction", None), default="")
    if current:
        return current
    call_id = str(getattr(call, "call_id", "") or "").lower()
    if call_id.startswith("inbound_"):
        return "inbound"
    if call_id.startswith("outbound_"):
        return "outbound"
    return DEFAULT_CALL_DIRECTION


def _is_stale_active_call(call: Optional["CallModel"]) -> bool:
    if not call:
        return False
    if (call.status or "").lower() not in ACTIVE_CALL_STATUSES:
        return False
    now = datetime.utcnow()
    started = call.started_at or call.created_at
    if started and (now - started).total_seconds() > STALE_ACTIVE_CALL_SECONDS:
        return True
    return False


def _infer_terminal_status_for_call(call: "CallModel", db: Session) -> tuple[str, Optional[str]]:
    current_status = str(call.status or "").strip().lower()
    if current_status in {"failed", "error"}:
        return ("failed" if current_status == "error" else current_status), call.error_message

    if (call.error_message or "").strip():
        return "failed", call.error_message

    direction = normalize_call_direction_for_row(call)
    duration = call.duration_seconds
    if duration is None and call.started_at and call.ended_at:
        duration = max(int((call.ended_at - call.started_at).total_seconds()), 0)
    if duration is None and call.ended_at and call.created_at:
        duration = max(int((call.ended_at - call.created_at).total_seconds()), 0)
    duration = int(duration or 0)

    has_usage = any(
        [
            (call.llm_tokens_in or 0) > 0,
            (call.llm_tokens_out or 0) > 0,
            (call.stt_duration_ms or 0) > 0,
            (call.tts_characters or 0) > 0,
        ]
    )
    has_cost = any(
        [
            (call.cost_usd or 0) > 0,
            (call.llm_cost or 0) > 0,
            (call.stt_cost or 0) > 0,
            (call.tts_cost or 0) > 0,
        ]
    )
    transcript_exists = (
        db.query(TranscriptModel.id)
        .filter(TranscriptModel.call_id == call.call_id)
        .first()
        is not None
    )

    # Outbound calls that end quickly with no media/usage are typically carrier/SIP failures.
    is_phone_call = (str(call.call_type or "").strip().lower() == "phone")

    if (
        is_phone_call
        and
        direction == "outbound"
        and duration <= 35
        and not has_usage
        and not has_cost
        and not transcript_exists
    ):
        return (
            "failed",
            "Call ended before audio/transcript was established (likely SIP INVITE/carrier failure).",
        )

    return "completed", None


def resolve_dispatch_agent_name(
    agent: Optional["AgentModel"] = None,
    requested_name: Optional[str] = None,
) -> str:
    if PREFER_AGENT_SPECIFIC_DISPATCH:
        explicit = (requested_name or "").strip()
        if explicit:
            return explicit
        if agent and (agent.agent_name or "").strip():
            return str(agent.agent_name).strip()
    return DEFAULT_LIVEKIT_WORKER_AGENT_NAME


def _coerce_agent_setting_float(
    value: Any,
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN guard
        return default
    if number < min_value:
        return min_value
    if number > max_value:
        return max_value
    return number


def resolve_agent_llm_temperature_from_params(custom_params: Dict[str, Any]) -> float:
    return _coerce_agent_setting_float(
        custom_params.get("llm_temperature"),
        default=DEFAULT_AGENT_LLM_TEMPERATURE,
        min_value=MIN_AGENT_LLM_TEMPERATURE,
        max_value=MAX_AGENT_LLM_TEMPERATURE,
    )


def resolve_agent_voice_speed_from_params(custom_params: Dict[str, Any]) -> float:
    return _coerce_agent_setting_float(
        custom_params.get("voice_speed"),
        default=DEFAULT_AGENT_VOICE_SPEED,
        min_value=MIN_AGENT_VOICE_SPEED,
        max_value=MAX_AGENT_VOICE_SPEED,
    )


def resolve_agent_llm_temperature(agent: AgentModel) -> float:
    return resolve_agent_llm_temperature_from_params(ensure_custom_params(agent.custom_params))


def resolve_agent_voice_speed(agent: AgentModel) -> float:
    return resolve_agent_voice_speed_from_params(ensure_custom_params(agent.custom_params))


def _normalize_tool_speech_flags(
    speak_during_execution: bool,
    speak_after_execution: bool,
    *,
    fallback_after: bool = True,
) -> tuple[bool, bool]:
    during = bool(speak_during_execution)
    after = bool(speak_after_execution)
    if during ^ after:
        return during, after
    if fallback_after:
        return False, True
    return False, False


def _validate_tool_speech_flags_or_400(
    speak_during_execution: bool,
    speak_after_execution: bool,
) -> tuple[bool, bool]:
    during = bool(speak_during_execution)
    after = bool(speak_after_execution)
    if during == after:
        raise HTTPException(
            status_code=400,
            detail="Exactly one of speak_during_execution or speak_after_execution must be true.",
        )
    return during, after


def _tool_speech_instruction_line(func_cfg: Dict[str, Any]) -> str:
    tool_name = str(func_cfg.get("name", "")).strip().replace(" ", "_").lower() or "tool"
    during, after = _normalize_tool_speech_flags(
        func_cfg.get("speak_during_execution", False),
        func_cfg.get("speak_after_execution", True),
        fallback_after=True,
    )
    if during:
        return (
            f"- `{tool_name}`: first tell the caller what you are checking/doing, "
            "then call the tool, then give a concise result summary."
        )
    if after:
        return (
            f"- `{tool_name}`: call silently first, then explain only the result after the tool finishes."
        )
    return f"- `{tool_name}`: default to concise post-tool result only."


def _build_tool_speech_guidance_block(runtime_functions: List[Dict[str, Any]]) -> str:
    if not runtime_functions:
        return ""
    lines = [_tool_speech_instruction_line(fn) for fn in runtime_functions if fn.get("name")]
    if not lines:
        return ""
    return (
        "Tool speech behavior (must follow per tool):\n"
        + "\n".join(lines)
    )


def _build_effective_system_prompt(base_prompt: str, runtime_functions: List[Dict[str, Any]]) -> str:
    prompt = (base_prompt or "").strip()
    guidance = _build_tool_speech_guidance_block(runtime_functions)
    if not guidance:
        return prompt
    if not prompt:
        return guidance
    return f"{prompt}\n\n{guidance}"


def extract_agent_tts_settings(agent: AgentModel) -> Dict[str, Optional[str]]:
    custom_params = ensure_custom_params(agent.custom_params)
    provider = normalize_tts_provider(custom_params.get("tts_provider"), agent.voice)
    model = custom_params.get("tts_model")
    if provider == "elevenlabs" and not model:
        model = DEFAULT_ELEVENLABS_MODEL
    return {"tts_provider": provider, "tts_model": model}


def serialize_agent(agent: AgentModel) -> Dict[str, Any]:
    tts = extract_agent_tts_settings(agent)
    custom_params = ensure_custom_params(agent.custom_params)
    return {
        "id": agent.id,
        "name": agent.name,
        "display_name": agent.name,
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "voice": agent.voice,
        "language": agent.language,
        "twilio_number": agent.twilio_number,
        "welcome_message_type": agent.welcome_message_type,
        "welcome_message": agent.welcome_message,
        "max_call_duration": agent.max_call_duration,
        "enable_recording": agent.enable_recording,
        "webhook_url": agent.webhook_url,
        "custom_params": custom_params,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "tts_provider": tts["tts_provider"],
        "tts_model": tts["tts_model"],
        "llm_temperature": resolve_agent_llm_temperature_from_params(custom_params),
        "voice_speed": resolve_agent_voice_speed_from_params(custom_params),
    }


class AgentCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    agent_name: Optional[str] = None  # LiveKit agent name for dispatch
    system_prompt: str
    llm_model: str = "moonshot-v1-8k"
    voice: str = "jessica"
    tts_provider: Optional[str] = DEFAULT_TTS_PROVIDER
    tts_model: Optional[str] = None
    language: str = "en"
    twilio_number: Optional[str] = None
    welcome_message_type: Optional[str] = "user_speaks_first"
    welcome_message: Optional[str] = None
    max_call_duration: int = 1800
    enable_recording: bool = True
    webhook_url: Optional[str] = None
    llm_temperature: Optional[float] = DEFAULT_AGENT_LLM_TEMPERATURE
    voice_speed: Optional[float] = DEFAULT_AGENT_VOICE_SPEED
    custom_params: Dict[str, Any] = {}

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    agent_name: Optional[str] = None  # LiveKit agent name for dispatch
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    voice: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_model: Optional[str] = None
    language: Optional[str] = None
    twilio_number: Optional[str] = None
    welcome_message_type: Optional[str] = None
    welcome_message: Optional[str] = None
    max_call_duration: Optional[int] = None
    enable_recording: Optional[bool] = None
    webhook_url: Optional[str] = None
    llm_temperature: Optional[float] = None
    voice_speed: Optional[float] = None
    custom_params: Optional[Dict[str, Any]] = None

    def validate_llm_model(cls, v):
        if v not in VALID_LLM_MODELS:
            raise ValueError(f'Invalid llm_model. Must be one of: {", ".join(VALID_LLM_MODELS)}')
        return v

    def validate_voice(cls, v):
        if v is None:
            return v
        if v in VALID_VOICES:
            return v
        if len(v) > 20:
            return v
        raise ValueError(f'Invalid voice. Must be one of: {", ".join(VALID_VOICES)}')

    def validate_language(cls, v):
        if v not in VALID_LANGUAGES:
            raise ValueError(f'Invalid language. Must be one of: {", ".join(VALID_LANGUAGES)}')
        return v


class AgentResponse(BaseModel):
    id: int
    name: str
    display_name: str
    agent_name: Optional[str]  # LiveKit agent name for dispatch
    system_prompt: str
    llm_model: str
    voice: str
    tts_provider: str = DEFAULT_TTS_PROVIDER
    tts_model: Optional[str] = None
    language: str
    twilio_number: Optional[str]
    welcome_message_type: Optional[str]
    welcome_message: Optional[str]
    max_call_duration: int
    enable_recording: bool
    webhook_url: Optional[str]
    llm_temperature: float = DEFAULT_AGENT_LLM_TEMPERATURE
    voice_speed: float = DEFAULT_AGENT_VOICE_SPEED
    custom_params: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CallCreate(BaseModel):
    agent_id: int
    call_type: str = "web"
    direction: Optional[str] = DEFAULT_CALL_DIRECTION
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CallResponse(BaseModel):
    id: int
    call_id: str
    agent_id: int
    room_name: Optional[str]
    call_type: str
    direction: str
    status: str
    from_number: Optional[str]
    to_number: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    recording_url: Optional[str]
    cost_usd: float
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TranscriptEntry(BaseModel):
    role: str
    content: str
    is_final: bool = True
    confidence: Optional[float] = None
    stt_latency_ms: Optional[int] = None
    llm_latency_ms: Optional[int] = None
    tts_latency_ms: Optional[int] = None


class FunctionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    method: str = "POST"
    url: str
    timeout_ms: int = 120000
    headers: Dict[str, str] = {}
    query_params: Dict[str, str] = {}
    parameters_schema: Dict[str, Any] = {}
    variables: Dict[str, str] = {}
    speak_during_execution: bool = False
    speak_after_execution: bool = True


class FunctionResponse(BaseModel):
    id: int
    agent_id: int
    name: str
    description: Optional[str]
    method: str
    url: str
    timeout_ms: int
    headers: Dict[str, str]
    query_params: Dict[str, str]
    parameters_schema: Dict[str, Any]
    variables: Dict[str, str]
    speak_during_execution: bool
    speak_after_execution: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Phone Number Models for Twilio SIP Integration
class PhoneNumberCreate(BaseModel):
    phone_number: str  # E.164 format: +1234567890
    description: Optional[str] = None
    
    # Twilio SIP Trunk Configuration (Retell-style)
    termination_uri: Optional[str] = None  # e.g., yourcompany.pstn.twilio.com
    sip_trunk_username: Optional[str] = None  # e.g., osteo-twilio
    sip_trunk_password: Optional[str] = None  # e.g., twilio123456
    
    # Legacy Twilio credentials (for outbound calls via Twilio REST)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_sip_trunk_sid: Optional[str] = None
    
    inbound_agent_id: Optional[int] = None
    outbound_agent_id: Optional[int] = None
    enable_inbound: bool = True
    enable_outbound: bool = True
    enable_krisp_noise_cancellation: bool = True


class PhoneNumberUpdate(BaseModel):
    description: Optional[str] = None
    
    # Twilio SIP Trunk Configuration (Retell-style)
    termination_uri: Optional[str] = None
    sip_trunk_username: Optional[str] = None
    sip_trunk_password: Optional[str] = None
    
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_sip_trunk_sid: Optional[str] = None
    inbound_agent_id: Optional[int] = None
    outbound_agent_id: Optional[int] = None
    enable_inbound: Optional[bool] = None
    enable_outbound: Optional[bool] = None
    enable_krisp_noise_cancellation: Optional[bool] = None
    livekit_dispatch_rule_id: Optional[str] = None


class PhoneNumberResponse(BaseModel):
    id: int
    phone_number: str
    description: Optional[str]
    
    # Twilio SIP Trunk Configuration
    termination_uri: Optional[str]
    sip_trunk_username: Optional[str]
    
    twilio_account_sid: Optional[str]
    twilio_sip_trunk_sid: Optional[str]
    livekit_inbound_trunk_id: Optional[str]
    livekit_outbound_trunk_id: Optional[str]
    livekit_dispatch_rule_id: Optional[str]
    livekit_sip_endpoint: Optional[str]
    inbound_agent_id: Optional[int]
    outbound_agent_id: Optional[int]
    status: str
    error_message: Optional[str]
    enable_inbound: bool
    enable_outbound: bool
    enable_krisp_noise_cancellation: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Include agent names for response
    inbound_agent_name: Optional[str] = None
    outbound_agent_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OutboundCallRequest(BaseModel):
    to_number: str  # E.164 format
    phone_number_id: Optional[int] = None  # Optional, can be passed in body
    runtime_vars: Dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    email: str
    password: str


app = FastAPI(title="Voice AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


redis_client = None


async def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
        except:
            pass
    return redis_client


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_session_token(email: str) -> str:
    now = int(time.time())
    nonce = secrets.token_urlsafe(12)
    payload = f"{email}:{now}:{nonce}"
    signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def _verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    parts = token.split(":")
    if len(parts) != 4:
        return None
    email, issued_at_raw, nonce, signature = parts
    payload = f"{email}:{issued_at_raw}:{nonce}"
    expected_signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        issued_at = int(issued_at_raw)
    except ValueError:
        return None
    age_seconds = int(time.time()) - issued_at
    if age_seconds < 0 or age_seconds > AUTH_SESSION_MAX_AGE:
        return None
    return {"id": 1, "email": email}


def generate_livekit_token(room_name: str, identity: str, name: str = None) -> str:
    from livekit import api
    
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity)
    token.with_name(name or identity)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    ))
    return token.to_jwt()


async def send_webhook(webhook_url: str, event_type: str, payload: dict, db: Session):
    if not webhook_url:
        return None, "No webhook URL"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json={
                    "event": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": payload
                }
            )
            
            log = WebhookLogModel(
                event_type=event_type,
                payload=payload,
                response_status=response.status_code,
                response_body=response.text[:1000] if response.text else None
            )
            db.add(log)
            db.commit()
            
            return response.status_code, response.text
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        log = WebhookLogModel(
            event_type=event_type,
            payload=payload,
            response_status=None,
            response_body=str(e)
        )
        db.add(log)
        db.commit()
        return None, str(e)


@app.on_event("startup")
async def startup_event():
    global redis_client
    try:
        redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
    except:
        logger.warning("Redis not available")
    logger.info("Backend API started")


@app.get("/health")
async def health_check():
    redis_ok = False
    try:
        r = await get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except:
        pass
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "version": "2.0.0",
        "livekit_url": LIVEKIT_URL,
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/health")
async def health_check_api_alias():
    return await health_check()


@app.post("/api/login")
async def login(payload: LoginRequest, response: Response):
    if not AUTH_ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    email = (payload.email or "").strip().lower()
    password = payload.password or ""
    email_ok = hmac.compare_digest(email, AUTH_ADMIN_EMAIL)
    password_ok = hmac.compare_digest(password, AUTH_ADMIN_PASSWORD)
    if not (email_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    session_token = _create_session_token(email)
    response.set_cookie(
        key=AUTH_SESSION_COOKIE,
        value=session_token,
        max_age=AUTH_SESSION_MAX_AGE,
        httponly=True,
        secure=AUTH_SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
    return {
        "success": True,
        "message": "Login successful",
        "user": {"id": 1, "email": email},
        "session_token": session_token,
    }


@app.post("/login", include_in_schema=False)
async def login_alias(payload: LoginRequest, response: Response):
    return await login(payload, response)


@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=AUTH_SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=AUTH_SECURE_COOKIES,
        samesite="lax",
    )
    return {"success": True, "message": "Logged out"}


@app.post("/logout", include_in_schema=False)
async def logout_alias(response: Response):
    return await logout(response)


@app.get("/api/me")
async def me(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    user = _verify_session_token(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"success": True, "user": user}


@app.get("/me", include_in_schema=False)
async def me_alias(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    return await me(session_token)


@app.post("/api/agents/", response_model=AgentResponse, status_code=201)
async def create_agent(agent: AgentCreate, db: Session = Depends(get_database)):
    provider = normalize_tts_provider(agent.tts_provider, agent.voice)
    if agent.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if provider == "deepgram" and agent.voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {', '.join(VALID_VOICES)}")
    if provider not in VALID_TTS_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid tts_provider. Must be one of: {', '.join(VALID_TTS_PROVIDERS)}")
    if provider == "elevenlabs" and not agent.voice:
        raise HTTPException(status_code=400, detail="voice must be a valid ElevenLabs voice ID when tts_provider=elevenlabs")
    if agent.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    resolved_name = resolve_display_name(agent.name, agent.display_name)

    custom_params = ensure_custom_params(agent.custom_params)
    custom_params["tts_provider"] = provider
    if provider == "elevenlabs":
        custom_params["tts_model"] = agent.tts_model or custom_params.get("tts_model") or DEFAULT_ELEVENLABS_MODEL
    elif agent.tts_model:
        custom_params["tts_model"] = agent.tts_model
    else:
        custom_params.pop("tts_model", None)
    custom_params["llm_temperature"] = _coerce_agent_setting_float(
        agent.llm_temperature,
        default=DEFAULT_AGENT_LLM_TEMPERATURE,
        min_value=MIN_AGENT_LLM_TEMPERATURE,
        max_value=MAX_AGENT_LLM_TEMPERATURE,
    )
    custom_params["voice_speed"] = _coerce_agent_setting_float(
        agent.voice_speed,
        default=DEFAULT_AGENT_VOICE_SPEED,
        min_value=MIN_AGENT_VOICE_SPEED,
        max_value=MAX_AGENT_VOICE_SPEED,
    )
    
    db_agent = AgentModel(
        name=resolved_name,
        agent_name=agent.agent_name,
        system_prompt=agent.system_prompt,
        llm_model=agent.llm_model,
        voice=agent.voice,
        language=agent.language,
        twilio_number=agent.twilio_number,
        welcome_message_type=agent.welcome_message_type,
        welcome_message=agent.welcome_message,
        max_call_duration=agent.max_call_duration,
        enable_recording=agent.enable_recording,
        webhook_url=agent.webhook_url,
        custom_params=custom_params,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return serialize_agent(db_agent)


@app.get("/api/agents/list-simple")
async def list_agents_simple(db: Session = Depends(get_database)):
    """List all agents in simple format (id and name) for dropdowns"""
    agents = db.query(AgentModel).order_by(AgentModel.name).all()
    return [{"id": a.id, "name": a.name} for a in agents]


@app.get("/api/agents/", response_model=List[AgentResponse])
async def list_agents(db: Session = Depends(get_database)):
    agents = db.query(AgentModel).order_by(AgentModel.created_at.desc()).all()
    return [serialize_agent(agent) for agent in agents]


@app.get("/api/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return serialize_agent(agent)


@app.patch("/api/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent_update: AgentUpdate, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent_update.llm_model is not None and agent_update.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if agent_update.language is not None and agent_update.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    current_tts = extract_agent_tts_settings(agent)
    new_voice = agent_update.voice if agent_update.voice is not None else agent.voice
    new_provider = normalize_tts_provider(agent_update.tts_provider, new_voice)
    if new_provider not in VALID_TTS_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid tts_provider. Must be one of: {', '.join(VALID_TTS_PROVIDERS)}")
    if new_provider == "deepgram" and new_voice and new_voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {', '.join(VALID_VOICES)}")
    if new_provider == "elevenlabs" and not new_voice:
        raise HTTPException(status_code=400, detail="voice must be provided for ElevenLabs")

    update_data = agent_update.dict(exclude_unset=True)
    update_data.pop("tts_provider", None)
    update_data.pop("tts_model", None)
    update_data.pop("llm_temperature", None)
    update_data.pop("voice_speed", None)
    incoming_display_name = update_data.pop("display_name", None)
    if incoming_display_name is not None and "name" not in update_data:
        update_data["name"] = resolve_display_name(agent.name, incoming_display_name)
    elif "name" in update_data:
        update_data["name"] = resolve_display_name(update_data.get("name"), incoming_display_name)

    for field, value in update_data.items():
        if value is not None:
            setattr(agent, field, value)

    custom_params = ensure_custom_params(agent.custom_params)
    if agent_update.custom_params is not None:
        custom_params = ensure_custom_params(agent_update.custom_params)
    custom_params["tts_provider"] = new_provider

    resolved_tts_model = agent_update.tts_model
    if resolved_tts_model is None and new_provider == "elevenlabs":
        resolved_tts_model = current_tts.get("tts_model") or custom_params.get("tts_model") or DEFAULT_ELEVENLABS_MODEL
    if resolved_tts_model:
        custom_params["tts_model"] = resolved_tts_model
    elif new_provider == "deepgram":
        custom_params.pop("tts_model", None)

    if agent_update.llm_temperature is not None:
        custom_params["llm_temperature"] = _coerce_agent_setting_float(
            agent_update.llm_temperature,
            default=DEFAULT_AGENT_LLM_TEMPERATURE,
            min_value=MIN_AGENT_LLM_TEMPERATURE,
            max_value=MAX_AGENT_LLM_TEMPERATURE,
        )
    else:
        custom_params["llm_temperature"] = resolve_agent_llm_temperature_from_params(custom_params)

    if agent_update.voice_speed is not None:
        custom_params["voice_speed"] = _coerce_agent_setting_float(
            agent_update.voice_speed,
            default=DEFAULT_AGENT_VOICE_SPEED,
            min_value=MIN_AGENT_VOICE_SPEED,
            max_value=MAX_AGENT_VOICE_SPEED,
        )
    else:
        custom_params["voice_speed"] = resolve_agent_voice_speed_from_params(custom_params)

    agent.custom_params = custom_params
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return serialize_agent(agent)


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        # Collect all related call IDs for transcript/webhook cleanup first.
        call_id_rows = (
            db.query(CallModel.call_id)
            .filter(CallModel.agent_id == agent_id)
            .all()
        )
        call_ids = [row[0] for row in call_id_rows if row and row[0]]

        deleted_transcripts = 0
        deleted_webhook_logs = 0
        if call_ids:
            deleted_transcripts = (
                db.query(TranscriptModel)
                .filter(TranscriptModel.call_id.in_(call_ids))
                .delete(synchronize_session=False)
            )
            deleted_webhook_logs = (
                db.query(WebhookLogModel)
                .filter(WebhookLogModel.call_id.in_(call_ids))
                .delete(synchronize_session=False)
            )

        deleted_calls = (
            db.query(CallModel)
            .filter(CallModel.agent_id == agent_id)
            .delete(synchronize_session=False)
        )

        deleted_functions = (
            db.query(FunctionModel)
            .filter(FunctionModel.agent_id == agent_id)
            .delete(synchronize_session=False)
        )

        unlinked_phone_numbers = (
            db.query(PhoneNumberModel)
            .filter(
                or_(
                    PhoneNumberModel.inbound_agent_id == agent_id,
                    PhoneNumberModel.outbound_agent_id == agent_id,
                )
            )
            .update(
                {
                    PhoneNumberModel.inbound_agent_id: None,
                    PhoneNumberModel.outbound_agent_id: None,
                },
                synchronize_session=False,
            )
        )

        db.delete(agent)
        db.commit()

        return {
            "message": "Agent deleted successfully",
            "cleanup": {
                "functions_deleted": deleted_functions,
                "calls_deleted": deleted_calls,
                "transcripts_deleted": deleted_transcripts,
                "webhook_logs_deleted": deleted_webhook_logs,
                "phone_numbers_unlinked": unlinked_phone_numbers,
            },
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")


class AgentDuplicateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@app.post("/api/agents/{agent_id}/duplicate", response_model=AgentResponse, status_code=201)
async def duplicate_agent(agent_id: int, request: AgentDuplicateRequest, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    new_agent = AgentModel(
        name=request.name,
        agent_name=agent.agent_name,
        system_prompt=agent.system_prompt,
        llm_model=agent.llm_model,
        voice=agent.voice,
        language=agent.language,
        twilio_number=agent.twilio_number,
        welcome_message_type=agent.welcome_message_type,
        welcome_message=agent.welcome_message,
        max_call_duration=agent.max_call_duration,
        enable_recording=agent.enable_recording,
        webhook_url=agent.webhook_url,
        custom_params=agent.custom_params if isinstance(agent.custom_params, dict) else {},
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    # Copy all functions from the original agent
    original_functions = db.query(FunctionModel).filter(FunctionModel.agent_id == agent_id).all()
    for func in original_functions:
        new_function = FunctionModel(
            agent_id=new_agent.id,
            name=func.name,
            description=func.description,
            method=func.method,
            url=func.url,
            timeout_ms=func.timeout_ms,
            headers=func.headers if isinstance(func.headers, dict) else {},
            query_params=func.query_params if isinstance(func.query_params, dict) else {},
            parameters_schema=func.parameters_schema if isinstance(func.parameters_schema, dict) else {},
            variables=func.variables if isinstance(func.variables, dict) else {},
            speak_during_execution=func.speak_during_execution,
            speak_after_execution=func.speak_after_execution,
        )
        db.add(new_function)
    
    db.commit()
    db.refresh(new_agent)
    return serialize_agent(new_agent)


@app.get("/api/tts/providers")
async def get_tts_providers():
    eleven_api_key = get_elevenlabs_api_key()
    return {
        "providers": [
            {
                "id": "deepgram",
                "name": "Deepgram",
                "available": True,
            },
            {
                "id": "elevenlabs",
                "name": "ElevenLabs",
                "available": bool(eleven_api_key),
                "missing_env": [] if eleven_api_key else ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"],
            },
        ]
    }


@app.get("/api/tts/models")
async def get_tts_models(provider: str = DEFAULT_TTS_PROVIDER):
    provider = normalize_tts_provider(provider, None)
    if provider == "deepgram":
        return {
            "provider": "deepgram",
            "default_model": None,
            "models": [],
        }

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {
            "provider": "elevenlabs",
            "available": False,
            "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"],
            "default_model": DEFAULT_ELEVENLABS_MODEL,
            "models": [],
        }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.elevenlabs.io/v1/models",
                headers={"xi-api-key": eleven_api_key},
            )
            resp.raise_for_status()
            rows = resp.json() or []
    except Exception as e:
        logger.error(f"Failed to fetch ElevenLabs models: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch ElevenLabs models")

    models = []
    for row in rows:
        if not row.get("can_do_text_to_speech"):
            continue
        langs = row.get("languages") or []
        models.append(
            {
                "id": row.get("model_id"),
                "name": row.get("name") or row.get("model_id"),
                "description": row.get("description"),
                "character_cost_multiplier": (row.get("model_rates") or {}).get("character_cost_multiplier"),
                "languages": [lang.get("language_id") for lang in langs if isinstance(lang, dict) and lang.get("language_id")],
            }
        )

    models = [m for m in models if m.get("id")]
    models.sort(key=lambda m: m["name"].lower())
    return {
        "provider": "elevenlabs",
        "available": True,
        "missing_env": [],
        "default_model": DEFAULT_ELEVENLABS_MODEL,
        "models": models,
    }


@app.get("/api/tts/voices")
async def get_tts_voices(provider: str = DEFAULT_TTS_PROVIDER):
    provider = normalize_tts_provider(provider, None)
    if provider == "deepgram":
        options = []

        for alias, mapped_model in DEEPGRAM_VOICE_ALIASES.items():
            model_meta = next((v for v in DEEPGRAM_VOICE_OPTIONS if v["id"] == mapped_model), None)
            options.append(
                {
                    "id": alias,
                    "name": alias.title(),
                    "label": f"{alias.title()} ({model_meta['name'] if model_meta else mapped_model})",
                    "accent": model_meta["accent"] if model_meta else None,
                    "gender": model_meta["gender"] if model_meta else None,
                    "provider": "deepgram",
                    "deepgram_model": mapped_model,
                }
            )

        for option in DEEPGRAM_VOICE_OPTIONS:
            options.append(
                {
                    "id": option["id"],
                    "name": option["name"],
                    "label": option["label"],
                    "accent": option["accent"],
                    "gender": option["gender"],
                    "provider": "deepgram",
                    "deepgram_model": option["id"],
                }
            )

        return {"provider": "deepgram", "voices": options}

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {
            "provider": "elevenlabs",
            "available": False,
            "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"],
            "voices": [],
        }

    voices: List[Dict[str, Any]] = []
    page_token = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(5):
                params = {"page_size": 100}
                if page_token:
                    params["next_page_token"] = page_token

                resp = await client.get(
                    "https://api.elevenlabs.io/v2/voices",
                    params=params,
                    headers={"xi-api-key": eleven_api_key},
                )
                resp.raise_for_status()
                payload = resp.json() or {}
                voices.extend(payload.get("voices") or [])
                page_token = payload.get("next_page_token")
                if not page_token:
                    break
    except Exception as e:
        logger.error(f"Failed to fetch ElevenLabs voices: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch ElevenLabs voices")

    normalized = []
    for voice in voices:
        voice_id = voice.get("voice_id")
        if not voice_id:
            continue
        labels = voice.get("labels") or {}
        normalized.append(
            {
                "id": voice_id,
                "name": voice.get("name") or voice_id,
                "label": voice.get("name") or voice_id,
                "accent": labels.get("accent") or labels.get("language") or None,
                "gender": labels.get("gender") or None,
                "category": voice.get("category"),
                "provider": "elevenlabs",
            }
        )

    normalized.sort(key=lambda item: item["label"].lower())
    return {"provider": "elevenlabs", "available": True, "missing_env": [], "voices": normalized}


@app.get("/api/tts/voices/lookup")
async def lookup_tts_voice(provider: str = DEFAULT_TTS_PROVIDER, voice_id: str = ""):
    provider = normalize_tts_provider(provider, None)
    if provider != "elevenlabs":
        raise HTTPException(status_code=400, detail="Voice lookup is currently supported only for elevenlabs")

    voice_id = (voice_id or "").strip()
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id is required")

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {
            "provider": "elevenlabs",
            "available": False,
            "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"],
            "voice": None,
        }

    voices: List[Dict[str, Any]] = []
    page_token = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(10):
                params = {"page_size": 100}
                if page_token:
                    params["next_page_token"] = page_token

                resp = await client.get(
                    "https://api.elevenlabs.io/v2/voices",
                    params=params,
                    headers={"xi-api-key": eleven_api_key},
                )
                resp.raise_for_status()
                payload = resp.json() or {}
                page_voices = payload.get("voices") or []
                voices.extend(page_voices)

                match = next((v for v in page_voices if v.get("voice_id") == voice_id), None)
                if match:
                    labels = match.get("labels") or {}
                    normalized_voice = {
                        "id": match.get("voice_id") or voice_id,
                        "name": match.get("name") or (match.get("voice_id") or voice_id),
                        "label": match.get("name") or (match.get("voice_id") or voice_id),
                        "accent": labels.get("accent") or labels.get("language") or None,
                        "gender": labels.get("gender") or None,
                        "category": match.get("category"),
                        "provider": "elevenlabs",
                    }
                    return {"provider": "elevenlabs", "available": True, "missing_env": [], "voice": normalized_voice}

                page_token = payload.get("next_page_token")
                if not page_token:
                    break
    except Exception as e:
        logger.error(f"Failed to lookup ElevenLabs voice {voice_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to lookup ElevenLabs voices from provider")

    raise HTTPException(
        status_code=404,
        detail="Voice ID not found in this ElevenLabs account (or not accessible to this API key)",
    )


# Chat Agents API
class ChatAgentResponse(BaseModel):
    id: int
    name: str
    system_prompt: str
    llm_model: str
    language: str
    custom_params: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatAgentCreate(BaseModel):
    name: str
    system_prompt: str = ""
    llm_model: str = "gpt-4o-mini"
    language: str = "en"
    custom_params: dict = {}


class ChatAgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    language: Optional[str] = None
    custom_params: Optional[dict] = None


class ChatMessageRequest(BaseModel):
    message: str


class AgentTestChatRequest(BaseModel):
    message: Optional[str] = ""
    history: List[Dict[str, Any]] = []
    start: bool = False


def _resolve_openai_client_for_agent_model(model_name: str):
    import openai

    is_moonshot = any(k in (model_name or "").lower() for k in ["moonshot", "kimi", "moonlight"])
    base_url = "https://api.moonshot.cn/v1" if is_moonshot else None

    raw_key = os.getenv("MOONSHOT_API_KEY") if is_moonshot else os.getenv("OPENAI_API_KEY")
    api_key = (raw_key or "").strip() or (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI/Moonshot API key is not configured")

    return openai.OpenAI(api_key=api_key, base_url=base_url)


def _load_agent_runtime_functions(agent: AgentModel, db: Session) -> List[Dict[str, Any]]:
    rows = db.query(FunctionModel).filter(FunctionModel.agent_id == agent.id).all()
    runtime_functions: List[Dict[str, Any]] = []

    for row in rows:
        speak_during, speak_after = _normalize_tool_speech_flags(
            row.speak_during_execution,
            row.speak_after_execution,
            fallback_after=True,
        )
        runtime_functions.append(
            {
                "name": row.name,
                "description": row.description or "",
                "url": row.url or "",
                "method": (row.method or "POST").upper(),
                "timeout_ms": int(row.timeout_ms or 120000),
                "headers": row.headers or {},
                "parameters_schema": row.parameters_schema or {"type": "object", "properties": {}},
                "speak_during_execution": speak_during,
                "speak_after_execution": speak_after,
            }
        )

    custom_params = ensure_custom_params(agent.custom_params)
    builtin_cfg = custom_params.get("builtin_functions", {})

    transfer_cfg = builtin_cfg.get("builtin_transfer_call", {})
    if transfer_cfg.get("enabled"):
        transfer_phone = str((transfer_cfg.get("config") or {}).get("phone_number", "")).strip()
        transfer_speak_during, transfer_speak_after = _normalize_tool_speech_flags(
            transfer_cfg.get("speak_during_execution", True),
            transfer_cfg.get("speak_after_execution", False),
            fallback_after=False,
        )
        if not transfer_speak_during and not transfer_speak_after:
            transfer_speak_during, transfer_speak_after = True, False
        runtime_functions.append(
            {
                "name": "transfer_call",
                "description": (
                    "Use ONLY when the user explicitly asks to transfer/escalate/connect to a human agent. "
                    "Do not call this for regular Q&A."
                ),
                "url": "",
                "method": "POST",
                "timeout_ms": 120000,
                "headers": {},
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Target phone number in E.164 format, e.g. +447123456789",
                        }
                    },
                    "required": ["phone_number"],
                },
                "phone_number": transfer_phone,
                "speak_during_execution": transfer_speak_during,
                "speak_after_execution": transfer_speak_after,
            }
        )

    end_call_cfg = builtin_cfg.get("builtin_end_call", {})
    if end_call_cfg.get("enabled"):
        end_speak_during, end_speak_after = _normalize_tool_speech_flags(
            end_call_cfg.get("speak_during_execution", False),
            end_call_cfg.get("speak_after_execution", True),
            fallback_after=True,
        )
        runtime_functions.append(
            {
                "name": "end_call",
                "description": (
                    "Use ONLY when the user explicitly confirms they want to end/stop/hang up the conversation."
                ),
                "url": "",
                "method": "POST",
                "timeout_ms": 120000,
                "headers": {},
                "parameters_schema": {"type": "object", "properties": {}},
                "speak_during_execution": end_speak_during,
                "speak_after_execution": end_speak_after,
            }
        )

    return runtime_functions


def _to_openai_tool_definitions(runtime_functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for func in runtime_functions:
        fn_name = str(func.get("name", "")).strip().replace(" ", "_").lower()
        if not fn_name:
            continue
        speak_during, speak_after = _normalize_tool_speech_flags(
            func.get("speak_during_execution", False),
            func.get("speak_after_execution", True),
            fallback_after=True,
        )
        schema = func.get("parameters_schema") or {"type": "object", "properties": {}}
        base_description = (func.get("description") or "").strip() or fn_name
        if speak_during:
            behavior_hint = "Before calling this tool, tell the user what you are doing; then summarize the result."
        elif speak_after:
            behavior_hint = "Call this tool first, then speak only after receiving its result."
        else:
            behavior_hint = "Keep tool speech concise."
        description = f"{base_description} {behavior_hint}".strip()
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": description,
                    "parameters": schema,
                },
            }
        )
    return tools


def _normalize_tool_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _tool_aliases(tool_name: str) -> List[str]:
    normalized = _normalize_tool_name(tool_name)
    aliases = {
        tool_name or "",
        normalized,
        normalized.replace("_", " "),
    }
    if normalized == "call_transfer":
        aliases.update({"transfer_call", "transfer call"})
    elif normalized == "transfer_call":
        aliases.update({"call_transfer", "call transfer"})
    return [a for a in aliases if a]


def _tool_alias_pattern(alias: str) -> re.Pattern:
    words = [w for w in re.split(r"[^a-z0-9]+", alias.lower()) if w]
    if not words:
        return re.compile(r"$^")
    separator = r"[\s_\-\.:`'\"()\[\]{}<>]*"
    token = separator.join(re.escape(w) for w in words)
    return re.compile(rf"(?<![a-z0-9]){token}(?![a-z0-9])", re.IGNORECASE)


def _is_tool_mentioned_in_prompt(tool_name: str, prompt: str) -> bool:
    text = (prompt or "").lower()
    if not text:
        return False
    for alias in _tool_aliases(tool_name):
        if _tool_alias_pattern(alias).search(text):
            return True
    return False


def _filter_runtime_functions_by_prompt(
    runtime_functions: List[Dict[str, Any]],
    system_prompt: str,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    removed_names: List[str] = []
    for fn in runtime_functions or []:
        tool_name = str(fn.get("name", "")).strip()
        if tool_name and _is_tool_mentioned_in_prompt(tool_name, system_prompt):
            filtered.append(fn)
        else:
            removed_names.append(tool_name or "<unknown>")

    if removed_names:
        logger.info(
            "Prompt tool filter removed tools not referenced in system prompt: %s",
            removed_names,
        )
    return filtered


def _is_missing_runtime_arg(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _coerce_runtime_arg(expected_type: str, value: Any) -> tuple[bool, Any, str]:
    if expected_type == "string":
        if isinstance(value, str):
            return True, value.strip(), ""
        return True, str(value), ""

    if expected_type == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return True, value, ""
        if isinstance(value, float) and value.is_integer():
            return True, int(value), ""
        if isinstance(value, str):
            try:
                return True, int(value.strip()), ""
            except Exception:
                return False, None, "must be an integer"
        return False, None, "must be an integer"

    if expected_type == "number":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True, float(value), ""
        if isinstance(value, str):
            try:
                return True, float(value.strip()), ""
            except Exception:
                return False, None, "must be a number"
        return False, None, "must be a number"

    if expected_type == "boolean":
        if isinstance(value, bool):
            return True, value, ""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "y", "1"}:
                return True, True, ""
            if lowered in {"false", "no", "n", "0"}:
                return True, False, ""
        return False, None, "must be a boolean"

    if expected_type == "array":
        if isinstance(value, list):
            return True, value, ""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return True, parsed, ""
            except Exception:
                pass
        return False, None, "must be an array"

    if expected_type == "object":
        if isinstance(value, dict):
            return True, value, ""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return True, parsed, ""
            except Exception:
                pass
        return False, None, "must be an object"

    return True, value, ""


def _validate_and_normalize_runtime_args(
    func_cfg: Dict[str, Any],
    args: Dict[str, Any],
) -> tuple[Dict[str, Any], List[str]]:
    schema = func_cfg.get("parameters_schema") or {}
    if not isinstance(schema, dict):
        return args if isinstance(args, dict) else {}, []

    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    if not isinstance(properties, dict):
        properties = {}
    if not isinstance(required, list):
        required = []

    source_args = args if isinstance(args, dict) else {}
    normalized_args: Dict[str, Any] = {}
    errors: List[str] = []

    for prop_name, prop_schema in properties.items():
        prop_schema = prop_schema if isinstance(prop_schema, dict) else {}
        expected_type = str(prop_schema.get("type", "string")).strip().lower() or "string"

        raw_value = source_args.get(prop_name)
        if raw_value is None:
            fallback_key = str(prop_name).strip().replace(" ", "_").lower()
            raw_value = source_args.get(fallback_key)

        if _is_missing_runtime_arg(raw_value):
            if prop_name in required:
                errors.append(f"missing required parameter: {prop_name}")
            continue

        ok, coerced_value, err = _coerce_runtime_arg(expected_type, raw_value)
        if not ok:
            errors.append(f"invalid parameter {prop_name}: {err}")
            continue

        normalized_args[prop_name] = coerced_value

    for key, value in source_args.items():
        if key not in normalized_args and key not in properties and not _is_missing_runtime_arg(value):
            normalized_args[key] = value

    for req in required:
        if req not in normalized_args and req not in properties:
            errors.append(f"missing required parameter: {req}")

    return normalized_args, errors


def _safe_chat_completion_create(client, **kwargs):
    """Compatibility wrapper for models that require max_completion_tokens."""
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        message = str(exc)
        if (
            "temperature" in kwargs
            and "temperature" in message.lower()
            and ("unsupported value" in message.lower() or "only the default (1) value is supported" in message.lower())
        ):
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("temperature", None)
            return client.chat.completions.create(**retry_kwargs)
        if (
            "max_tokens" in kwargs
            and "max_completion_tokens" not in kwargs
            and "Unsupported parameter: 'max_tokens'" in message
        ):
            retry_kwargs = dict(kwargs)
            token_limit = retry_kwargs.pop("max_tokens", None)
            if token_limit is not None:
                retry_kwargs["max_completion_tokens"] = token_limit
            return client.chat.completions.create(**retry_kwargs)
        raise


async def _execute_agent_runtime_tool(func_cfg: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = str(func_cfg.get("name", "")).strip().replace(" ", "_").lower()
    normalized_args, validation_errors = _validate_and_normalize_runtime_args(func_cfg, args or {})
    if validation_errors:
        return {
            "success": False,
            "error": "Tool parameter validation failed",
            "details": validation_errors,
        }
    args = normalized_args

    if tool_name in ("transfer_call", "call_transfer"):
        configured_phone = str(func_cfg.get("phone_number", "")).strip()
        requested_phone = str((args or {}).get("phone_number", "")).strip()
        target_phone = configured_phone or requested_phone
        if not target_phone:
            return {"success": False, "error": "Transfer phone number is not configured"}
        return {
            "success": True,
            "action": "transfer_call",
            "phone_number": target_phone,
            "status": "test_chat_simulated",
        }

    if tool_name == "end_call":
        return {"success": True, "action": "end_call", "status": "test_chat_simulated"}

    url = str(func_cfg.get("url", "")).strip()
    if not url:
        return {"success": False, "error": "Function URL is empty"}

    method = str(func_cfg.get("method", "POST")).upper()
    timeout_sec = max(float(func_cfg.get("timeout_ms", 120000)) / 1000.0, 1.0)
    headers = func_cfg.get("headers") or {}

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            if method == "GET":
                resp = await client.get(url, params=args or {}, headers=headers)
            else:
                resp = await client.request(method, url, json=args or {}, headers=headers)
        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "response": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _generate_dynamic_welcome_text(agent: AgentModel, system_prompt: str) -> str:
    try:
        client = _resolve_openai_client_for_agent_model(agent.llm_model or "gpt-4o-mini")
        response = _safe_chat_completion_create(
            client,
            model=agent.llm_model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": (system_prompt or "").strip()},
                {
                    "role": "user",
                    "content": (
                        "Start of conversation. Generate one short natural first greeting "
                        "that follows your role and tone. Do not mention tools or internal logic."
                    ),
                },
            ],
            temperature=resolve_agent_llm_temperature(agent),
            max_tokens=80,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as e:
        logger.error(f"Failed to generate dynamic welcome text: {e}")
    return "Hello."


@app.post("/api/chat-agents/", response_model=ChatAgentResponse, status_code=201)
async def create_chat_agent(agent_data: ChatAgentCreate, db: Session = Depends(get_database)):
    db_agent = ChatAgentModel(
        name=agent_data.name,
        system_prompt=agent_data.system_prompt,
        llm_model=agent_data.llm_model,
        language=agent_data.language,
        custom_params=agent_data.custom_params,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent


@app.get("/api/chat-agents/", response_model=List[ChatAgentResponse])
async def list_chat_agents(db: Session = Depends(get_database)):
    return db.query(ChatAgentModel).order_by(ChatAgentModel.created_at.desc()).all()


@app.get("/api/chat-agents/{agent_id}", response_model=ChatAgentResponse)
async def get_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    return agent


@app.patch("/api/chat-agents/{agent_id}", response_model=ChatAgentResponse)
async def update_chat_agent(agent_id: int, agent_data: ChatAgentUpdate, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.system_prompt is not None:
        agent.system_prompt = agent_data.system_prompt
    if agent_data.llm_model is not None:
        agent.llm_model = agent_data.llm_model
    if agent_data.language is not None:
        agent.language = agent_data.language
    if agent_data.custom_params is not None:
        agent.custom_params = agent_data.custom_params
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@app.delete("/api/chat-agents/{agent_id}")
async def delete_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    db.delete(agent)
    db.commit()
    return {"message": "Chat agent deleted successfully"}


@app.post("/api/chat-agents/{agent_id}/chat")
async def chat_with_agent(agent_id: int, chat_data: ChatMessageRequest, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat agent not found")
    
    # Build messages for the LLM
    messages = []
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})
    messages.append({"role": "user", "content": chat_data.message})
    
    # Call OpenAI API
    try:
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return {"response": "OpenAI API key not configured. Please set OPENAI_API_KEY in environment."}
        
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = _safe_chat_completion_create(
            client,
            model=agent.llm_model,
            messages=messages,
            temperature=0.3,
            max_tokens=280,
        )
        
        return {"response": response.choices[0].message.content}
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return {"response": f"Sorry, I encountered an error: {str(e)}"}


@app.post("/api/agents/{agent_id}/test-chat")
async def test_chat_with_voice_agent(agent_id: int, payload: AgentTestChatRequest, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    runtime_functions = _load_agent_runtime_functions(agent, db)
    if STRICT_PROMPT_TOOL_FILTER:
        before_count = len(runtime_functions)
        runtime_functions = _filter_runtime_functions_by_prompt(runtime_functions, agent.system_prompt or "")
        logger.info(
            "Prompt tool filter enabled (test-chat): kept=%s removed=%s",
            len(runtime_functions),
            max(before_count - len(runtime_functions), 0),
        )
    effective_system_prompt = _build_effective_system_prompt(agent.system_prompt or "", runtime_functions)

    history = payload.history or []
    welcome_type = (agent.welcome_message_type or "user_speaks_first").strip().lower()
    welcome_text = (agent.welcome_message or "").strip()

    if payload.start and welcome_type == "agent_greets":
        first_reply = welcome_text or await _generate_dynamic_welcome_text(agent, effective_system_prompt)
        new_history = history + [{"role": "assistant", "content": first_reply}]
        return {"reply": first_reply, "events": [], "history": new_history}

    user_message = (payload.message or "").strip()
    if not user_message:
        return {"reply": "", "events": [], "history": history}

    messages: List[Dict[str, Any]] = []
    if effective_system_prompt:
        messages.append({"role": "system", "content": effective_system_prompt})

    for item in history:
        role = str(item.get("role", "")).strip().lower()
        if role not in {"user", "assistant", "tool"}:
            continue
        msg: Dict[str, Any] = {"role": role, "content": item.get("content", "")}
        if role == "assistant" and item.get("tool_calls"):
            msg["tool_calls"] = item.get("tool_calls")
        if role == "tool" and item.get("tool_call_id"):
            msg["tool_call_id"] = item.get("tool_call_id")
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    tool_defs = _to_openai_tool_definitions(runtime_functions)
    runtime_by_name = {
        str(f.get("name", "")).strip().replace(" ", "_").lower(): f
        for f in runtime_functions
    }

    # Keep fallback chat responsive on UI by limiting context size.
    max_history_messages = 14
    if len(messages) > max_history_messages + 2:
        system_messages = [m for m in messages if m.get("role") == "system"]
        non_system_messages = [m for m in messages if m.get("role") != "system"]
        messages = system_messages + non_system_messages[-max_history_messages:]

    client = _resolve_openai_client_for_agent_model(agent.llm_model or "gpt-4o-mini")
    llm_temperature = resolve_agent_llm_temperature(agent)
    events: List[Dict[str, Any]] = []
    final_reply = ""

    for _ in range(2):
        response = _safe_chat_completion_create(
            client,
            model=agent.llm_model or "gpt-4o-mini",
            messages=messages,
            tools=tool_defs or None,
            tool_choice="auto" if tool_defs else None,
            temperature=llm_temperature,
            max_tokens=260,
        )
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if tool_calls:
            assistant_tool_message = {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [],
            }

            for tc in tool_calls:
                tool_name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    parsed_args = {}

                assistant_tool_message["tool_calls"].append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": json.dumps(parsed_args)},
                    }
                )

            messages.append(assistant_tool_message)

            for tc in tool_calls:
                tool_name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    parsed_args = {}

                events.append({"type": "tool_call", "tool_name": tool_name, "args": parsed_args})
                func_cfg = runtime_by_name.get(str(tool_name).strip().lower())
                if not func_cfg:
                    tool_result = {"success": False, "error": f"Tool not found: {tool_name}"}
                else:
                    tool_result = await _execute_agent_runtime_tool(func_cfg, parsed_args)

                events.append({"type": "tool_response", "tool_name": tool_name, "response": tool_result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result),
                    }
                )
            continue

        final_reply = assistant_message.content or ""
        messages.append({"role": "assistant", "content": final_reply})
        break

    response_history = [m for m in messages if m.get("role") != "system"]
    return {"reply": final_reply, "events": events, "history": response_history}


@app.post("/api/calls/", response_model=CallResponse)
async def create_call(call_data: CallCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == call_data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    call_id = f"call_{uuid.uuid4().hex[:16]}"
    room_name = f"call_{call_data.agent_id}_{uuid.uuid4().hex[:8]}"
    
    db_call = CallModel(
        call_id=call_id,
        agent_id=call_data.agent_id,
        room_name=room_name,
        call_type=call_data.call_type,
        direction=normalize_call_direction(call_data.direction),
        status="pending",
        from_number=call_data.from_number,
        to_number=call_data.to_number,
        call_metadata=call_data.metadata
    )
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    
    return db_call


@app.get("/calls/", response_model=List[CallResponse])
async def list_calls(
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    call_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_database)
):
    query = db.query(CallModel)
    
    if agent_id:
        query = query.filter(CallModel.agent_id == agent_id)
    if status:
        query = query.filter(CallModel.status == status)
    if call_type:
        query = query.filter(CallModel.call_type == call_type)
    
    return query.order_by(CallModel.created_at.desc()).limit(limit).all()


@app.get("/calls/{call_id}", response_model=CallResponse)
async def get_call(call_id: str, db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@app.post("/api/calls/{call_id}/end")
async def end_call(call_id: str, db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    call.ended_at = datetime.utcnow()
    if call.started_at:
        call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())
    elif call.created_at:
        call.duration_seconds = int((call.ended_at - call.created_at).total_seconds())

    final_status, inferred_error = _infer_terminal_status_for_call(call, db)
    call.status = final_status
    if inferred_error and not (call.error_message or "").strip():
        call.error_message = inferred_error
    
    db.commit()

    # If runtime usage payload was missed, backfill from transcript and recompute costs.
    if _looks_like_missing_usage(call):
        if _backfill_usage_from_transcript_and_cost(call, db):
            db.commit()
            logger.info("Backfilled usage on end_call for call_id=%s", call_id)
    
    return {"message": "Call ended", "call_id": call_id}


@app.get("/calls/{call_id}/transcript")
async def get_transcript(call_id: str, db: Session = Depends(get_database)):
    transcripts = db.query(TranscriptModel).filter(
        TranscriptModel.call_id == call_id
    ).order_by(TranscriptModel.timestamp).all()
    
    return {
        "call_id": call_id,
        "entries": [
            {
                "role": t.role,
                "content": t.content,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "is_final": t.is_final,
                "confidence": t.confidence,
                "latency": {
                    "stt_ms": t.stt_latency_ms,
                    "llm_ms": t.llm_latency_ms,
                    "tts_ms": t.tts_latency_ms
                } if t.stt_latency_ms or t.llm_latency_ms or t.tts_latency_ms else None
            }
            for t in transcripts
        ]
    }


@app.post("/api/calls/{call_id}/transcript")
async def add_transcript(call_id: str, entry: TranscriptEntry, db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    transcript = TranscriptModel(
        call_id=call_id,
        role=entry.role,
        content=entry.content,
        is_final=entry.is_final,
        confidence=entry.confidence,
        stt_latency_ms=entry.stt_latency_ms,
        llm_latency_ms=entry.llm_latency_ms,
        tts_latency_ms=entry.tts_latency_ms
    )
    db.add(transcript)
    db.commit()
    
    if call.status == "pending":
        call.status = "in-progress"
        call.started_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Transcript added"}


@app.get("/api/token/{agent_id}")
async def get_token(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    room_name = f"call_{agent.id}_{uuid.uuid4().hex[:8]}"
    user_identity = f"user_{uuid.uuid4().hex[:8]}"
    
    token = generate_livekit_token(room_name, user_identity, f"User-{agent.id}")
    
    call_id = f"call_{agent.id}_{uuid.uuid4().hex[:16]}"
    db_call = CallModel(
        call_id=call_id,
        agent_id=agent.id,
        room_name=room_name,
        call_type="web",
        direction="outbound",
        status="pending"
    )
    db.add(db_call)
    db.commit()
    
    # Dispatch agent to the room
    try:
        http_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
        from livekit import api as livekit_api
        lk_api = livekit_api.LiveKitAPI(url=http_url, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        
        # Create room first
        room = await lk_api.room.create_room(
            livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,
                # Allow transfer scenarios (agent + active callee + transfer target)
                max_participants=4
            )
        )
        
        dispatch_agent_name = resolve_dispatch_agent_name(agent)
        dispatch = await lk_api.agent_dispatch.create_dispatch(
            livekit_api.CreateAgentDispatchRequest(
                agent_name=dispatch_agent_name,
                room=room_name,
                metadata=json.dumps({
                    "call_id": call_id,
                    "call_type": "web",
                    "user_identity": user_identity
                })
            )
        )
        logger.info(
            "Dispatched agent worker %s to room %s (configured agent_name=%s)",
            dispatch_agent_name,
            room_name,
            agent.agent_name,
        )
        
        await lk_api.aclose()
    except Exception as e:
        logger.error(f"Failed to dispatch agent: {e}")
    
    return {
        "token": token,
        "room_name": room_name,
        "call_id": call_id,
        "user_identity": user_identity,
        "livekit_url": os.getenv("LIVEKIT_WS_URL", "wss://13.135.81.172:7880"),
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "voice_id": agent.voice,
            "voice_speed": resolve_agent_voice_speed(agent),
            "llm_temperature": resolve_agent_llm_temperature(agent),
            "tts_provider": extract_agent_tts_settings(agent)["tts_provider"],
            "tts_model": extract_agent_tts_settings(agent)["tts_model"],
            "welcome_message": agent.welcome_message
        }
    }


@app.get("/api/analytics")
async def get_analytics(agent_id: Optional[int] = None, days: int = 7, db: Session = Depends(get_database)):
    from datetime import timedelta
    
    def get_duration(call):
        """Get duration from duration_seconds OR calculate from timestamps"""
        # First try stored duration
        dur = 0
        if call.duration_seconds:
            dur = call.duration_seconds
        # Calculate from ended_at - created_at for completed calls
        elif call.ended_at and call.created_at:
            delta = call.ended_at - call.created_at
            dur = int(delta.total_seconds())
        
        # Filter out unrealistic durations (> 1 hour for realistic stats)
        if dur > 3600:
            return 0
        return dur
    
    def calc_stats(calls_list, valid_calls=None, cost_calls=None):
        """Calculate stats for a list of calls
        - calls_list: all calls (for total count, completed count)
        - valid_calls: calls with actual duration (for duration calculation)
        - cost_calls: completed calls (for cost calculation - includes calls with no duration but have cost)
        """
        if valid_calls is None:
            valid_calls = calls_list
        if cost_calls is None:
            cost_calls = valid_calls
        total = len(calls_list)
        completed = len([c for c in calls_list if c.status == "completed"])
        failed = len([c for c in calls_list if c.status == "failed"])
        duration = sum([get_duration(c) for c in valid_calls])
        avg_dur = round(duration / completed) if completed > 0 else 0
        cost = sum([c.cost_usd or 0 for c in cost_calls])
        return {
            "total_calls": total,
            "completed_calls": completed,
            "failed_calls": failed,
            "success_rate": round((completed / total * 100), 1) if total > 0 else 0,
            "total_duration_seconds": duration,
            "average_duration_seconds": avg_dur,
            "total_cost_usd": round(cost, 4),
        }
    
    # Get all calls
    query = db.query(CallModel)
    if agent_id:
        query = query.filter(CallModel.agent_id == agent_id)
    all_calls = query.all()
    
    # Separate phone calls and web calls
    phone_calls = [c for c in all_calls if c.call_type == "phone"]
    web_calls = [c for c in all_calls if c.call_type == "web"]
    
    # Filter unrealistic durations (> 1 hour) - for duration calculation
    # Include calls with cost (even if duration calculation returns 0 due to null timestamps)
    MAX_DURATION = 3600
    # Valid calls: has valid duration (from stored or calculated) OR has cost
    valid_phone = [c for c in phone_calls if (get_duration(c) > 0 and get_duration(c) <= MAX_DURATION) or (c.cost_usd and c.cost_usd > 0)]
    valid_web = [c for c in web_calls if (get_duration(c) > 0 and get_duration(c) <= MAX_DURATION) or (c.cost_usd and c.cost_usd > 0)]
    
    # Completed calls (for cost calculation - include all)
    completed_phone = [c for c in phone_calls if c.status == "completed"]
    completed_web = [c for c in web_calls if c.status == "completed"]
    
    # All-time stats - use ALL calls for total, valid for duration, completed for cost
    phone_all_time = calc_stats(phone_calls, valid_phone, completed_phone)
    web_all_time = calc_stats(web_calls, valid_web, completed_web)
    
    # Period stats
    start_date = datetime.utcnow() - timedelta(days=days)
    phone_period = [c for c in phone_calls if c.created_at and c.created_at >= start_date]
    web_period = [c for c in web_calls if c.created_at and c.created_at >= start_date]
    phone_period_valid = [c for c in valid_phone if c.created_at and c.created_at >= start_date]
    web_period_valid = [c for c in valid_web if c.created_at and c.created_at >= start_date]
    phone_period_completed = [c for c in completed_phone if c.created_at and c.created_at >= start_date]
    web_period_completed = [c for c in completed_web if c.created_at and c.created_at >= start_date]
    
    return {
        "period_days": days,
        "phone": {
            "period": calc_stats(phone_period, phone_period_valid, phone_period_completed),
            "all_time": phone_all_time,
        },
        "web": {
            "period": calc_stats(web_period, web_period_valid, web_period_completed),
            "all_time": web_all_time,
        },
    }


@app.get("/api/debug/calls-count")
async def debug_calls_count(db: Session = Depends(get_database)):
    """Debug endpoint to check total calls in database"""
    total = db.query(CallModel).count()
    completed = db.query(CallModel).filter(CallModel.status == "completed").count()
    in_progress = db.query(CallModel).filter(CallModel.status == "in-progress").count()
    pending = db.query(CallModel).filter(CallModel.status == "pending").count()
    
    # Get sample of recent calls
    recent = db.query(CallModel).order_by(CallModel.created_at.desc()).limit(5).all()
    recent_data = [{
        "call_id": c.call_id,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_seconds": c.duration_seconds,
    } for c in recent]
    
    return {
        "total_calls": total,
        "completed": completed,
        "in_progress": in_progress,
        "pending": pending,
        "recent_calls": recent_data
    }


@app.get("/api/webhooks/logs")
async def get_webhook_logs(call_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100, db: Session = Depends(get_database)):
    query = db.query(WebhookLogModel)
    
    if call_id:
        query = query.filter(WebhookLogModel.call_id == call_id)
    if event_type:
        query = query.filter(WebhookLogModel.event_type == event_type)
    
    return query.order_by(WebhookLogModel.created_at.desc()).limit(limit).all()


@app.post("/api/calls/{call_id}/builtin-action")
async def execute_builtin_action(call_id: str, action: dict, db: Session = Depends(get_database)):
    """Execute a built-in system action (end_call, transfer_call)"""
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    action_type = action.get("action")
    params = action.get("parameters", {})
    
    if action_type == "end_call":
        # End the call immediately
        call.status = "completed"
        call.ended_at = datetime.utcnow()
        call.error_message = params.get("reason", "Ended by system")
        db.commit()
        
        return {
            "success": True,
            "action": "end_call",
            "call_id": call_id,
            "message": "Call ended successfully"
        }
    
    elif action_type == "transfer_call":
        phone_number = params.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="phone_number is required for transfer")
        
        # Store transfer info
        call.error_message = f"Transfer requested to: {phone_number}"
        db.commit()
        
        return {
            "success": True,
            "action": "transfer_call",
            "call_id": call_id,
            "transfer_to": phone_number,
            "message": f"Call transfer initiated to {phone_number}"
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action_type}")


@app.websocket("/ws/calls/{call_id}")
async def websocket_transcript(websocket: WebSocket, call_id: str):
    await websocket.accept()
    
    db = SessionLocal()
    try:
        transcripts = db.query(TranscriptModel).filter(
            TranscriptModel.call_id == call_id
        ).order_by(TranscriptModel.timestamp).all()
        
        await websocket.send_json({
            "type": "history",
            "call_id": call_id,
            "entries": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                    "is_final": t.is_final
                }
                for t in transcripts
            ]
        })
        
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "transcript":
                    transcript = TranscriptModel(
                        call_id=call_id,
                        role=data.get("role", "user"),
                        content=data.get("content", ""),
                        is_final=data.get("is_final", True),
                    )
                    db.add(transcript)
                    db.commit()
                    
                    await websocket.send_json({
                        "type": "transcript",
                        "call_id": call_id,
                        "entry": {
                            "role": transcript.role,
                            "content": transcript.content,
                            "timestamp": transcript.timestamp.isoformat() if transcript.timestamp else None,
                            "is_final": transcript.is_final
                        }
                    })
                    
            except WebSocketDisconnect:
                break
                
    finally:
        db.close()


# Function Endpoints
@app.post("/api/agents/{agent_id}/functions", response_model=FunctionResponse, status_code=201)
async def create_function(agent_id: int, function: FunctionCreate, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if function.method.upper() not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Invalid method. Must be one of: {', '.join(valid_methods)}")
    
    speak_during_execution, speak_after_execution = _validate_tool_speech_flags_or_400(
        function.speak_during_execution,
        function.speak_after_execution,
    )

    db_function = FunctionModel(
        agent_id=agent_id,
        name=function.name,
        description=function.description,
        method=function.method.upper(),
        url=function.url,
        timeout_ms=function.timeout_ms,
        headers=function.headers,
        query_params=function.query_params,
        parameters_schema=function.parameters_schema,
        variables=function.variables,
        speak_during_execution=speak_during_execution,
        speak_after_execution=speak_after_execution,
    )
    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    return db_function


@app.get("/api/agents/{agent_id}/functions", response_model=List[FunctionResponse])
async def list_functions(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return db.query(FunctionModel).filter(FunctionModel.agent_id == agent_id).order_by(FunctionModel.created_at.desc()).all()


@app.get("/api/agents/{agent_id}/builtin-functions")
async def get_builtin_functions(agent_id: int, db: Session = Depends(get_database)):
    """Get built-in system functions for an agent"""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Define built-in system functions
    builtin_functions = [
        {
            "id": "builtin_end_call",
            "agent_id": agent_id,
            "name": "end_call",
            "description": "End the current call immediately. Use this when the user wants to hang up or when the conversation is complete.",
            "method": "SYSTEM",
            "url": "builtin://end_call",
            "timeout_ms": 5000,
            "headers": {},
            "query_params": {},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for ending the call (e.g., 'user_request', 'completed', 'error')"
                    }
                },
                "required": []
            },
            "variables": {},
            "speak_during_execution": False,
            "speak_after_execution": True,
            "is_builtin": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "builtin_transfer_call",
            "agent_id": agent_id,
            "name": "transfer_call",
            "description": "Transfer the current call to another phone number. Use this when the user needs to speak to a different department or person.",
            "method": "SYSTEM",
            "url": "builtin://transfer_call",
            "timeout_ms": 10000,
            "headers": {},
            "query_params": {},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "The phone number to transfer the call to (E.164 format, e.g., +1234567890)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to speak before transferring (e.g., 'Please hold while I transfer you')"
                    }
                },
                "required": ["phone_number"]
            },
            "variables": {},
            "speak_during_execution": True,
            "speak_after_execution": False,
            "is_builtin": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    return builtin_functions


@app.post("/api/agents/{agent_id}/builtin-functions")
async def save_builtin_functions(agent_id: int, config: dict, db: Session = Depends(get_database)):
    print(f"SAVE: agent_id={agent_id}, config={config}")
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    incoming = config if isinstance(config, dict) else {}
    normalized_config: Dict[str, Dict[str, Any]] = {}
    for builtin_id, raw_value in incoming.items():
        if not isinstance(raw_value, dict):
            continue
        enabled = bool(raw_value.get("enabled"))
        raw_cfg = raw_value.get("config")
        cfg = dict(raw_cfg) if isinstance(raw_cfg, dict) else {}

        if builtin_id == "builtin_transfer_call":
            default_during, default_after = True, False
            if enabled:
                phone_number = str(cfg.get("phone_number", "")).strip()
                if not phone_number:
                    raise HTTPException(status_code=400, detail="Transfer call requires config.phone_number")
                cfg["phone_number"] = phone_number
        elif builtin_id == "builtin_end_call":
            default_during, default_after = False, True
        else:
            default_during, default_after = False, True

        speak_during, speak_after = _validate_tool_speech_flags_or_400(
            raw_value.get("speak_during_execution", default_during),
            raw_value.get("speak_after_execution", default_after),
        )

        normalized_config[builtin_id] = {
            "enabled": enabled,
            "config": cfg,
            "speak_during_execution": speak_during,
            "speak_after_execution": speak_after,
        }
    
    # Get existing custom_params or initialize as a NEW dict
    current_params = agent.custom_params or {}
    new_params = dict(current_params)  # Create a new dict to force SQLAlchemy to detect the change
    new_params['builtin_functions'] = normalized_config
    agent.custom_params = new_params
    flag_modified(agent, "custom_params")
    agent.updated_at = datetime.utcnow()
    
    # Mark as dirty to ensure SQLAlchemy detects the change
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Verify save
    verify = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    print(f"SAVE: verified custom_params={verify.custom_params}")
    
    saved_config = ensure_custom_params(verify.custom_params).get("builtin_functions", {})
    return {"success": True, "message": "Builtin functions saved", "config": saved_config}


@app.get("/api/agents/{agent_id}/builtin-functions/config")
async def get_builtin_functions_config(agent_id: int, response: Response, db: Session = Depends(get_database)):
    print(f"GET: agent_id={agent_id}")
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    print(f"GET: custom_params={agent.custom_params}")
    custom_params = agent.custom_params or {}
    return custom_params.get('builtin_functions', {})


@app.get("/api/agents/{agent_id}/functions/{function_id}", response_model=FunctionResponse)
async def get_function(agent_id: int, function_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    return function


@app.patch("/api/agents/{agent_id}/functions/{function_id}", response_model=FunctionResponse)
async def update_function(agent_id: int, function_id: int, function_update: FunctionCreate, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if function_update.method and function_update.method.upper() not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Invalid method. Must be one of: {', '.join(valid_methods)}")

    speak_during_execution, speak_after_execution = _validate_tool_speech_flags_or_400(
        function_update.speak_during_execution,
        function_update.speak_after_execution,
    )
    
    for field, value in function_update.dict(exclude_unset=True).items():
        if value is not None:
            if field == "method":
                value = value.upper()
            setattr(function, field, value)

    function.speak_during_execution = speak_during_execution
    function.speak_after_execution = speak_after_execution
    
    function.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(function)
    return function


@app.delete("/api/agents/{agent_id}/functions/{function_id}")
async def delete_function(agent_id: int, function_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    db.delete(function)
    db.commit()
    return {"message": "Function deleted successfully"}


@app.get("/api/phone-numbers/sip-endpoint")
async def get_sip_endpoint():
    """Get the LiveKit SIP endpoint for phone number configuration"""
    sip_endpoint = get_livekit_sip_endpoint()
    return {
        "sip_endpoint": sip_endpoint,
        "sip_uri": f"sip:{sip_endpoint}",
        "livekit_url": LIVEKIT_URL,
        "instructions": "Use this endpoint when configuring Twilio SIP Trunk origination URI. Format: sip:13.135.81.172:5060"
    }


# ==================== Phone Number Endpoints (Twilio SIP) ====================

def get_livekit_sip_endpoint() -> str:
    """Get LiveKit SIP endpoint from environment or construct from URL"""
    # Try to get from environment first
    sip_from_env = os.getenv("LIVEKIT_SIP_ENDPOINT")
    if sip_from_env:
        return sip_from_env
    # Otherwise construct from LIVEKIT_URL by changing port 7880 to 5060
    url_host = LIVEKIT_URL.replace("ws://", "").replace("wss://", "").split(":")[0]
    return f"{url_host}:5060"


@app.post("/api/phone-numbers/", response_model=PhoneNumberResponse, status_code=201)
async def create_phone_number(phone_data: PhoneNumberCreate, db: Session = Depends(get_database)):
    """Create a new phone number with Twilio SIP configuration"""
    # Validate phone number format (E.164)
    if not phone_data.phone_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Phone number must be in E.164 format (e.g., +1234567890)")
    
    # Check if phone number already exists
    existing = db.query(PhoneNumberModel).filter(PhoneNumberModel.phone_number == phone_data.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Validate agent IDs if provided
    if phone_data.inbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone_data.inbound_agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Inbound agent not found")
    
    if phone_data.outbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone_data.outbound_agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Outbound agent not found")
    
    # Create phone number record
    phone_number = PhoneNumberModel(
        phone_number=phone_data.phone_number,
        description=phone_data.description,
        
        # Twilio SIP Trunk config
        termination_uri=phone_data.termination_uri,
        sip_trunk_username=phone_data.sip_trunk_username,
        sip_trunk_password=phone_data.sip_trunk_password,
        
        # Legacy Twilio credentials
        twilio_account_sid=phone_data.twilio_account_sid,
        twilio_auth_token=phone_data.twilio_auth_token,
        twilio_sip_trunk_sid=phone_data.twilio_sip_trunk_sid,
        
        inbound_agent_id=phone_data.inbound_agent_id,
        outbound_agent_id=phone_data.outbound_agent_id,
        enable_inbound=phone_data.enable_inbound,
        enable_outbound=phone_data.enable_outbound,
        enable_krisp_noise_cancellation=phone_data.enable_krisp_noise_cancellation,
        livekit_sip_endpoint=get_livekit_sip_endpoint(),
        status="pending"
    )
    
    db.add(phone_number)
    db.commit()
    db.refresh(phone_number)
    
    return phone_number


@app.get("/api/phone-numbers/", response_model=List[PhoneNumberResponse])
async def list_phone_numbers(db: Session = Depends(get_database)):
    """List all configured phone numbers"""
    phone_numbers = db.query(PhoneNumberModel).order_by(PhoneNumberModel.created_at.desc()).all()
    
    # Add agent names to response
    result = []
    for pn in phone_numbers:
        pn_dict = {
            "inbound_agent_name": None,
            "outbound_agent_name": None
        }
        if pn.inbound_agent_id:
            agent = db.query(AgentModel).filter(AgentModel.id == pn.inbound_agent_id).first()
            if agent:
                pn_dict["inbound_agent_name"] = agent.name
        if pn.outbound_agent_id:
            agent = db.query(AgentModel).filter(AgentModel.id == pn.outbound_agent_id).first()
            if agent:
                pn_dict["outbound_agent_name"] = agent.name
        
        # Create response with agent names
        response = PhoneNumberResponse.from_orm(pn)
        response.inbound_agent_name = pn_dict["inbound_agent_name"]
        response.outbound_agent_name = pn_dict["outbound_agent_name"]
        result.append(response)
    
    return result


@app.get("/api/phone-numbers/{phone_id}", response_model=PhoneNumberResponse)
async def get_phone_number(phone_id: int, db: Session = Depends(get_database)):
    """Get a specific phone number"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    response = PhoneNumberResponse.from_orm(phone)
    if phone.inbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone.inbound_agent_id).first()
        if agent:
            response.inbound_agent_name = agent.name
    if phone.outbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone.outbound_agent_id).first()
        if agent:
            response.outbound_agent_name = agent.name
    
    return response


@app.patch("/api/phone-numbers/{phone_id}", response_model=PhoneNumberResponse)
async def update_phone_number(phone_id: int, phone_update: PhoneNumberUpdate, db: Session = Depends(get_database)):
    """Update a phone number configuration"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Validate agent IDs if provided
    if phone_update.inbound_agent_id is not None:
        if phone_update.inbound_agent_id > 0:
            agent = db.query(AgentModel).filter(AgentModel.id == phone_update.inbound_agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail="Inbound agent not found")
    
    if phone_update.outbound_agent_id is not None:
        if phone_update.outbound_agent_id > 0:
            agent = db.query(AgentModel).filter(AgentModel.id == phone_update.outbound_agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail="Outbound agent not found")
    
    # Update fields
    update_data = phone_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(phone, field, value)
    
    phone.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(phone)
    
    response = PhoneNumberResponse.from_orm(phone)
    if phone.inbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone.inbound_agent_id).first()
        if agent:
            response.inbound_agent_name = agent.name
    if phone.outbound_agent_id:
        agent = db.query(AgentModel).filter(AgentModel.id == phone.outbound_agent_id).first()
        if agent:
            response.outbound_agent_name = agent.name
    
    return response


@app.delete("/api/phone-numbers/{phone_id}")
async def delete_phone_number(phone_id: int, db: Session = Depends(get_database)):
    """Delete a phone number configuration"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    db.delete(phone)
    db.commit()
    return {"message": "Phone number deleted successfully"}


@app.post("/api/phone-numbers/{phone_id}/configure")
async def configure_phone_number(phone_id: int, db: Session = Depends(get_database)):
    """Configure LiveKit SIP trunks for a phone number"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Needs EITHER Twilio credentials OR Pure SIP Trunking settings
    has_twilio = bool(phone.twilio_account_sid and phone.twilio_auth_token)
    has_pure_sip = bool(phone.termination_uri)
    
    if not has_twilio and not has_pure_sip:
        raise HTTPException(status_code=400, detail="Neither Twilio credentials nor SIP Trunk Details (Termination URI) are configured")
    
    # Get LiveKit API credentials
    lk_api_key = os.getenv("LIVEKIT_API_KEY")
    lk_api_secret = os.getenv("LIVEKIT_API_SECRET")
    lk_url = os.getenv("LIVEKIT_URL", "http://localhost:7880").replace("ws://", "http://").replace("wss://", "https://")
    
    if not lk_api_key or not lk_api_secret:
        phone.status = "error"
        phone.error_message = "LiveKit credentials not configured"
        db.commit()
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured on server")
    
    try:
        if has_pure_sip:
            # CREATE PURE SIP OUTBOUND TRUNK
            from livekit import api as livekit_api
            from livekit.protocol import sip as sip_proto
            
            lk_http_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
            if "livekit-server" in lk_http_url:
                lk_http_url = lk_http_url.replace("livekit-server", "localhost")
            
            lk_api = livekit_api.LiveKitAPI(url=lk_http_url, api_key=lk_api_key, api_secret=lk_api_secret)
            try:
                username = phone.sip_trunk_username or ""
                password = phone.sip_trunk_password or ""
                trunk_name = phone.phone_number
                
                req = livekit_api.CreateSIPOutboundTrunkRequest(
                    trunk=sip_proto.SIPOutboundTrunkInfo(
                        name=trunk_name,
                        address=phone.termination_uri,
                        numbers=[phone.phone_number],
                        auth_username=username,
                        auth_password=password
                    )
                )
                
                logger.info(f"Creating SIP Outbound Trunk for {phone.phone_number} at {phone.termination_uri}")
                res = await lk_api.sip.create_sip_outbound_trunk(req)
                
                # Update phone record with the new trunk ID
                phone.livekit_outbound_trunk_id = res.sip_trunk_id
                logger.info(f"Created SIP Outbound Trunk: {res.sip_trunk_id}")
                
                phone.status = "configured"
                phone.error_message = None
                db.commit()
                
                return {
                    "message": f"Successfully created Pure SIP Outbound Trunk ({res.sip_trunk_id}).",
                    "phone_number": phone.phone_number,
                    "livekit_outbound_trunk_id": res.sip_trunk_id
                }
            except Exception as e:
                logger.error(f"Error creating SIP Outbound Trunk: {e}")
                raise
            finally:
                await lk_api.aclose()
        
        else:
            # STANDARD TWILIO HTTP SETUP (Fallback)
            phone.status = "configured"
            phone.error_message = None
            db.commit()
            
            return {
                "message": "Phone number configured. Please create SIP trunks in LiveKit Cloud dashboard.",
                "phone_number": phone.phone_number,
                "livekit_sip_endpoint": phone.livekit_sip_endpoint,
                "instructions": {
                    "step1": "Go to LiveKit Cloud Dashboard â†’ Telephony â†’ SIP Trunks",
                    "step2": f"Create Inbound Trunk with number: {phone.phone_number}",
                    "step3": f"Set Origination URI to: sip:{phone.livekit_sip_endpoint}",
                    "step4": "Create Dispatch Rule to route calls to your agent",
                    "step5": "Update this record with the trunk IDs from LiveKit"
                }
            }
            
    except Exception as e:
        phone.status = "error"
        phone.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")


@app.post("/api/phone-numbers/{phone_id}/create-dispatch-rule")
async def create_dispatch_rule(phone_id: int, agent_name: str = "sarah", db: Session = Depends(get_database)):
    """Create a LiveKit SIP dispatch rule with agent configuration"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    if not phone.livekit_inbound_trunk_id:
        raise HTTPException(status_code=400, detail="Phone number not configured with LiveKit trunk")
    dispatch_agent_name = resolve_dispatch_agent_name(None, agent_name)

    try:
        import httpx
        from livekit import api as livekit_api
        
        # Use LiveKit SDK to get proper URL
        lk_api = livekit_api.LiveKitAPI(
            url="http://127.0.0.1:7880",
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678")
        )
        
        # Delete existing dispatch rules for this trunk
        dispatch_rules = await lk_api.sip.list_sip_dispatch_rule(livekit_api.ListSIPDispatchRuleRequest())
        for rule in dispatch_rules.items:
            if phone.livekit_inbound_trunk_id in rule.trunk_ids:
                logger.info(f"Deleting existing dispatch rule: {rule.sip_dispatch_rule_id}")
                await lk_api.sip.delete_sip_dispatch_rule(
                    livekit_api.DeleteSIPDispatchRuleRequest(
                        sip_dispatch_rule_id=rule.sip_dispatch_rule_id
                    )
                )
        
        dispatch_req = livekit_api.CreateSIPDispatchRuleRequest(
            name=f"{dispatch_agent_name}-inbound",
            trunk_ids=[phone.livekit_inbound_trunk_id],
            room_config=livekit_api.RoomConfiguration(
                agents=[livekit_api.RoomAgentDispatch(agent_name=dispatch_agent_name)]
            ),
            rule=livekit_api.SIPDispatchRule(
                dispatch_rule_individual=livekit_api.SIPDispatchRuleIndividual(
                    room_prefix="call"
                )
            )
        )

        result = await lk_api.sip.create_sip_dispatch_rule(dispatch_req)
        dispatch_rule_id = str(getattr(result, "sip_dispatch_rule_id", "") or "").strip()
        if not dispatch_rule_id:
            raise RuntimeError(f"Unable to read created dispatch rule id from LiveKit response: {result}")
        
        await lk_api.aclose()
        
        # Update database
        phone.livekit_dispatch_rule_id = dispatch_rule_id
        db.commit()
        
        logger.info(f"Created dispatch rule {dispatch_rule_id} with agent {dispatch_agent_name}")
        
        return {
            "message": f"Dispatch rule created with agent {dispatch_agent_name}",
            "dispatch_rule_id": dispatch_rule_id,
            "agent_name": dispatch_agent_name
        }
        
    except Exception as e:
        logger.error(f"Failed to create dispatch rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dispatch rule: {str(e)}")


@app.post("/api/phone-numbers/{phone_id}/outbound")
async def make_outbound_call(phone_id: int, call_request: OutboundCallRequest, db: Session = Depends(get_database)):
    """Make an outbound call using Twilio SIP Trunk"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    if not phone.outbound_agent_id:
        raise HTTPException(status_code=400, detail="No outbound agent configured")
    
    # Validate target number
    to_number = call_request.to_number
    if not to_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Target number must be in E.164 format")
    
    # Get the agent
    agent = db.query(AgentModel).filter(AgentModel.id == phone.outbound_agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Outbound agent not found")
    
    # Create a call record
    call_id = f"outbound_{uuid.uuid4().hex[:12]}"
    room_name = f"call_{agent.id}_{uuid.uuid4().hex[:6]}"
    runtime_vars = normalize_runtime_vars(call_request.runtime_vars)
    call_metadata: Dict[str, Any] = {
        "call_id": call_id,
        "from_number": phone.phone_number,
        "to_number": to_number,
        "runtime_vars": runtime_vars,
    }
    
    call = CallModel(
        call_id=call_id,
        agent_id=agent.id,
        room_name=room_name,
        call_type="phone",
        direction="outbound",
        status="initiating",
        started_at=datetime.utcnow(),
        from_number=phone.phone_number,
        to_number=to_number,
        call_metadata=call_metadata,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    
    try:
        http_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
        if "livekit-server" in http_url:
            http_url = http_url.replace("livekit-server", "localhost")
        
        # Check if we have SIP trunk config (either dynamic from configure or manual)
        has_sip_trunk = bool(phone.livekit_outbound_trunk_id) or bool(phone.termination_uri)
        
        if has_sip_trunk:
            # Use Pure SIP Trunk for outbound
            logger.info(f"Using SIP Trunk for outbound call (trunk_id={phone.livekit_outbound_trunk_id})")
            
            # First create room and dispatch agent
            from livekit import api as livekit_api
            lk_api = livekit_api.LiveKitAPI(url=http_url, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            
            try:
                # Create room
                room = await lk_api.room.create_room(
                    livekit_api.CreateRoomRequest(
                        name=room_name,
                        empty_timeout=300,
                        # Allow transfer scenarios (agent + active callee + transfer target)
                        max_participants=4
                    )
                )
                logger.info(f"Created room: {room_name}")
                
                dispatch_agent_name = resolve_dispatch_agent_name(agent)
                dispatch_metadata: Dict[str, Any] = {
                    "call_id": call_id,
                    "from_number": phone.phone_number,
                    "to_number": to_number,
                }
                if runtime_vars:
                    dispatch_metadata["runtime_vars"] = runtime_vars
                dispatch = await lk_api.agent_dispatch.create_dispatch(
                    livekit_api.CreateAgentDispatchRequest(
                        agent_name=dispatch_agent_name,
                        room=room_name,
                        metadata=json.dumps(dispatch_metadata)
                    )
                )
                logger.info(
                    "Dispatched agent worker %s to room %s (configured agent_name=%s)",
                    dispatch_agent_name,
                    room_name,
                    agent.agent_name,
                )
            finally:
                await lk_api.aclose()
            
            # Use LiveKit SIP trunk for outbound call
            outbound_trunk_id = phone.livekit_outbound_trunk_id
            if not outbound_trunk_id:
                raise HTTPException(status_code=400, detail="No outbound trunk ID configured. Please run /configure first.")
            
            from livekit import api as livekit_api
            lk_api2 = livekit_api.LiveKitAPI(url=http_url, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            
            try:
                await lk_api2.sip.create_sip_participant(
                    livekit_api.CreateSIPParticipantRequest(
                        sip_trunk_id=outbound_trunk_id,
                        sip_call_to=to_number,
                        sip_number=phone.phone_number,
                        room_name=room_name,
                        participant_identity=f"call_{to_number}",
                        play_ringtone=True,
                    )
                )
                logger.info(f"Initiated SIP call to {to_number} via LiveKit trunk")
            finally:
                await lk_api2.aclose()
            
            call.status = "dialing"
            db.commit()
            
            return {
                "call_id": call.call_id,
                "room_name": room_name,
                "from_number": phone.phone_number,
                "to_number": to_number,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "status": "dialing",
                "message": "Outbound call initiated!",
                "runtime_vars": runtime_vars,
            }
        else:
            raise HTTPException(status_code=400, detail="Twilio SIP trunk not configured for this phone number")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making outbound call: {e}")
        call.status = "error"
        call.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to initiate outbound call: {str(e)}")


@app.get("/api/phone-numbers/{phone_id}/instructions")
async def get_phone_number_instructions(phone_id: int, db: Session = Depends(get_database)):
    """Get step-by-step Twilio configuration instructions"""
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    return {
        "phone_number": phone.phone_number,
        "livekit_sip_endpoint": phone.livekit_sip_endpoint,
        "twilio_instructions": {
            "step1": {
                "title": "Buy a Phone Number in Twilio",
                "description": "Go to Twilio Console â†’ Phone Numbers â†’ Buy a Number. Purchase a number that supports Voice.",
                "link": "https://console.twilio.com/us1/develop/sms/buy-phone-numbers"
            },
            "step2": {
                "title": "Create SIP Trunk in Twilio",
                "description": "Go to Elastic SIP Trunking â†’ Create SIP Trunk. Name it 'LiveKit Inbound'.",
                "link": "https://console.twilio.com/us1/develop/sip-trunking/trunks"
            },
            "step3": {
                "title": "Configure Origination (Inbound)",
                "description": f"In Twilio SIP Trunk, set Origination URI to: sip:{phone.livekit_sip_endpoint}",
                "value_to_paste": f"sip:{phone.livekit_sip_endpoint}"
            },
            "step4": {
                "title": "Configure Termination (Outbound - Optional)",
                "description": "If you want to make outbound calls, configure Termination with your LiveKit credentials."
            },
            "step5": {
                "title": "Assign Phone Number to Trunk",
                "description": "In Twilio, go to your phone number and configure it to use the SIP trunk."
            },
            "step6": {
                "title": "Create Inbound Trunk in LiveKit",
                "description": "In LiveKit Cloud Dashboard â†’ Telephony â†’ SIP Trunks, create an inbound trunk with your phone number.",
                "link": "https://cloud.livekit.io/projects/p_/telephony/trunks"
            },
            "step7": {
                "title": "Create Dispatch Rule in LiveKit",
                "description": f"Create a dispatch rule to route calls to agent ID {phone.inbound_agent_id or 'your agent'}",
                "link": "https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/"
            }
        },
        "agent_configuration": {
            "inbound_agent_id": phone.inbound_agent_id,
            "outbound_agent_id": phone.outbound_agent_id
        }
    }


# TwiML endpoint for outbound calls - connects Twilio call to LiveKit room
@app.api_route("/api/twiml/{room_name}", methods=["GET", "POST"])
async def get_twiml_for_room(room_name: str):
    """Returns TwiML to connect a Twilio call to a LiveKit room via SIP"""
    # Get the SIP endpoint for LiveKit
    sip_endpoint = os.getenv("LIVEKIT_SIP_ENDPOINT", "13.135.81.172:5060")
    
    # Return TwiML that connects to LiveKit via SIP
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:{room_name}@{sip_endpoint}</Sip>
    </Dial>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


# Also expose without /api prefix for when nginx strips /api
@app.api_route("/twiml/{room_name}", methods=["GET", "POST"])
async def get_twiml_for_room_no_api(room_name: str):
    """Returns TwiML to connect a Twilio call to a LiveKit room via SIP (no /api prefix)"""
    # Get the SIP endpoint for LiveKit
    sip_endpoint = os.getenv("LIVEKIT_SIP_ENDPOINT", "13.135.81.172:5060")
    
    # Return TwiML that connects to LiveKit via SIP
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:{room_name}@{sip_endpoint}</Sip>
    </Dial>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


# Twilio status callback endpoint
@app.post("/api/twilio-status/{call_id}")
async def twilio_status_callback(call_id: str, db: Session = Depends(get_database)):
    """Handle Twilio status callbacks"""
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if call:
        pass
    return {"status": "ok"}


# ==================== LiveKit Webhook (Inbound Call Detection) ====================

@app.post("/api/livekit-webhook")
async def livekit_webhook(request_body: dict = None, db: Session = Depends(get_database)):
    """
    Handle LiveKit webhooks for automatic inbound call detection.
    When a SIP call arrives, LiveKit creates a room and sends events here.
    We use this to auto-create call records for inbound calls.
    """
    if not request_body:
        return {"status": "ok"}
    
    event = request_body.get("event", "")
    room = request_body.get("room", {})
    participant = request_body.get("participant", {})
    
    room_name = room.get("name", "")
    
    logger.info(f"LiveKit webhook: event={event}, room={room_name}")
    
    if event == "participant_joined":
        # Check if this is a SIP participant (inbound phone call)
        identity = participant.get("identity", "")
        participant_name = participant.get("name", "")
        attributes = participant.get("attributes", {})
        kind = participant.get("kind", "")
        
        is_sip = identity.startswith("sip_") or kind == "SIP" or \
                 attributes.get("sip.callID") or \
                 "sip" in identity.lower()
        
        if is_sip:
            # This is an inbound phone call
            caller_number = normalize_phone_lookup(
                attributes.get("sip.callerNumber", "")
                or attributes.get("sip.from", "")
                or participant_name
            )
            called_number = normalize_phone_lookup(
                attributes.get("sip.calledNumber", "")
                or attributes.get("sip.to", "")
            )
            sip_call_id = attributes.get("sip.callID", "")
            sip_trunk_id = (
                attributes.get("sip.trunkID", "")
                or attributes.get("sip.trunkId", "")
                or attributes.get("sip.trunk_id", "")
            )
            
            # Check if an ACTIVE call already exists for this room.
            existing_call = (
                db.query(CallModel)
                .filter(
                    CallModel.room_name == room_name,
                    CallModel.status.in_(ACTIVE_CALL_STATUSES),
                )
                .order_by(CallModel.created_at.desc())
                .first()
            )
            if existing_call:
                if _is_stale_active_call(existing_call):
                    existing_call.status = "failed"
                    existing_call.error_message = "Auto-closed stale active call before creating new inbound session."
                    existing_call.ended_at = datetime.utcnow()
                    if existing_call.started_at:
                        existing_call.duration_seconds = int((existing_call.ended_at - existing_call.started_at).total_seconds())
                    db.commit()
                    logger.warning("Closed stale active call %s for room %s", existing_call.call_id, room_name)
                else:
                    logger.info(f"Call already exists for room {room_name}")
                    return {"status": "ok"}
            
            routing = resolve_inbound_agent_id(
                db,
                called_number=called_number,
                sip_trunk_id=sip_trunk_id,
                room_name=room_name,
            )
            agent_id = routing["agent_id"]
            
            # Create inbound call record
            call_id = f"inbound_{uuid.uuid4().hex[:12]}"
            db_call = CallModel(
                call_id=call_id,
                agent_id=agent_id,
                room_name=room_name,
                call_type="phone",
                direction="inbound",
                status="in-progress",
                from_number=caller_number,
                to_number=called_number,
                twilio_call_sid=sip_call_id,
                started_at=datetime.utcnow(),
                call_metadata={
                    "sip_attributes": attributes,
                    "participant_identity": identity,
                    "sip_trunk_id": sip_trunk_id,
                    "inbound_routing_source": routing.get("source"),
                    "resolved_called_number": routing.get("normalized_called_number"),
                }
            )
            db.add(db_call)
            db.commit()
            logger.info(f"Created inbound call record: {call_id} for room {room_name}")
    
    elif event == "participant_left":
        # Do not close call immediately on SIP participant_left because telephony jitter can cause
        # rapid leave/join cycles. Call is finalized by /api/calls/{call_id}/end or room_finished.
        identity = participant.get("identity", "")
        is_sip = identity.startswith("sip_") or "sip" in identity.lower()
        
        if is_sip:
            logger.info("SIP participant_left received for room %s; waiting for explicit end event", room_name)
    
    elif event == "room_finished":
        # Mark any ongoing calls in this room as completed
        calls = db.query(CallModel).filter(
            CallModel.room_name == room_name,
            CallModel.status.in_(ACTIVE_CALL_STATUSES)
        ).all()
        for call in calls:
            call.ended_at = datetime.utcnow()
            if call.started_at:
                call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())
            elif call.created_at:
                call.duration_seconds = int((call.ended_at - call.created_at).total_seconds())

            final_status, inferred_error = _infer_terminal_status_for_call(call, db)
            call.status = final_status
            if inferred_error and not (call.error_message or "").strip():
                call.error_message = inferred_error
        db.commit()

        # Auto-backfill usage/cost from transcript if runtime usage wasn't posted.
        for call in calls:
            if _looks_like_missing_usage(call):
                if _backfill_usage_from_transcript_and_cost(call, db):
                    logger.info("Backfilled usage on room_finished for call_id=%s", call.call_id)
        db.commit()
    
    return {"status": "ok"}


# ==================== Agent by Phone Number (for inbound routing) ====================

def _serialize_voice_runtime_agent(agent: AgentModel) -> Dict[str, Any]:
    tts = extract_agent_tts_settings(agent)
    return {
        "agent_id": agent.id,
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "llm_temperature": resolve_agent_llm_temperature(agent),
        "voice": agent.voice,
        "voice_speed": resolve_agent_voice_speed(agent),
        "tts_provider": tts["tts_provider"],
        "tts_model": tts["tts_model"],
        "language": agent.language,
        "welcome_message_type": agent.welcome_message_type,
        "welcome_message": agent.welcome_message,
        "custom_params": ensure_custom_params(agent.custom_params),
    }


@app.get("/api/agents/by-dispatch-name/{dispatch_name:path}")
async def get_agent_by_dispatch_name(dispatch_name: str, db: Session = Depends(get_database)):
    """Resolve agent config by worker dispatch name (used when SIP metadata lacks phone numbers)."""
    dispatch = (dispatch_name or "").strip()
    if not dispatch:
        raise HTTPException(status_code=400, detail="dispatch_name is required")

    agent = (
        db.query(AgentModel)
        .filter(AgentModel.agent_name.ilike(dispatch))
        .order_by(AgentModel.updated_at.desc())
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="No agent configured with this dispatch name")
    return _serialize_voice_runtime_agent(agent)


@app.get("/api/agents/by-phone/{phone_number:path}")
async def get_agent_by_phone(phone_number: str, db: Session = Depends(get_database)):
    """Get agent configuration for a phone number (used by voice agent for inbound calls)"""
    phone_record, normalized_phone = find_phone_record_by_number(db, phone_number)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="phone_number is required")

    if not phone_record or not phone_record.enable_inbound or not phone_record.inbound_agent_id:
        raise HTTPException(status_code=404, detail="No agent configured for this phone number")
    
    agent = db.query(AgentModel).filter(AgentModel.id == phone_record.inbound_agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Assigned agent not found")

    return _serialize_voice_runtime_agent(agent)


# ==================== Call Usage / Metrics Update ====================

def _estimate_usage_from_transcripts(db: Session, call_id: str) -> Dict[str, int]:
    rows = (
        db.query(TranscriptModel.role, TranscriptModel.content)
        .filter(TranscriptModel.call_id == call_id)
        .all()
    )
    llm_tokens_in = 0
    llm_tokens_out = 0
    stt_duration_ms = 0
    tts_characters = 0
    for role, content in rows:
        text = str(content or "").strip()
        if not text:
            continue
        token_estimate = max(1, len(text) // 4)
        if role == "user":
            llm_tokens_in += token_estimate
            # ~150 wpm ~= 2.5 words/sec
            word_count = max(1, len(text.split()))
            stt_duration_ms += max(700, int((word_count / 2.5) * 1000))
        elif role == "agent":
            llm_tokens_out += token_estimate
            tts_characters += len(text)
        elif role in {"tool_call", "tool_response", "tool_invocation", "tool_result"}:
            # Tool messages still consume some model tokens.
            llm_tokens_out += max(1, token_estimate // 2)
    return {
        "llm_tokens_in": llm_tokens_in,
        "llm_tokens_out": llm_tokens_out,
        "stt_duration_ms": stt_duration_ms,
        "tts_characters": tts_characters,
    }


def _looks_like_missing_usage(call: CallModel) -> bool:
    return (
        (call.llm_tokens_in or 0) <= 0
        and (call.llm_tokens_out or 0) <= 0
        and (call.stt_duration_ms or 0) <= 0
        and (call.tts_characters or 0) <= 0
    )


def _compute_llm_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    m = (model or "").lower()
    ti = max(tokens_in or 0, 0)
    to = max(tokens_out or 0, 0)

    if "gpt-4o-mini" in m:
        cost = (ti * 0.15 + to * 0.60) / 1_000_000
    elif "gpt-4o" in m:
        cost = (ti * 2.50 + to * 10.0) / 1_000_000
    elif "gpt-5" in m:
        cost = (ti * 1.0 + to * 4.0) / 1_000_000
    elif "moonshot" in m or "kimi" in m or "moonlight" in m:
        cost = (ti * 1.0 + to * 2.0) / 1_000_000
    elif "claude" in m:
        cost = (ti * 3.0 + to * 15.0) / 1_000_000
    else:
        cost = (ti * 0.15 + to * 0.60) / 1_000_000

    if ti > 0 or to > 0:
        cost = max(cost, 0.001)
    return cost


def _backfill_usage_from_transcript_and_cost(call: CallModel, db: Session) -> bool:
    if not call:
        return False

    estimate = _estimate_usage_from_transcripts(db, call.call_id)
    if not any(estimate.values()):
        return False

    call.llm_tokens_in = max(call.llm_tokens_in or 0, estimate["llm_tokens_in"])
    call.llm_tokens_out = max(call.llm_tokens_out or 0, estimate["llm_tokens_out"])
    call.stt_duration_ms = max(call.stt_duration_ms or 0, estimate["stt_duration_ms"])
    call.tts_characters = max(call.tts_characters or 0, estimate["tts_characters"])
    if not call.transcript_summary:
        call.transcript_summary = "Usage estimated from transcript due missing runtime metrics."

    model = call.llm_model_used or ""
    if not model:
        agent = db.query(AgentModel).filter(AgentModel.id == call.agent_id).first()
        model = (agent.llm_model if agent else "") or ""
        if model:
            call.llm_model_used = model

    call.llm_cost = _compute_llm_cost_usd(model, call.llm_tokens_in or 0, call.llm_tokens_out or 0)

    stt_minutes = (call.stt_duration_ms or 0) / 60000.0
    if stt_minutes > 0:
        stt_model = ensure_custom_params(call.call_metadata).get("stt_model") or "nova-3"
        stt_rate = 0.006 if ("nova-3" in str(stt_model).lower() or "conversationalai" in str(stt_model).lower()) else 0.004
        call.stt_cost = max(stt_minutes * stt_rate, 0.001)

    metadata = ensure_custom_params(call.call_metadata)
    tts_provider = normalize_tts_provider(metadata.get("tts_provider"), None)
    tts_model_used = metadata.get("tts_model")
    tts_chars = call.tts_characters or 0
    if tts_chars > 0:
        if tts_provider == "elevenlabs":
            tts_rate = FALLBACK_ELEVENLABS_TTS_RATE_PER_1K_CHARS.get(
                tts_model_used or DEFAULT_ELEVENLABS_MODEL,
                FALLBACK_ELEVENLABS_TTS_RATE_PER_1K_CHARS[DEFAULT_ELEVENLABS_MODEL],
            )
        else:
            tts_rate = 0.015
        call.tts_cost = max((tts_chars / 1000.0) * tts_rate, 0.001)

    call.cost_usd = (call.llm_cost or 0) + (call.stt_cost or 0) + (call.tts_cost or 0)
    return True


class CallUsageUpdate(BaseModel):
    llm_tokens_in: Optional[int] = None
    llm_tokens_out: Optional[int] = None
    llm_model_used: Optional[str] = None
    stt_duration_ms: Optional[int] = None
    stt_model_used: Optional[str] = None  # Track STT model for accurate cost
    tts_characters: Optional[int] = None
    tts_provider: Optional[str] = None
    tts_model_used: Optional[str] = None
    transcript_summary: Optional[str] = None
    actual_duration_seconds: Optional[int] = None
    # Actual usage from API providers
    actual_llm_tokens_in: Optional[int] = None
    actual_llm_tokens_out: Optional[int] = None
    actual_stt_minutes: Optional[float] = None
    actual_tts_characters: Optional[int] = None
    actual_tts_cost_usd: Optional[float] = None
    tts_cost_source: Optional[str] = None
    llm_temperature: Optional[float] = None
    voice_speed: Optional[float] = None


@app.post("/api/calls/{call_id}/usage")
async def update_call_usage(call_id: str, usage: CallUsageUpdate, db: Session = Depends(get_database)):
    """Update call with usage metrics and calculate costs"""
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        # Try finding by room_name
        call = db.query(CallModel).filter(CallModel.room_name == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if usage.llm_tokens_in is not None and usage.llm_tokens_in >= 0:
        call.llm_tokens_in = max(call.llm_tokens_in or 0, usage.llm_tokens_in)
    if usage.llm_tokens_out is not None and usage.llm_tokens_out >= 0:
        call.llm_tokens_out = max(call.llm_tokens_out or 0, usage.llm_tokens_out)
    if usage.actual_llm_tokens_in is not None and usage.actual_llm_tokens_in >= 0:
        call.llm_tokens_in = max(call.llm_tokens_in or 0, usage.actual_llm_tokens_in)
    if usage.actual_llm_tokens_out is not None and usage.actual_llm_tokens_out >= 0:
        call.llm_tokens_out = max(call.llm_tokens_out or 0, usage.actual_llm_tokens_out)
    if usage.llm_model_used:
        call.llm_model_used = usage.llm_model_used
    if usage.stt_duration_ms is not None and usage.stt_duration_ms >= 0:
        call.stt_duration_ms = max(call.stt_duration_ms or 0, usage.stt_duration_ms)
    if usage.tts_characters is not None and usage.tts_characters >= 0:
        call.tts_characters = max(call.tts_characters or 0, usage.tts_characters)
    if usage.actual_tts_characters is not None and usage.actual_tts_characters > 0:
        call.tts_characters = max(call.tts_characters or 0, usage.actual_tts_characters)
    if usage.transcript_summary:
        call.transcript_summary = usage.transcript_summary

    metadata = ensure_custom_params(call.call_metadata)
    if usage.tts_provider:
        metadata["tts_provider"] = normalize_tts_provider(usage.tts_provider, None)
    if usage.tts_model_used:
        metadata["tts_model"] = usage.tts_model_used
    if usage.stt_model_used:
        metadata["stt_model"] = usage.stt_model_used
    if usage.tts_cost_source:
        metadata["tts_cost_source"] = usage.tts_cost_source
    if usage.llm_temperature is not None:
        metadata["llm_temperature"] = _coerce_agent_setting_float(
            usage.llm_temperature,
            default=DEFAULT_AGENT_LLM_TEMPERATURE,
            min_value=MIN_AGENT_LLM_TEMPERATURE,
            max_value=MAX_AGENT_LLM_TEMPERATURE,
        )
    if usage.voice_speed is not None:
        metadata["voice_speed"] = _coerce_agent_setting_float(
            usage.voice_speed,
            default=DEFAULT_AGENT_VOICE_SPEED,
            min_value=MIN_AGENT_VOICE_SPEED,
            max_value=MAX_AGENT_VOICE_SPEED,
        )
    call.call_metadata = metadata

    if _looks_like_missing_usage(call):
        estimate = _estimate_usage_from_transcripts(db, call.call_id)
        if any(estimate.values()):
            call.llm_tokens_in = max(call.llm_tokens_in or 0, estimate["llm_tokens_in"])
            call.llm_tokens_out = max(call.llm_tokens_out or 0, estimate["llm_tokens_out"])
            call.stt_duration_ms = max(call.stt_duration_ms or 0, estimate["stt_duration_ms"])
            call.tts_characters = max(call.tts_characters or 0, estimate["tts_characters"])
            if not call.transcript_summary:
                call.transcript_summary = "Usage estimated from transcript due missing runtime metrics."
            logger.warning("Usage fallback applied from transcript for call_id=%s", call.call_id)
    
    # Calculate costs based on ACTUAL usage from API providers when available
    model = call.llm_model_used or ""
    if not model:
        agent = db.query(AgentModel).filter(AgentModel.id == call.agent_id).first()
        model = (agent.llm_model if agent else "") or ""
        if model and not call.llm_model_used:
            call.llm_model_used = model
    
    # Use actual LLM tokens from API if available, otherwise use estimated
    # Note: actual_llm_tokens are now sent from agent with real-time per-call usage
    actual_tokens_in = usage.actual_llm_tokens_in if usage.actual_llm_tokens_in and usage.actual_llm_tokens_in > 0 else call.llm_tokens_in
    actual_tokens_out = usage.actual_llm_tokens_out if usage.actual_llm_tokens_out and usage.actual_llm_tokens_out > 0 else call.llm_tokens_out
    
    # Calculate LLM cost using actual/estimated tokens
    if "gpt-4o-mini" in model:
        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        call.llm_cost = ((actual_tokens_in or 0) * 0.15 + (actual_tokens_out or 0) * 0.60) / 1_000_000
    elif "gpt-4o" in model:
        # GPT-4o: $2.50/1M input, $10.0/1M output
        call.llm_cost = ((actual_tokens_in or 0) * 2.50 + (actual_tokens_out or 0) * 10.0) / 1_000_000
    elif "gpt-5" in model or "gpt-5-mini" in model:
        # GPT-5: $1.00/1M input, $4.0/1M output
        call.llm_cost = ((actual_tokens_in or 0) * 1.0 + (actual_tokens_out or 0) * 4.0) / 1_000_000
    elif "moonshot" in model:
        # Moonshot: $1.00/1M input, $2.0/1M output
        call.llm_cost = ((actual_tokens_in or 0) * 1.0 + (actual_tokens_out or 0) * 2.0) / 1_000_000
    elif "claude" in model.lower():
        # Claude: ~$3.0/1M input, $15.0/1M output
        call.llm_cost = ((actual_tokens_in or 0) * 3.0 + (actual_tokens_out or 0) * 15.0) / 1_000_000
    else:
        # Default: assume GPT-4o-mini rates
        call.llm_cost = ((actual_tokens_in or 0) * 0.15 + (actual_tokens_out or 0) * 0.60) / 1_000_000
    
    # Add minimum LLM cost if there were any tokens (base API call cost)
    if (actual_tokens_in or 0) > 0 or (actual_tokens_out or 0) > 0:
        call.llm_cost = max(call.llm_cost, 0.001)  # Minimum $0.001 per call

    # Use actual STT minutes from Deepgram API if available
    actual_stt_minutes = usage.actual_stt_minutes if usage.actual_stt_minutes else (call.stt_duration_ms / 60000.0) if call.stt_duration_ms else 0
    if actual_stt_minutes > 0:
        # Deepgram STT pricing varies by model family.
        # We keep a conservative estimate for cost display when provider-level exact billing
        # is unavailable in-session.
        stt_model = usage.stt_model_used or "nova-3"
        stt_model_l = stt_model.lower()
        if "nova-3" in stt_model_l or "conversationalai" in stt_model_l:
            stt_rate = 0.006
        else:
            stt_rate = 0.004  # nova-2 and other models
        call.stt_cost = actual_stt_minutes * stt_rate
        call.stt_cost = max(call.stt_cost, 0.001)

    tts_provider = metadata.get("tts_provider", DEFAULT_TTS_PROVIDER)
    tts_model_used = metadata.get("tts_model")
    actual_tts_chars = usage.actual_tts_characters if usage.actual_tts_characters is not None else (call.tts_characters or 0)

    # Use provider-reported TTS cost whenever agent supplies it.
    if usage.actual_tts_cost_usd is not None and usage.actual_tts_cost_usd >= 0:
        call.tts_cost = usage.actual_tts_cost_usd
    elif actual_tts_chars > 0:
        if tts_provider == "elevenlabs":
            fallback_rate = FALLBACK_ELEVENLABS_TTS_RATE_PER_1K_CHARS.get(
                tts_model_used or DEFAULT_ELEVENLABS_MODEL,
                FALLBACK_ELEVENLABS_TTS_RATE_PER_1K_CHARS[DEFAULT_ELEVENLABS_MODEL],
            )
        else:
            # Deepgram estimate fallback: ~$0.015 / 1K chars
            fallback_rate = 0.015

        call.tts_cost = (actual_tts_chars / 1000.0) * fallback_rate
        call.tts_cost = max(call.tts_cost, 0.001)
    
    call.cost_usd = (call.llm_cost or 0) + (call.stt_cost or 0) + (call.tts_cost or 0)
    
    # Use actual duration from agent if provided, otherwise keep calculated duration
    if usage.actual_duration_seconds is not None:
        call.duration_seconds = usage.actual_duration_seconds
    
    db.commit()
    return {"message": "Usage updated", "total_cost": call.cost_usd}


# ==================== Create Call from Agent (for inbound) ====================

class AgentCallCreate(BaseModel):
    room_name: str
    agent_id: int
    direction: str = "inbound"
    call_type: str = "phone"
    from_number: Optional[str] = None
    to_number: Optional[str] = None


@app.post("/api/calls/create-from-agent")
async def create_call_from_agent(call_data: AgentCallCreate, db: Session = Depends(get_database)):
    """Create a call record from the voice agent (used for inbound calls)"""
    normalized_direction = normalize_call_direction(call_data.direction, default="inbound")
    normalized_from_number = normalize_phone_lookup(call_data.from_number)
    normalized_to_number = normalize_phone_lookup(call_data.to_number)
    inbound_routing = None
    resolved_agent_id = call_data.agent_id

    if normalized_direction == "inbound":
        inbound_routing = resolve_inbound_agent_id(
            db,
            called_number=normalized_to_number,
            room_name=call_data.room_name,
            fallback_agent_id=call_data.agent_id,
        )
        resolved_agent_id = inbound_routing["agent_id"]

    # Reuse only active call rows for this room; create a fresh row for ended/failed calls.
    existing = (
        db.query(CallModel)
        .filter(
            CallModel.room_name == call_data.room_name,
            CallModel.status.in_(ACTIVE_CALL_STATUSES),
        )
        .order_by(CallModel.created_at.desc())
        .first()
    )
    if existing:
        if _is_stale_active_call(existing):
            existing.status = "failed"
            existing.error_message = "Auto-closed stale active call before new create-from-agent."
            existing.ended_at = datetime.utcnow()
            if existing.started_at:
                existing.duration_seconds = int((existing.ended_at - existing.started_at).total_seconds())
            db.commit()
        else:
            metadata = ensure_custom_params(existing.call_metadata)
            changed = False

            if normalized_from_number and existing.from_number != normalized_from_number:
                existing.from_number = normalized_from_number
                metadata["from_number"] = normalized_from_number
                changed = True
            if normalized_to_number and existing.to_number != normalized_to_number:
                existing.to_number = normalized_to_number
                metadata["to_number"] = normalized_to_number
                changed = True
            if resolved_agent_id and existing.agent_id != resolved_agent_id:
                existing.agent_id = resolved_agent_id
                changed = True
            if inbound_routing and inbound_routing.get("source"):
                metadata["inbound_routing_source"] = inbound_routing["source"]
                if inbound_routing.get("normalized_called_number"):
                    metadata["resolved_called_number"] = inbound_routing["normalized_called_number"]
                changed = True

            if changed:
                existing.call_metadata = metadata
                flag_modified(existing, "call_metadata")
                db.commit()

            return {
                "call_id": existing.call_id,
                "agent_id": existing.agent_id,
                "already_exists": True,
                "metadata": ensure_custom_params(existing.call_metadata),
            }
    
    call_id = f"{normalized_direction}_{uuid.uuid4().hex[:12]}"
    call_metadata = {}
    if normalized_from_number:
        call_metadata["from_number"] = normalized_from_number
    if normalized_to_number:
        call_metadata["to_number"] = normalized_to_number
    if inbound_routing and inbound_routing.get("source"):
        call_metadata["inbound_routing_source"] = inbound_routing["source"]
        if inbound_routing.get("normalized_called_number"):
            call_metadata["resolved_called_number"] = inbound_routing["normalized_called_number"]

    db_call = CallModel(
        call_id=call_id,
        agent_id=resolved_agent_id,
        room_name=call_data.room_name,
        call_type=call_data.call_type,
        direction=normalized_direction,
        status="in-progress",
        from_number=normalized_from_number,
        to_number=normalized_to_number,
        started_at=datetime.utcnow(),
        call_metadata=call_metadata,
    )
    db.add(db_call)
    db.commit()
    
    return {
        "call_id": call_id,
        "agent_id": db_call.agent_id,
        "already_exists": False,
        "metadata": ensure_custom_params(db_call.call_metadata),
    }


# ==================== Admin: Clear Calls ====================

@app.delete("/api/admin/calls/clear")
async def clear_calls(keep_call_id: Optional[int] = None, db: Session = Depends(get_database)):
    """Delete all calls, optionally keep one by ID"""
    try:
        # First get call IDs to delete
        if keep_call_id:
            calls_to_delete = db.query(CallModel).filter(CallModel.id != keep_call_id).all()
            call_ids = [c.call_id for c in calls_to_delete]
        else:
            all_calls = db.query(CallModel).all()
            call_ids = [c.call_id for c in all_calls]
        
        # Delete transcripts for these calls first
        if call_ids:
            db.query(TranscriptModel).filter(TranscriptModel.call_id.in_(call_ids)).delete(synchronize_session=False)
        
        # Delete calls
        if keep_call_id:
            db.query(CallModel).filter(CallModel.id != keep_call_id).delete()
        else:
            db.query(CallModel).delete()
        
        db.commit()
        
        if keep_call_id:
            return {"message": f"Deleted all calls except ID {keep_call_id}"}
        else:
            return {"message": "Deleted all calls"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}


# ==================== Comprehensive Call History Endpoints ====================

@app.get("/api/call-history")
async def get_call_history(
    page: int = 1,
    limit: int = 50,
    direction: Optional[str] = None,
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    call_type: Optional[str] = None,
    db: Session = Depends(get_database)
):
    """Get paginated call history with agent names and cost details"""
    query = db.query(CallModel)
    normalized_direction_filter = normalize_call_direction(direction, default="") if direction else ""
    
    if normalized_direction_filter == "inbound":
        query = query.filter(
            or_(
                CallModel.direction.ilike("inbound"),
                CallModel.call_id.ilike("inbound_%"),
            )
        )
    elif normalized_direction_filter == "outbound":
        query = query.filter(
            or_(
                CallModel.direction.ilike("outbound"),
                CallModel.call_id.ilike("outbound_%"),
                CallModel.call_type == "web",
            )
        )
    if agent_id:
        query = query.filter(CallModel.agent_id == agent_id)
    if status:
        query = query.filter(CallModel.status == status)
    if call_type:
        query = query.filter(CallModel.call_type == call_type)
    
    total = query.count()
    offset = (page - 1) * limit
    calls = query.order_by(CallModel.created_at.desc()).offset(offset).limit(limit).all()
    
    # Enrich with agent names
    result = []
    for call in calls:
        agent = db.query(AgentModel).filter(AgentModel.id == call.agent_id).first()
        
        # Calculate duration from timestamps if null
        duration = call.duration_seconds
        if not duration and call.ended_at and call.created_at:
            delta = call.ended_at - call.created_at
            duration = int(delta.total_seconds())
        
        # Count transcript entries
        transcript_count = db.query(TranscriptModel).filter(
            TranscriptModel.call_id == call.call_id
        ).count()
        
        result.append({
            "id": call.id,
            "call_id": call.call_id,
            "agent_id": call.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "room_name": call.room_name,
            "call_type": call.call_type,
            "direction": normalize_call_direction_for_row(call),
            "status": call.status,
            "from_number": call.from_number,
            "to_number": call.to_number,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": duration,
            "cost_usd": round(call.cost_usd or 0, 6),
            "llm_cost": round(call.llm_cost or 0, 6),
            "stt_cost": round(call.stt_cost or 0, 6),
            "tts_cost": round(call.tts_cost or 0, 6),
            "llm_tokens_in": call.llm_tokens_in or 0,
            "llm_tokens_out": call.llm_tokens_out or 0,
            "llm_model_used": call.llm_model_used,
            "stt_duration_ms": call.stt_duration_ms or 0,
            "tts_characters": call.tts_characters or 0,
            "tts_provider": ensure_custom_params(call.call_metadata).get("tts_provider", DEFAULT_TTS_PROVIDER),
            "tts_model_used": ensure_custom_params(call.call_metadata).get("tts_model"),
            "transcript_count": transcript_count,
            "transcript_summary": call.transcript_summary,
            "error_message": call.error_message,
            "created_at": call.created_at.isoformat() if call.created_at else None,
        })
    
    return {
        "calls": result,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@app.get("/api/call-history/{call_id}/details")
async def get_call_details(call_id: str, db: Session = Depends(get_database)):
    """Get full call details including transcript, costs, and latency"""
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    agent = db.query(AgentModel).filter(AgentModel.id == call.agent_id).first()
    
    # Calculate duration from timestamps if null
    duration = call.duration_seconds
    if not duration and call.ended_at and call.created_at:
        delta = call.ended_at - call.created_at
        duration = int(delta.total_seconds())
    
    # Get full transcript
    transcripts = db.query(TranscriptModel).filter(
        TranscriptModel.call_id == call_id
    ).order_by(TranscriptModel.timestamp).all()
    
    # Calculate latency stats
    stt_latencies = [t.stt_latency_ms for t in transcripts if t.stt_latency_ms]
    llm_latencies = [t.llm_latency_ms for t in transcripts if t.llm_latency_ms]
    tts_latencies = [t.tts_latency_ms for t in transcripts if t.tts_latency_ms]
    
    return {
        "call": {
            "call_id": call.call_id,
            "agent_id": call.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "room_name": call.room_name,
            "call_type": call.call_type,
            "direction": normalize_call_direction_for_row(call),
            "status": call.status,
            "from_number": call.from_number,
            "to_number": call.to_number,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": duration,
            "recording_url": call.recording_url,
            "error_message": call.error_message,
        },
        "costs": {
            "total_usd": round(call.cost_usd or 0, 6),
            "llm_cost": round(call.llm_cost or 0, 6),
            "stt_cost": round(call.stt_cost or 0, 6),
            "tts_cost": round(call.tts_cost or 0, 6),
        },
        "usage": {
            "llm_model": call.llm_model_used,
            "llm_tokens_in": call.llm_tokens_in or 0,
            "llm_tokens_out": call.llm_tokens_out or 0,
            "stt_duration_ms": call.stt_duration_ms or 0,
            "stt_duration_formatted": f"{(call.stt_duration_ms or 0) / 1000:.1f}s",
            "tts_characters": call.tts_characters or 0,
            "tts_provider": ensure_custom_params(call.call_metadata).get("tts_provider", DEFAULT_TTS_PROVIDER),
            "tts_model": ensure_custom_params(call.call_metadata).get("tts_model"),
            "tts_cost_source": ensure_custom_params(call.call_metadata).get("tts_cost_source"),
        },
        "latency": {
            "stt_avg_ms": round(sum(stt_latencies) / len(stt_latencies)) if stt_latencies else None,
            "llm_avg_ms": round(sum(llm_latencies) / len(llm_latencies)) if llm_latencies else None,
            "tts_avg_ms": round(sum(tts_latencies) / len(tts_latencies)) if tts_latencies else None,
            "stt_p95_ms": sorted(stt_latencies)[int(len(stt_latencies)*0.95)] if len(stt_latencies) > 1 else (stt_latencies[0] if stt_latencies else None),
            "llm_p95_ms": sorted(llm_latencies)[int(len(llm_latencies)*0.95)] if len(llm_latencies) > 1 else (llm_latencies[0] if llm_latencies else None),
        },
        "transcript": [
            {
                "role": t.role,
                "content": t.content,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "is_final": t.is_final,
                "confidence": t.confidence,
                "latency": {
                    "stt_ms": t.stt_latency_ms,
                    "llm_ms": t.llm_latency_ms,
                    "tts_ms": t.tts_latency_ms
                }
            }
            for t in transcripts
        ],
        "metadata": call.call_metadata,
    }


# Webhook endpoint for triggering outbound calls from n8n or other automation tools
@app.post("/api/webhook/outbound-call")
async def webhook_outbound_call(
    request: dict,  # Accept JSON payload
    db: Session = Depends(get_database)
):
    """
    Webhook endpoint to trigger outbound calls.
    
    Payload (JSON):
    {
        "to_number": "+1234567890",  # Phone number to call (E.164 format)
        "agent_id": 1,               # Agent ID to use for the call
        "phone_id": 1,               # (Optional) Phone number ID to use - if not provided, uses default
        "name": "John",              # Optional runtime vars available in agent prompt as {name}
        "company_name": "Acme"       # Optional runtime vars available as {company_name}
    }
    
    Example n8n call:
    POST http://your-server:8000/api/webhook/outbound-call
    {
        "to_number": "+1234567890",
        "agent_id": 1
    }
    """
    if not isinstance(request, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    to_number = str(request.get("to_number", "")).strip()
    raw_agent_id = request.get("agent_id")
    raw_phone_id = request.get("phone_id", request.get("phone_number_id"))
    explicit_runtime_vars = normalize_runtime_vars(request.get("runtime_vars"))
    reserved_keys = {
        "to_number",
        "agent_id",
        "phone_id",
        "phone_number_id",
        "runtime_vars",
    }
    extra_runtime_vars = normalize_runtime_vars(
        {k: v for k, v in request.items() if str(k) not in reserved_keys}
    )
    runtime_vars = {**explicit_runtime_vars, **extra_runtime_vars}

    if not to_number:
        raise HTTPException(status_code=400, detail="to_number is required")
    if not to_number.startswith("+"):
        raise HTTPException(status_code=400, detail="to_number must be in E.164 format (example: +1234567890)")

    agent_id: Optional[int] = None
    phone_id: Optional[int] = None
    try:
        if raw_agent_id is not None:
            agent_id = int(raw_agent_id)
    except Exception:
        raise HTTPException(status_code=400, detail="agent_id must be an integer")
    try:
        if raw_phone_id is not None:
            phone_id = int(raw_phone_id)
    except Exception:
        raise HTTPException(status_code=400, detail="phone_id must be an integer")

    if agent_id is None and phone_id is None:
        raise HTTPException(status_code=400, detail="Provide at least one of agent_id or phone_id")

    phone: Optional[PhoneNumberModel] = None
    if phone_id is not None:
        phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
        if not phone:
            raise HTTPException(status_code=404, detail="Phone number not found")
    elif agent_id is not None:
        # Prefer an enabled outbound mapping for the requested agent.
        phone = (
            db.query(PhoneNumberModel)
            .filter(
                PhoneNumberModel.outbound_agent_id == agent_id,
                PhoneNumberModel.enable_outbound.is_(True),
            )
            .order_by(PhoneNumberModel.updated_at.desc())
            .first()
        )
        if not phone:
            phone = (
                db.query(PhoneNumberModel)
                .filter(PhoneNumberModel.outbound_agent_id == agent_id)
                .order_by(PhoneNumberModel.updated_at.desc())
                .first()
            )
        if not phone:
            raise HTTPException(status_code=404, detail="No phone number mapped for outbound on this agent")

    if not phone:
        raise HTTPException(status_code=404, detail="No phone number available")
    if not phone.enable_outbound:
        raise HTTPException(status_code=400, detail="Outbound calling is disabled for this phone number")

    resolved_agent_id = phone.outbound_agent_id if phone.outbound_agent_id else agent_id
    if resolved_agent_id is None:
        raise HTTPException(status_code=400, detail="No outbound agent configured on this phone number")

    if agent_id is not None and phone.outbound_agent_id and phone.outbound_agent_id != agent_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"phone_id {phone.id} is mapped to outbound_agent_id {phone.outbound_agent_id}, "
                f"but request agent_id is {agent_id}"
            ),
        )

    resolved_agent = db.query(AgentModel).filter(AgentModel.id == resolved_agent_id).first()
    if not resolved_agent:
        raise HTTPException(status_code=404, detail="Outbound agent not found")

    try:
        call_request = OutboundCallRequest(
            to_number=to_number,
            phone_number_id=phone.id,
            runtime_vars=runtime_vars,
        )
        return await make_outbound_call(phone.id, call_request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook outbound call failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/llm-status")
async def get_llm_status(db: Session = Depends(get_database)):
    """Check LLM provider status and recent quota errors"""
    try:
        # Get recent calls with quota/insufficient balance errors
        recent_calls = db.query(CallModel).filter(
            CallModel.created_at >= datetime.utcnow() - timedelta(hours=24),
            CallModel.error_message.isnot(None)
        ).order_by(CallModel.created_at.desc()).limit(10).all()
        
        quota_errors = []
        for call in recent_calls:
            error_msg = call.error_message or ""
            if any(keyword in error_msg.lower() for keyword in ['quota', 'insufficient', 'billing', 'balance', '429', '401']):
                agent = db.query(AgentModel).filter(AgentModel.id == call.agent_id).first()
                quota_errors.append({
                    "agent_id": call.agent_id,
                    "agent_name": agent.name if agent else "Unknown",
                    "llm_model": agent.llm_model if agent else "Unknown",
                    "error": error_msg,
                    "timestamp": call.created_at.isoformat() if call.created_at else None
                })
        
        # Check which models are being used
        active_agents = db.query(AgentModel).all()
        models_in_use = list(set([agent.llm_model for agent in active_agents if agent.llm_model]))
        
        return {
            "quota_errors": quota_errors[:5],  # Return last 5 errors
            "models_in_use": models_in_use,
            "has_quota_error": len(quota_errors) > 0
        }
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return {"quota_errors": [], "models_in_use": [], "has_quota_error": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
