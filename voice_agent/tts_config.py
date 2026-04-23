"""
Voice Agent - TTS Configuration Module
Handles TTS provider selection, voice settings, and model resolution.
"""

import os
import logging
from typing import Dict, Any, Optional

from voice_agent.config import (
    DEFAULT_TTS_PROVIDER,
    DEFAULT_ELEVENLABS_MODEL,
    DEFAULT_AGENT_VOICE_SPEED,
    MIN_AGENT_VOICE_SPEED,
    MAX_AGENT_VOICE_SPEED,
    DEEPGRAM_VOICE_MAP,
    ELEVENLABS_VOICE_MAP,
)

logger = logging.getLogger("voice_agent")

def get_elevenlabs_api_key() -> str:
    return (os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY") or "").strip()

def is_elevenlabs_v3_model(model_id: Any) -> bool:
    candidate = str(model_id or "").strip().lower()
    return "v3" in candidate and "flash" not in candidate

def _coerce_setting_float(value: Any, default: float, min_value: float, max_value: float) -> float:
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

def resolve_voice_speed(config: Dict[str, Any]) -> float:
    custom_params = config.get("custom_params") or {}
    return _coerce_setting_float(
        config.get("voice_speed", custom_params.get("voice_speed")),
        default=DEFAULT_AGENT_VOICE_SPEED,
        min_value=MIN_AGENT_VOICE_SPEED,
        max_value=MAX_AGENT_VOICE_SPEED,
    )

def build_elevenlabs_voice_settings(
    config: Dict[str, Any],
    voice_speed: float,
    *,
    include_extended_settings: bool = True,
):
    try:
        from livekit.plugins.elevenlabs import VoiceSettings as ElevenVoiceSettings
    except Exception:
        return None
    
    custom_params = config.get("custom_params") or {}
    raw = custom_params.get("elevenlabs_voice_settings")
    raw_settings = raw if isinstance(raw, dict) else {}
    
    stability = _coerce_setting_float(raw_settings.get("stability"), default=0.5, min_value=0.0, max_value=1.0)
    similarity_boost = _coerce_setting_float(raw_settings.get("similarity_boost"), default=0.75, min_value=0.0, max_value=1.0)
    speed = _coerce_setting_float(voice_speed, default=DEFAULT_AGENT_VOICE_SPEED, min_value=MIN_AGENT_VOICE_SPEED, max_value=MAX_AGENT_VOICE_SPEED)
    
    kwargs: Dict[str, Any] = {"speed": speed}
    if include_extended_settings and "style" in raw_settings:
        kwargs["style"] = _coerce_setting_float(raw_settings.get("style"), default=0.0, min_value=0.0, max_value=1.0)
    if include_extended_settings and "use_speaker_boost" in raw_settings:
        kwargs["use_speaker_boost"] = bool(raw_settings.get("use_speaker_boost"))
    
    try:
        return ElevenVoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            **kwargs,
        )
    except Exception as e:
        logger.warning(f"Failed to construct ElevenLabs VoiceSettings; falling back without speed override: {e}")
        return None

def resolve_tts_provider(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    provider = (
        config.get("tts_provider")
        or custom_params.get("tts_provider")
        or DEFAULT_TTS_PROVIDER
    )
    provider = str(provider).strip().lower()
    if provider not in ("deepgram", "elevenlabs"):
        provider = DEFAULT_TTS_PROVIDER
    return provider

def resolve_tts_model(config: Dict[str, Any], language: str) -> str:
    custom_params = config.get("custom_params") or {}
    tts_model = custom_params.get("tts_model")
    if tts_model:
        return str(tts_model)
    return DEFAULT_ELEVENLABS_MODEL

def resolve_stt_language(language: Any) -> str:
    normalized_language = str(language or "").strip()
    if normalized_language == "multi":
        return "multi"
    if normalized_language in {"ml", "ml-IN"}:
        logger.warning(
            f"Language {normalized_language} selected, Deepgram doesn't support Malayalam directly. "
            "Using language=multi for code-switching."
        )
        return "multi"
    if normalized_language in {"hi", "hi-IN"}:
        return "hi"
    return normalized_language
