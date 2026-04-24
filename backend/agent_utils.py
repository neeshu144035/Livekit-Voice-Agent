import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from backend.constants import (
    VALID_LLM_MODELS,
    VALID_VOICES,
    VALID_LANGUAGES,
    VALID_TTS_PROVIDERS,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_AGENT_LLM_TEMPERATURE,
    DEFAULT_AGENT_VOICE_SPEED,
    MIN_AGENT_LLM_TEMPERATURE,
    MAX_AGENT_LLM_TEMPERATURE,
    MIN_AGENT_VOICE_SPEED,
    MAX_AGENT_VOICE_SPEED,
    DEEPGRAM_VOICE_OPTIONS,
    DEEPGRAM_VOICE_ALIASES
)
from backend.models import AgentModel

logger = logging.getLogger("backend-api")

def normalize_tts_provider(provider: Optional[str], voice: Optional[str]) -> str:
    if not provider:
        return DEFAULT_TTS_PROVIDER
    provider = provider.lower().strip()
    if provider in {"deepgram", "dg"}:
        return "deepgram"
    if provider in {"elevenlabs", "eleven", "el"}:
        return "elevenlabs"
    return DEFAULT_TTS_PROVIDER

def resolve_display_name(name: str, display_name: Optional[str]) -> str:
    return (display_name or name).strip() or "Unnamed Agent"

def ensure_custom_params(params: Any) -> Dict[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, dict):
        try:
            import json
            return json.loads(params) if isinstance(params, str) else {}
        except:
            return {}
    return params

def _coerce_agent_setting_float(value: Any, default: float, min_value: float, max_value: float) -> float:
    try:
        if value is None:
            return default
        f_val = float(value)
        return max(min_value, min(max_value, f_val))
    except (ValueError, TypeError):
        return default

def extract_agent_tts_settings(agent: AgentModel) -> Dict[str, Any]:
    params = ensure_custom_params(agent.custom_params)
    return {
        "tts_provider": params.get("tts_provider", DEFAULT_TTS_PROVIDER),
        "tts_model": params.get("tts_model"),
        "voice": agent.voice,
    }

def resolve_agent_llm_temperature_from_params(params: Dict[str, Any]) -> float:
    val = params.get("llm_temperature")
    return _coerce_agent_setting_float(val, DEFAULT_AGENT_LLM_TEMPERATURE, MIN_AGENT_LLM_TEMPERATURE, MAX_AGENT_LLM_TEMPERATURE)

def resolve_agent_voice_speed_from_params(params: Dict[str, Any]) -> float:
    val = params.get("voice_speed")
    return _coerce_agent_setting_float(val, DEFAULT_AGENT_VOICE_SPEED, MIN_AGENT_VOICE_SPEED, MAX_AGENT_VOICE_SPEED)

def serialize_agent(agent: AgentModel) -> Dict[str, Any]:
    params = ensure_custom_params(agent.custom_params)
    return {
        "id": agent.id,
        "name": agent.name,
        "display_name": getattr(agent, "display_name", None) or agent.name,
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "voice": agent.voice,
        "tts_provider": params.get("tts_provider", DEFAULT_TTS_PROVIDER),
        "tts_model": params.get("tts_model"),
        "language": agent.language,
        "twilio_number": agent.twilio_number,
        "welcome_message_type": agent.welcome_message_type,
        "welcome_message": agent.welcome_message,
        "max_call_duration": agent.max_call_duration,
        "enable_recording": agent.enable_recording,
        "webhook_url": agent.webhook_url,
        "llm_temperature": params.get("llm_temperature", DEFAULT_AGENT_LLM_TEMPERATURE),
        "voice_speed": params.get("voice_speed", DEFAULT_AGENT_VOICE_SPEED),
        "custom_params": params,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }
