import os
import json
import asyncio
import logging
import time
from datetime import datetime
import atexit
import signal
import re
import uuid
import inspect
import contextlib
from dotenv import load_dotenv
from typing import Annotated, Optional, Dict, Any, List

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import deepgram, openai, silero, elevenlabs
try:
    from livekit.plugins import xai
except Exception:
    xai = None  # type: ignore[assignment]
try:
    from livekit.plugins.elevenlabs import VoiceSettings as ElevenVoiceSettings
except Exception:
    ElevenVoiceSettings = None  # type: ignore[assignment]
import livekit.agents.llm as llm_module
from livekit.agents.voice.room_io.types import RoomOptions
import httpx

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-retell")

DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://host.docker.internal:8000").rstrip("/")
DEFAULT_WORKER_DISPATCH_NAME = (
    os.getenv("LIVEKIT_WORKER_AGENT_NAME", "voice-agent") or "voice-agent"
).strip().lower()
MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "1800"))
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"
DEFAULT_XAI_REALTIME_MODEL = os.getenv("XAI_REALTIME_MODEL", "grok-voice-think-fast-1.0").strip() or "grok-voice-think-fast-1.0"
XAI_REALTIME_BASE_URL = os.getenv("XAI_REALTIME_BASE_URL", "https://api.x.ai/v1").strip() or "https://api.x.ai/v1"
DEFAULT_AGENT_LLM_TEMPERATURE = 0.2
DEFAULT_AGENT_VOICE_SPEED = 1.0
MIN_AGENT_LLM_TEMPERATURE = 0.0
MAX_AGENT_LLM_TEMPERATURE = 1.5
MIN_AGENT_VOICE_SPEED = 0.8
MAX_AGENT_VOICE_SPEED = 1.2
TRANSFER_HANDOFF_DELAY_SEC = float(os.getenv("TRANSFER_HANDOFF_DELAY_SEC", "0.1"))
SUBAGENT_GREETING_DELAY_SEC = float(os.getenv("SUBAGENT_GREETING_DELAY_SEC", "0.5"))
END_CALL_DISCONNECT_DELAY_SEC = float(os.getenv("END_CALL_DISCONNECT_DELAY_SEC", "1.0"))
DISCONNECT_GRACE_SEC = float(os.getenv("DISCONNECT_GRACE_SEC", "20"))
CHAT_REPLY_TIMEOUT_SEC = float(os.getenv("CHAT_REPLY_TIMEOUT_SEC", "40"))
SILENCE_REPROMPT_SEC = float(os.getenv("SILENCE_REPROMPT_SEC", "20"))
SILENCE_REPROMPT_MAX_PER_CALL = int(os.getenv("SILENCE_REPROMPT_MAX_PER_CALL", "6"))
STT_ENDPOINTING_PHONE_MS = int(os.getenv("STT_ENDPOINTING_PHONE_MS", "40"))
STT_ENDPOINTING_WEB_MS = int(os.getenv("STT_ENDPOINTING_WEB_MS", "40"))
SESSION_MIN_ENDPOINTING_DELAY = float(os.getenv("SESSION_MIN_ENDPOINTING_DELAY", "0.03"))
SESSION_MAX_ENDPOINTING_DELAY = float(os.getenv("SESSION_MAX_ENDPOINTING_DELAY", "0.12"))
SESSION_PREEMPTIVE_GENERATION = os.getenv("SESSION_PREEMPTIVE_GENERATION", "1").strip().lower() in {"1", "true", "yes", "on"}
VAD_MIN_SPEECH_DURATION = float(os.getenv("VAD_MIN_SPEECH_DURATION", "0.02"))
VAD_MIN_SILENCE_DURATION = float(os.getenv("VAD_MIN_SILENCE_DURATION", "0.12"))
VAD_PREFIX_PADDING_DURATION = float(os.getenv("VAD_PREFIX_PADDING_DURATION", "0.18"))
ELEVENLABS_STREAMING_LATENCY = int(os.getenv("ELEVENLABS_STREAMING_LATENCY", "0"))
ELEVENLABS_AUTO_MODE = os.getenv("ELEVENLABS_AUTO_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_OPENAI_REASONING_EFFORT = (os.getenv("OPENAI_REASONING_EFFORT", "low") or "low").strip().lower()
DEFAULT_OPENAI_VERBOSITY = (os.getenv("OPENAI_VERBOSITY", "low") or "low").strip().lower()
DEFAULT_OPENAI_MAX_COMPLETION_TOKENS = int(os.getenv("OPENAI_MAX_COMPLETION_TOKENS", "220"))
PHONE_LOW_LATENCY_MAX_TOKENS = int(os.getenv("PHONE_LOW_LATENCY_MAX_TOKENS", "80"))
OPENAI_REALTIME_TURN_MODE = (os.getenv("OPENAI_REALTIME_TURN_MODE", "server_vad") or "server_vad").strip().lower()
OPENAI_REALTIME_SEMANTIC_EAGERNESS = (os.getenv("OPENAI_REALTIME_SEMANTIC_EAGERNESS", "high") or "high").strip().lower()
OPENAI_REALTIME_VAD_THRESHOLD = float(os.getenv("OPENAI_REALTIME_VAD_THRESHOLD", "0.45"))
OPENAI_REALTIME_PREFIX_PADDING_MS = int(os.getenv("OPENAI_REALTIME_PREFIX_PADDING_MS", "150"))
OPENAI_REALTIME_SILENCE_DURATION_MS = int(os.getenv("OPENAI_REALTIME_SILENCE_DURATION_MS", "200"))
INITIAL_GREETING_WAIT_FOR_PARTICIPANT_SEC = float(os.getenv("INITIAL_GREETING_WAIT_FOR_PARTICIPANT_SEC", "20"))
STRICT_PROMPT_TOOL_FILTER = os.getenv("STRICT_PROMPT_TOOL_FILTER", "1").strip().lower() not in {"0", "false", "no", "off"}
USE_DISPATCH_NAME_INBOUND_FALLBACK = os.getenv("USE_DISPATCH_NAME_INBOUND_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}
DEEPGRAM_STT_PHONE_MODEL = os.getenv("DEEPGRAM_STT_PHONE_MODEL", "nova-3").strip() or "nova-3"
DEEPGRAM_STT_WEB_MODEL = os.getenv("DEEPGRAM_STT_WEB_MODEL", "nova-3").strip() or "nova-3"

_dashboard_api_client: Optional[httpx.AsyncClient] = None

EMAIL_SPELLING_POLICY = (
    "STRICT SPELLING RULES:\n"
    "- When asked to spell an email address, spell each character individually (e.g., \"n, e, e, s, h, u\").\n"
    "- Do NOT use NATO/phonetic words (e.g., \"n for november\").\n"
    "- Use the words \"at\" and \"dot\" only for @ and .\n"
    "- For phone numbers, read each digit individually."
)

DEEPGRAM_VOICE_MAP = {
    "jessica": "aura-asteria-en",
    "mark": "aura-orion-en",
    "sarah": "aura-luna-en",
    "michael": "aura-perseus-en",
    "emma": "aura-hera-en",
    "james": "aura-zeus-en",
}

ELEVENLABS_VOICE_MAP = {
    "jessica": "EXAVITQu4vr4xnSDxMaL",  # Bella
    "mark": "TxGEqnHWrfWFTfGW9XjX",  # Josh
    "sarah": "oWAxZDx7w5VEj9dCyTpo",  # Grace
    "michael": "NMWYbVa3kjyX8aT8TtW9",  # Dominic
    "emma": "MF3mGyEYCl7XYWbV9V6O",  # Elli
    "james": "VR6AewLTigWG4xSOukaG",  # Arnold
}
XAI_VOICE_IDS = {"eve", "ara", "rex", "sal", "leo"}
XAI_VOICE_NAME_MAP = {
    "ara": "Ara",
    "eve": "Eve",
    "leo": "Leo",
    "rex": "Rex",
    "sal": "Sal",
}
CANONICAL_TRANSFER_TOOL_NAME = "call_transfer"
TRANSFER_DUPLICATE_SUPPRESS_SEC = float(os.getenv("TRANSFER_DUPLICATE_SUPPRESS_SEC", "20"))
DOUBLE_TEMPLATE_VAR_PATTERN = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")
SINGLE_TEMPLATE_VAR_PATTERN = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")

ELEVENLABS_V3_REQUIRED_LANGUAGES = {"ml", "ml-IN", "multi"}
LANGUAGE_NAME_MAP = {
    "en": "English",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-AU": "English (Australia)",
    "en-IN": "English (India)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "hi": "Hindi",
    "hi-IN": "Hindi",
    "ml": "Malayalam",
    "ml-IN": "Malayalam",
    "multi": "Multilingual",
}
AUTO_GREETING_FALLBACKS = {
    "en": "Hello, how can I help you today?",
    "en-US": "Hello, how can I help you today?",
    "en-GB": "Hello, how can I help you today?",
    "en-AU": "Hello, how can I help you today?",
    "en-IN": "Hello, how can I help you today?",
    "multi": "Hello, how can I help you today?",
    "es": "Hola, en que puedo ayudarte hoy?",
    "fr": "Bonjour, comment puis-je vous aider aujourd'hui ?",
    "de": "Hallo, wie kann ich Ihnen heute helfen?",
    "it": "Ciao, come posso aiutarla oggi?",
    "hi": "αñ¿αñ«αñ╕αÑìαññαÑç, αñ«αÑêαñé αñåαñ¬αñòαÑÇ αñòαÑêαñ╕αÑç αñ«αñªαñª αñòαñ░ αñ╕αñòαññαñ╛ αñ╣αÑéαñü?",
    "hi-IN": "αñ¿αñ«αñ╕αÑìαññαÑç, αñ«αÑêαñé αñåαñ¬αñòαÑÇ αñòαÑêαñ╕αÑç αñ«αñªαñª αñòαñ░ αñ╕αñòαññαñ╛ αñ╣αÑéαñü?",
    "ml": "α┤¿α┤«α┤╕α╡ìα┤òα┤╛α┤░α┤é, α┤₧α┤╛α╡╗ α┤¿α┤┐α┤Öα╡ìα┤Öα┤│α╡å α┤Äα┤Öα╡ìα┤Öα┤¿α╡å α┤╕α┤╣α┤╛α┤»α┤┐α┤òα╡ìα┤òα┤╛α┤é?",
    "ml-IN": "α┤¿α┤«α┤╕α╡ìα┤òα┤╛α┤░α┤é, α┤₧α┤╛α╡╗ α┤¿α┤┐α┤Öα╡ìα┤Öα┤│α╡å α┤Äα┤Öα╡ìα┤Öα┤¿α╡å α┤╕α┤╣α┤╛α┤»α┤┐α┤òα╡ìα┤òα┤╛α┤é?",
}
AUTO_GREETING_META_PREFIXES = (
    "you are ",
    "your role ",
    "role:",
    "objective:",
    "task:",
    "instructions",
    "instruction",
    "follow ",
    "do not ",
    "don't ",
    "never ",
    "always ",
    "respond ",
    "reply ",
    "speak ",
    "act as ",
    "behave as ",
    "system prompt",
    "assistant prompt",
    "persona:",
    "tone:",
)
AUTO_GREETING_META_SUBSTRINGS = (
    "system prompt",
    "internal logic",
    "tool speech behavior",
    "strict spelling rules",
    "prompt instructions",
    "configured persona",
    "configured language",
    "follow these instructions",
    "never repeat prompt instructions",
    "do not mention tools",
    "tools or internal logic",
    "respond only in",
    "speak only in",
)


def get_elevenlabs_api_key() -> str:
    return (os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY") or "").strip()


def get_xai_api_key() -> str:
    return (os.getenv("XAI_API_KEY") or "").strip()


def normalize_xai_voice_id(value: Any, default: str = "eve") -> str:
    voice_id = str(value or default).strip().lower() or default
    if voice_id not in XAI_VOICE_IDS:
        logger.warning("Unsupported xAI voice '%s'; falling back to %s", voice_id, default)
        return default
    return voice_id


def resolve_xai_runtime_voice_name(value: Any, default: str = "eve") -> str:
    return XAI_VOICE_NAME_MAP.get(normalize_xai_voice_id(value, default=default), XAI_VOICE_NAME_MAP["eve"])


def normalize_agent_language(language: Any, default: str = "en-GB") -> str:
    candidate = str(language or "").strip()
    return candidate or default


def is_elevenlabs_v3_model(model_id: Any) -> bool:
    candidate = str(model_id or "").strip().lower()
    return "v3" in candidate and "flash" not in candidate


def resolve_elevenlabs_tts_model_for_language(model_id: Any, language: Any) -> str:
    requested_model = str(model_id or "").strip()
    if requested_model:
        return requested_model
    raise RuntimeError(
        f"ElevenLabs selected but no tts_model was saved in the app for language={normalize_agent_language(language)}"
    )


def resolve_stt_language(language: Any) -> str:
    normalized_language = normalize_agent_language(language)
    if normalized_language == "multi":
        return "multi"
    if normalized_language in {"ml", "ml-IN"}:
        logger.warning(
            "Malayalam selected, but the current Deepgram streaming STT path does not natively support Malayalam. "
            "Using language=multi as the safest real-time fallback while ElevenLabs v3 handles multilingual TTS."
        )
        return "multi"
    return normalized_language


def build_language_enforcement_instruction(language: Any) -> str:
    normalized_language = normalize_agent_language(language, default="")
    if normalized_language in {"hi", "hi-IN"}:
        return (
            "CRITICAL SYSTEM INSTRUCTION: You must strictly speak and respond ONLY in Hindi natively. "
            "Do not use English unless strictly necessary for names or technical terms."
        )
    if normalized_language in {"ml", "ml-IN"}:
        return (
            "CRITICAL SYSTEM INSTRUCTION: You must strictly speak and respond ONLY in Malayalam natively. "
            "Do not use English unless strictly necessary for names or technical terms."
        )
    if normalized_language == "en-GB":
        return (
            "CRITICAL SYSTEM INSTRUCTION: Speak and respond in natural UK English. "
            "Prefer UK wording and spelling where appropriate."
        )
    if normalized_language == "en-IN":
        return (
            "CRITICAL SYSTEM INSTRUCTION: Speak and respond in natural Indian English. "
            "Keep the wording clear, friendly, and locally natural."
        )
    if normalized_language == "multi":
        return (
            "CRITICAL SYSTEM INSTRUCTION: This agent must operate multilingually. "
            "Mirror the caller's language naturally. If they speak English, reply in English. "
            "If they speak Hindi, reply in Hindi. If they speak Malayalam, reply in Malayalam. "
            "If they code-switch, you may code-switch naturally when it helps the conversation."
        )
    if normalized_language in {"es", "fr", "de", "it"}:
        language_name = LANGUAGE_NAME_MAP.get(normalized_language, normalized_language)
        return f"CRITICAL SYSTEM INSTRUCTION: You must strictly speak and respond ONLY in {language_name}."
    return ""


def build_tts_output_safety_instruction(tts_provider: str, tts_model: str) -> str:
    if str(tts_provider or "").strip().lower() != "elevenlabs":
        return ""
    if not is_elevenlabs_v3_model(tts_model):
        return ""
    return (
        "CRITICAL TTS OUTPUT RULES: Do not output raw SSML, XML, HTML, or angle-bracket tags such as <break>. "
        "Do not output asterisk actions like *smiles* or bracketed emotion tags like [warmly]. "
        "Do not speak unresolved template variables like {{name}}. "
        "Speak naturally using plain words and punctuation only."
    )


def normalize_tts_provider(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    provider = (
        config.get("tts_provider")
        or custom_params.get("tts_provider")
        or DEFAULT_TTS_PROVIDER
    )
    provider = str(provider).strip().lower()
    if provider not in ("deepgram", "elevenlabs", "xai"):
        provider = DEFAULT_TTS_PROVIDER
    return provider


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


def _coerce_setting_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < min_value:
        return min_value
    if number > max_value:
        return max_value
    return number


def _coerce_setting_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def get_dashboard_api_client() -> httpx.AsyncClient:
    global _dashboard_api_client
    if _dashboard_api_client is None:
        _dashboard_api_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _dashboard_api_client


def resolve_voice_runtime_mode(config: Dict[str, Any]) -> str:
    if normalize_tts_provider(config) == "xai":
        return "realtime_unified"
    custom_params = config.get("custom_params") or {}
    raw = str(custom_params.get("voice_runtime_mode") or "").strip().lower()
    if raw in {"pipeline", "realtime_text_tts", "realtime_unified"}:
        return raw
    return "pipeline"


def resolve_voice_realtime_model(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    if normalize_tts_provider(config) == "xai":
        return str(
            custom_params.get("voice_realtime_model")
            or config.get("tts_model")
            or custom_params.get("tts_model")
            or DEFAULT_XAI_REALTIME_MODEL
        ).strip() or DEFAULT_XAI_REALTIME_MODEL
    return str(custom_params.get("voice_realtime_model") or "").strip()


def _build_openai_realtime_turn_detection() -> Any:
    if OPENAI_REALTIME_TURN_MODE == "semantic_vad":
        payload: Dict[str, Any] = {
            "type": "semantic_vad",
            "eagerness": OPENAI_REALTIME_SEMANTIC_EAGERNESS,
            "create_response": True,
            "interrupt_response": True,
        }
    else:
        payload = {
            "type": "server_vad",
            "threshold": _coerce_setting_float(OPENAI_REALTIME_VAD_THRESHOLD, default=0.35, min_value=0.1, max_value=0.9),
            "prefix_padding_ms": _coerce_setting_int(OPENAI_REALTIME_PREFIX_PADDING_MS, default=300, min_value=50, max_value=500),
            "silence_duration_ms": _coerce_setting_int(OPENAI_REALTIME_SILENCE_DURATION_MS, default=600, min_value=80, max_value=800),
            "create_response": True,
            "interrupt_response": True,
        }
    try:
        from openai.types.beta.realtime.session import TurnDetection

        return TurnDetection(**payload)
    except Exception:
        return payload


def _build_xai_realtime_model(
    *,
    selected_voice: str,
    voice_realtime_model: str,
    xai_api_key: str,
) -> tuple[Any, str]:
    turn_detection = _build_openai_realtime_turn_detection()

    model_name = voice_realtime_model or DEFAULT_XAI_REALTIME_MODEL
    runtime_voice = resolve_xai_runtime_voice_name(selected_voice)

    if turn_detection is not None:
        if isinstance(turn_detection, dict):
            turn_detection = dict(turn_detection)
            turn_detection["silence_duration_ms"] = max(int(turn_detection.get("silence_duration_ms") or 0), 800)
        else:
            try:
                current_silence = int(getattr(turn_detection, "silence_duration_ms", 0) or 0)
                if current_silence < 800:
                    setattr(turn_detection, "silence_duration_ms", 800)
            except Exception:
                pass

    native_init_error = None
    if xai is not None and hasattr(xai, "realtime") and hasattr(xai.realtime, "RealtimeModel"):
        native_kwargs: Dict[str, Any] = {
            "model": model_name,
            "api_key": xai_api_key,
            "voice": runtime_voice,
        }
        if XAI_REALTIME_BASE_URL:
            native_kwargs["base_url"] = XAI_REALTIME_BASE_URL
        if turn_detection is not None:
            native_kwargs["turn_detection"] = turn_detection
        try:
            logger.info(
                "Instantiating xAI realtime model (native plugin) | Model: %s | Voice: %s",
                model_name,
                runtime_voice,
            )
            return xai.realtime.RealtimeModel(**native_kwargs), model_name
        except Exception as exc:
            native_init_error = exc
            logger.warning(
                "Native xAI realtime model init failed; falling back to OpenAI-compatible mode: %s",
                exc,
            )

    if not hasattr(openai, "realtime") or not hasattr(openai.realtime, "RealtimeModel"):
        if native_init_error is not None:
            raise RuntimeError(
                "xAI unified voice could not initialize via the native xAI plugin, and the OpenAI-compatible "
                "RealtimeModel fallback is unavailable."
            ) from native_init_error
        raise RuntimeError(
            "xAI unified voice requires livekit-plugins-xai or livekit-plugins-openai realtime support."
        )

    fallback_kwargs: Dict[str, Any] = {
        "model": model_name,
        "api_key": xai_api_key,
        "base_url": XAI_REALTIME_BASE_URL,
        "voice": runtime_voice,
        "modalities": ["audio"],
    }

    try:
        from livekit.plugins.openai.realtime.models import AudioTranscription

        fallback_kwargs["input_audio_transcription"] = AudioTranscription(model="whisper-1")
    except Exception:
        pass

    if turn_detection is not None:
        fallback_kwargs["turn_detection"] = turn_detection

    logger.info(
        "Instantiating xAI realtime model (OpenAI-compatible fallback) | Model: %s | Voice: %s",
        model_name,
        runtime_voice,
    )
    return openai.realtime.RealtimeModel(**fallback_kwargs), model_name


def resolve_llm_temperature(config: Dict[str, Any]) -> float:
    custom_params = config.get("custom_params") or {}
    return _coerce_setting_float(
        config.get("llm_temperature", custom_params.get("llm_temperature")),
        default=DEFAULT_AGENT_LLM_TEMPERATURE,
        min_value=MIN_AGENT_LLM_TEMPERATURE,
        max_value=MAX_AGENT_LLM_TEMPERATURE,
    )


def model_supports_custom_temperature(model_name: str) -> bool:
    model_l = (model_name or "").strip().lower()
    # GPT-5 family currently only accepts provider default temperature.
    if model_l.startswith("gpt-5"):
        return False
    return True


def resolve_voice_speed(config: Dict[str, Any]) -> float:
    custom_params = config.get("custom_params") or {}
    return _coerce_setting_float(
        config.get("voice_speed", custom_params.get("voice_speed")),
        default=DEFAULT_AGENT_VOICE_SPEED,
        min_value=MIN_AGENT_VOICE_SPEED,
        max_value=MAX_AGENT_VOICE_SPEED,
    )


def resolve_openai_reasoning_effort(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    raw = str(custom_params.get("llm_reasoning_effort", DEFAULT_OPENAI_REASONING_EFFORT) or DEFAULT_OPENAI_REASONING_EFFORT).strip().lower()
    if raw not in {"low", "medium", "high"}:
        return "low"
    return raw


def resolve_openai_verbosity(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    raw = str(custom_params.get("llm_verbosity", DEFAULT_OPENAI_VERBOSITY) or DEFAULT_OPENAI_VERBOSITY).strip().lower()
    if raw not in {"low", "medium", "high"}:
        return "low"
    return raw


def resolve_openai_max_completion_tokens(config: Dict[str, Any]) -> int:
    custom_params = config.get("custom_params") or {}
    return _coerce_setting_int(
        custom_params.get("llm_max_completion_tokens", DEFAULT_OPENAI_MAX_COMPLETION_TOKENS),
        default=DEFAULT_OPENAI_MAX_COMPLETION_TOKENS,
        min_value=64,
        max_value=1200,
    )


def build_elevenlabs_voice_settings(
    config: Dict[str, Any],
    voice_speed: float,
    *,
    include_extended_settings: bool = True,
):
    if ElevenVoiceSettings is None:
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


def _callable_supports_kwarg(callable_obj: Any, kwarg_name: str) -> bool:
    try:
        target = callable_obj.__init__ if inspect.isclass(callable_obj) else callable_obj
        sig = inspect.signature(target)
        if kwarg_name in sig.parameters:
            return True
        return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    except Exception:
        return False


def _normalize_tool_speech_flags(
    speak_during_execution: Any,
    speak_after_execution: Any,
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


def _is_transfer_tool(func_cfg: Dict[str, Any]) -> bool:
    tool_name = str(func_cfg.get("name", "")).strip().replace(" ", "_").lower() or ""
    system_type = _normalize_tool_name(func_cfg.get("system_type", ""))
    url = str(func_cfg.get("url", "")).strip()
    return (
        system_type in ("transfer_call", "agent_transfer")
        or url in ("builtin://transfer_call", "builtin://agent_transfer")
        or tool_name in ("transfer_call", "call_transfer", "agent_transfer")
        or tool_name.endswith("_agent_transfer")
    )


def _is_generic_transfer_tool_name(tool_name: str) -> bool:
    return _normalize_tool_name(tool_name) in {"transfer_call", "call_transfer"}


def _canonical_tool_name(tool_name: str) -> str:
    normalized = _normalize_tool_name(tool_name)
    if _is_generic_transfer_tool_name(normalized):
        return CANONICAL_TRANSFER_TOOL_NAME
    return normalized


def _extract_transfer_topic(tool_name: str) -> str:
    normalized = _canonical_tool_name(tool_name)
    if normalized.endswith("_agent_transfer"):
        normalized = normalized[: -len("_agent_transfer")]
    elif normalized.endswith("_transfer_call"):
        normalized = normalized[: -len("_transfer_call")]
    elif normalized in {"transfer_call", "call_transfer", "agent_transfer"}:
        normalized = ""
    return normalized.strip("_")


def _spoken_transfer_hints_for_tool(tool_name: str) -> List[str]:
    normalized = _normalize_tool_name(tool_name)
    topic = _extract_transfer_topic(normalized)
    hints = set(_tool_aliases(normalized))
    if topic:
        hints.update(
            {
                topic,
                topic.replace("_", " "),
                f"{topic} team",
            }
        )

    team_hints = {
        "renting": {"lettings", "letting", "lettings team", "renting", "renting team"},
        "buying": {"buying", "buying team", "buyer", "buyers"},
        "selling": {"selling", "selling team", "sales", "sales team"},
        "maintenance": {"maintenance", "maintenance team", "repair", "repairs"},
    }
    hints.update(team_hints.get(topic, set()))
    return [hint for hint in hints if hint]


def _tool_speech_instruction_line(func_cfg: Dict[str, Any]) -> str:
    tool_name = str(func_cfg.get("name", "")).strip().replace(" ", "_").lower() or "tool"
    if _is_transfer_tool(func_cfg):
        return ""

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


def build_transfer_instructions(functions_config: List[Dict[str, Any]]) -> str:
    instructions: List[str] = []
    for fn in functions_config or []:
        if not _is_transfer_tool(fn):
            continue
        tool_name = str(fn.get("name", "")).strip().replace(" ", "_").lower() or ""
        system_type = _normalize_tool_name(fn.get("system_type", ""))
        raw_description = re.sub(r"\s+", " ", str(fn.get("description", "")).strip())
        if tool_name.endswith("_agent_transfer"):
            topic = tool_name.replace("_agent_transfer", "").replace("_", " ").strip()
            trigger = f"If the caller asks for the {topic} team or agrees to that transfer"
        elif raw_description and normalize_text(raw_description) not in {"transfer", "transfer call", "agent transfer"}:
            trigger = f"If the caller's request matches this transfer ({raw_description})"
        elif system_type == "transfer_call":
            trigger = "If the caller asks to transfer, escalate, or speak to a human"
        else:
            trigger = "If the caller asks for another team/person or agrees to be transferred"
        instructions.append(
            f"{len(instructions)+1}. {trigger} -> DO NOT ask for permission or confirmation. -> "
            f"First say exactly 'I am transferring you now.' -> "
            f"immediately CALL `{tool_name}` TOOL -> STOP SPEAKING IMMEDIATELY. "
            "Do not add any explanations, helpful tips, or goodbye messages after calling the tool."
        )
    if not instructions:
        return ""
    return (
        "\nTRANSFER RULES — FOLLOW STRICTLY:\n"
        + "\n".join(instructions)
        + "\nDO NOT ask the user if they want to be transferred if they have already requested it or agreed to it. "
        + "\nCRITICAL SYSTEM INSTRUCTION: You MUST execute the ACTUAL JSON function call for the transfer tool. DO NOT simply say 'I am transferring you' and stop. You MUST trigger the tool itself. "
        + "\nAFTER EXECUTING THE TOOL FUNCTION CALL, YOU MUST STOP SPEAKING."
    )


def build_tool_speech_guidance(functions_config: List[Dict[str, Any]]) -> str:
    if not functions_config:
        return ""
    lines = [_tool_speech_instruction_line(fn) for fn in functions_config if fn.get("name")]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    return "Tool speech behavior (must follow per tool):\n" + "\n".join(lines)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_runtime_vars(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(data, dict):
        return {}
    normalized: Dict[str, str] = {}
    for raw_key, raw_value in data.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        if isinstance(raw_value, (dict, list)):
            normalized[key] = json.dumps(raw_value, ensure_ascii=False)
        elif raw_value is None:
            normalized[key] = ""
        else:
            normalized[key] = str(raw_value)
    return normalized


def apply_runtime_template(value: str, runtime_vars: Dict[str, str]) -> str:
    if not value:
        return value
    safe_runtime_vars = runtime_vars or {}

    def _resolve(match: re.Match[str]) -> str:
        key = match.group(1)
        return safe_runtime_vars.get(key, "")

    rendered = DOUBLE_TEMPLATE_VAR_PATTERN.sub(_resolve, value)
    rendered = SINGLE_TEMPLATE_VAR_PATTERN.sub(_resolve, rendered)
    rendered = re.sub(r"[ \t]{2,}", " ", rendered)
    rendered = re.sub(r"[ \t]+([?.!,;:])", r"\1", rendered)
    return rendered


def _resolve_time_of_day_label() -> str:
    hour = datetime.utcnow().hour
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def _strip_wrapping_quotes(text: str) -> str:
    stripped = (text or "").strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1].strip()
    return stripped


XAI_PROMPT_STYLE_TAG_PATTERN = re.compile(
    r"\[(?:warm|cheerful|excited|conversational tone|reassuring|sympathetic|concerned|serious tone|gentle|slow|whispers|laughs|matter-of-fact)\]",
    flags=re.IGNORECASE,
)


def strip_known_prompt_style_tags(text: str) -> str:
    cleaned = XAI_PROMPT_STYLE_TAG_PATTERN.sub("", text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def adapt_system_prompt_for_xai(system_prompt: str) -> str:
    lines = (system_prompt or "").splitlines()
    if not lines:
        return system_prompt

    cleaned_lines: List[str] = []
    skip_elevenlabs_audio_section = False

    for line in lines:
        stripped = (line or "").strip()
        normalized = normalize_text(stripped)

        if not skip_elevenlabs_audio_section and "tts audio tag instructions" in normalized and "elevenlabs" in normalized:
            skip_elevenlabs_audio_section = True
            continue

        if skip_elevenlabs_audio_section:
            if stripped.startswith("### ") or stripped.startswith("## "):
                skip_elevenlabs_audio_section = False
            else:
                continue

        cleaned_lines.append(strip_known_prompt_style_tags(line))

    adapted_prompt = "\n".join(cleaned_lines).strip()
    xai_instruction = (
        "CRITICAL SYSTEM INSTRUCTION: This call uses xAI's unified realtime voice model, not ElevenLabs. "
        "Ignore any ElevenLabs-v3 audio-tag instructions or square-bracket emotion cues in saved prompt text or examples. "
        "Keep the same persona, warmth, and pacing, but speak naturally using plain words only."
    )
    return f"{adapted_prompt}\n\n{xai_instruction}".strip()


def _clean_prompt_greeting_candidate(candidate: str) -> str:
    cleaned = (candidate or "").strip()
    if not cleaned or cleaned.startswith("#") or cleaned.startswith("---"):
        return ""
    cleaned = re.sub(r"^[\-\*]\s*", "", cleaned).strip()
    cleaned = re.sub(
        r"^(?:greeting|first message|opening line|opening greeting|say|script|general inquiry|general inquiries|general query|opening)\s*[:\-]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^(?:assistant|agent)\s*[:\-]\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*(?:->|→).*$", "", cleaned).strip()
    cleaned = strip_known_prompt_style_tags(cleaned)
    cleaned = _strip_wrapping_quotes(cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    
    # Root Cause Fix: Dynamic label stripping. 
    # Strips leading labels like "General Inquiries: Hello" -> "Hello"
    # or "Opening Script - Welcome" -> "Welcome".
    # Only strips if the prefix is short (label-like) and doesn't start with a greeting word.
    prefix_match = re.match(r"^([^:\-]{2,35})[:\-]\s+(.+)$", cleaned)
    if prefix_match:
        prefix, content = prefix_match.groups()
        prefix_lower = prefix.lower().strip()
        greeting_starters = ("hi", "hello", "hey", "welcome", "good morning", "good afternoon", "good evening", "namaste")
        if not any(prefix_lower.startswith(w) for w in greeting_starters):
            # It's a label, return the content
            cleaned = content.strip()

    if normalize_text(cleaned).startswith("bridge:"):
        return ""
    return cleaned


def _is_safe_auto_greeting(candidate: str) -> bool:
    cleaned = _clean_prompt_greeting_candidate(candidate)
    if not cleaned:
        return False
    if len(cleaned) > 220:
        return False
    if any(token in cleaned for token in ("{{", "}}", "<break", "</", "```")):
        return False
    normalized = normalize_text(cleaned)
    if normalized.startswith(AUTO_GREETING_META_PREFIXES):
        return False
    if any(snippet in normalized for snippet in AUTO_GREETING_META_SUBSTRINGS):
        return False
    return True


def extract_prompt_greeting(system_prompt: str) -> str:
    lines = (system_prompt or "").splitlines()
    if not lines:
        return ""

    start_idx = -1
    for idx, line in enumerate(lines):
        normalized = normalize_text(line)
        if "greeting" in normalized and (
            "first message" in normalized
            or normalized.startswith("### greeting")
            or normalized.startswith("## greeting")
            or normalized.startswith("# greeting")
        ):
            start_idx = idx
            break
    if start_idx < 0:
        return ""

    time_of_day = _resolve_time_of_day_label()
    fallback_candidate = ""
    for line in lines[start_idx + 1 : start_idx + 15]:
        raw_line = line.strip()
        if not raw_line:
            continue
        # Skip pure label lines like "General Inquiries:" or "Main Greeting:"
        if raw_line.endswith(":") and len(raw_line) < 40:
            continue
            
        candidate = _clean_prompt_greeting_candidate(line)
        if not candidate:
            continue
            
        # Skip technical candidates that only contain the labels we want to avoid
        if normalize_text(candidate) in ("general inquiries", "general inquiry", "general query", "opening script", "opening message"):
            continue
            
        candidate = re.sub(
            r"\[\s*morning\s*/\s*afternoon\s*/\s*evening\s*\]",
            time_of_day,
            candidate,
            flags=re.IGNORECASE,
        )
        if not _is_safe_auto_greeting(candidate):
            logger.warning("Discarded prompt-derived greeting candidate that looked like instructions")
            continue
        if normalize_text(candidate).endswith("is that?"):
            if not fallback_candidate:
                fallback_candidate = candidate
            continue
        return candidate
    return fallback_candidate


def build_safe_auto_greeting(language: Any, system_prompt: str) -> str:
    prompt_greeting = extract_prompt_greeting(system_prompt)
    if prompt_greeting:
        return prompt_greeting
    normalized_language = normalize_agent_language(language)
    return AUTO_GREETING_FALLBACKS.get(
        normalized_language,
        AUTO_GREETING_FALLBACKS.get(
            normalized_language.split("-", 1)[0],
            AUTO_GREETING_FALLBACKS["en-GB"],
        ),
    )


def resolve_welcome_message_mode(custom_params: Optional[Dict[str, Any]]) -> str:
    mode = str((custom_params or {}).get("welcome_message_mode") or "").strip().lower()
    return "custom" if mode == "custom" else "dynamic"


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


def filter_functions_by_prompt(
    functions_config: List[Dict[str, Any]],
    system_prompt: str,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    removed_names: List[str] = []
    for cfg in functions_config or []:
        tool_name = str(cfg.get("name", "")).strip()
        if tool_name and _is_tool_mentioned_in_prompt(tool_name, system_prompt):
            filtered.append(cfg)
        else:
            removed_names.append(tool_name or "<unknown>")

    if removed_names:
        logger.info(
            "Prompt tool filter removed tools not referenced in system prompt: %s",
            removed_names,
        )
    return filtered


def sum_usage_series(usage_payload: Dict[str, Any], key: Optional[str] = None) -> float:
    usage_map = usage_payload.get("usage") or {}
    if not usage_map:
        return 0.0

    if key and key in usage_map:
        series = usage_map.get(key) or []
        return float(series[-1]) if series else 0.0

    if "All" in usage_map:
        series = usage_map.get("All") or []
        return float(series[-1]) if series else 0.0

    total = 0.0
    for series in usage_map.values():
        if series:
            total += float(series[-1])
    return total


async def fetch_elevenlabs_character_stats(
    api_key: str,
    start_unix_ms: int,
    end_unix_ms: int,
    metric: str,
    breakdown_type: str,
) -> Dict[str, Any]:
    params = {
        "start_unix": start_unix_ms,
        "end_unix": end_unix_ms,
        "aggregation_interval": "cumulative",
        "metric": metric,
        "breakdown_type": breakdown_type,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/usage/character-stats",
            params=params,
            headers={"xi-api-key": api_key},
        )
        resp.raise_for_status()
        return resp.json() or {}


async def fetch_elevenlabs_history_items(
    api_key: str,
    start_unix_ms: int,
    end_unix_ms: int,
    voice_id: Optional[str],
    model_id: Optional[str],
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "page_size": 1000,
        "date_after_unix": int(start_unix_ms / 1000) - 2,
        "date_before_unix": int(end_unix_ms / 1000) + 2,
        "sort_direction": "asc",
        "source": "TTS",
    }
    if voice_id:
        params["voice_id"] = voice_id
    if model_id:
        params["model_id"] = model_id

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/history",
            params=params,
            headers={"xi-api-key": api_key},
        )
        resp.raise_for_status()
        payload = resp.json() or {}

    # ElevenLabs may return "history" or "items" depending on API generation.
    rows = payload.get("history")
    if rows is None:
        rows = payload.get("items")
    return rows or []


def estimate_call_characters_from_history(
    history_items: List[Dict[str, Any]],
    assistant_texts: List[str],
) -> Dict[str, int]:
    normalized_texts = [normalize_text(text) for text in assistant_texts if normalize_text(text)]
    total_chars = 0
    matched_chars = 0

    for row in history_items:
        start_count = row.get("character_count_change_from") or 0
        end_count = row.get("character_count_change_to") or 0
        char_count = max(int(end_count) - int(start_count), 0)
        if char_count <= 0:
            continue

        total_chars += char_count
        history_text = normalize_text(row.get("text") or "")
        if not history_text:
            continue

        if any(
            history_text == text
            or history_text in text
            or text in history_text
            for text in normalized_texts
        ):
            matched_chars += char_count

    if matched_chars <= 0 and total_chars > 0:
        matched_chars = total_chars

    return {
        "matched_chars": matched_chars,
        "total_chars": total_chars,
    }


# ==================== Usage Tracking (Global for atexit) ====================
_active_call_id = None
_active_usage = None

class UsageTracker:
    def __init__(self):
        self.llm_tokens_in = 0
        self.llm_tokens_out = 0
        self.llm_model = ""
        self.stt_duration_ms = 0
        self.stt_model = DEEPGRAM_STT_PHONE_MODEL  # Track STT model for accurate cost
        self.tts_characters = 0
        self.tts_provider = DEFAULT_TTS_PROVIDER
        self.tts_model = ""
        self.tts_voice_id = ""
        self.llm_temperature = DEFAULT_AGENT_LLM_TEMPERATURE
        self.voice_speed = DEFAULT_AGENT_VOICE_SPEED
        self.language = ""
        self.call_start_unix_ms = int(time.time() * 1000)
        self.transcript_entries = []
        self.assistant_texts = []
        self.call_start_time = time.time()
        self.usage_sent = False

    def add_llm_usage(self, tokens_in=0, tokens_out=0, model=""):
        self.llm_tokens_in += tokens_in
        self.llm_tokens_out += tokens_out
        if model:
            self.llm_model = model

    def add_stt_duration(self, duration_ms):
        self.stt_duration_ms += duration_ms

    def add_tts_characters(self, chars):
        self.tts_characters += chars

    def add_transcript(self, role, content):
        if self.transcript_entries:
            last_entry = self.transcript_entries[-1]
            if last_entry.get("role") == role and last_entry.get("content") == content:
                return
        self.transcript_entries.append({"role": role, "content": content})
        if role == "agent":
            self.assistant_texts.append(content)

    def get_transcript_summary(self):
        if not self.transcript_entries:
            return ""
        lines = []
        for entry in self.transcript_entries[-10:]:
            prefix = "Agent" if entry["role"] == "agent" else "User"
            lines.append(f"{prefix}: {entry['content'][:100]}")
        return "\n".join(lines)

    def get_call_duration(self):
        return int(time.time() - self.call_start_time)


def _send_usage_sync(call_id, tracker):
    """Synchronous usage sender for atexit handler"""
    if not call_id or tracker.usage_sent:
        return
    payload = {
        "llm_tokens_in": tracker.llm_tokens_in,
        "llm_tokens_out": tracker.llm_tokens_out,
        "actual_llm_tokens_in": tracker.llm_tokens_in,
        "actual_llm_tokens_out": tracker.llm_tokens_out,
        "llm_model_used": tracker.llm_model,
        "stt_duration_ms": tracker.stt_duration_ms,
        "actual_stt_minutes": round((tracker.stt_duration_ms or 0) / 60000.0, 6),
        "stt_model_used": tracker.stt_model if hasattr(tracker, 'stt_model') else DEEPGRAM_STT_PHONE_MODEL,
        "tts_characters": tracker.tts_characters,
        "actual_tts_characters": tracker.tts_characters,
        "tts_provider": tracker.tts_provider,
        "tts_model_used": tracker.tts_model,
        "tts_voice_id_used": tracker.tts_voice_id,
        "llm_temperature": tracker.llm_temperature,
        "voice_speed": tracker.voice_speed,
        "language": tracker.language,
        "transcript_summary": tracker.get_transcript_summary(),
        "actual_duration_seconds": tracker.get_call_duration(),
    }
    import urllib.request
    for attempt in range(1, 4):
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = getattr(resp, "status", 200)
                if status >= 400:
                    raise RuntimeError(f"HTTP {status}")
            tracker.usage_sent = True
            logger.info(f"[atexit] Sent usage for {call_id} (attempt {attempt})")
            break
        except Exception as e:
            logger.error(f"[atexit] Failed to send usage (attempt {attempt}/3): {e}")

    # Also end the call
    try:
        req2 = urllib.request.Request(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/end",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req2, timeout=5)
    except:
        pass


def _atexit_handler():
    global _active_call_id, _active_usage
    if _active_call_id and _active_usage:
        logger.info(f"[atexit] Sending final usage for {_active_call_id}")
        _send_usage_sync(_active_call_id, _active_usage)

atexit.register(_atexit_handler)


# ==================== API Helpers ====================

async def send_transcript_to_api(call_id, role, content):
    if not call_id:
        return False
    payload = {"role": role, "content": content, "is_final": True}
    for attempt in range(1, 4):
        try:
            await get_dashboard_api_client().post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/transcript",
                json=payload,
                timeout=8.0,
            )
            return True
        except Exception as e:
            logger.error("Error sending transcript for %s (attempt %s/3): %s", call_id, attempt, e)
            await asyncio.sleep(0.35 * attempt)
    return False


async def send_usage_to_api(call_id, tracker):
    if not call_id or tracker.usage_sent:
        return

    payload: Dict[str, Any] = {
        "llm_tokens_in": tracker.llm_tokens_in,
        "llm_tokens_out": tracker.llm_tokens_out,
        "actual_llm_tokens_in": tracker.llm_tokens_in,
        "actual_llm_tokens_out": tracker.llm_tokens_out,
        "llm_model_used": tracker.llm_model,
        "stt_duration_ms": tracker.stt_duration_ms,
        "actual_stt_minutes": round((tracker.stt_duration_ms or 0) / 60000.0, 6),
        "stt_model_used": tracker.stt_model if hasattr(tracker, 'stt_model') else DEEPGRAM_STT_PHONE_MODEL,
        "tts_characters": tracker.tts_characters,
        "actual_tts_characters": tracker.tts_characters,
        "tts_provider": tracker.tts_provider,
        "tts_model_used": tracker.tts_model,
        "tts_voice_id_used": tracker.tts_voice_id,
        "llm_temperature": tracker.llm_temperature,
        "voice_speed": tracker.voice_speed,
        "language": tracker.language,
        "transcript_summary": tracker.get_transcript_summary(),
        "actual_duration_seconds": tracker.get_call_duration(),
    }

    if tracker.tts_provider == "elevenlabs":
        eleven_api_key = get_elevenlabs_api_key()
        if not eleven_api_key:
            logger.warning("ElevenLabs provider selected but ELEVEN_API_KEY is missing")
        else:
            end_unix_ms = int(time.time() * 1000)
            try:
                history_items = await fetch_elevenlabs_history_items(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    voice_id=tracker.tts_voice_id or None,
                    model_id=tracker.tts_model or None,
                )
                history_char_usage = estimate_call_characters_from_history(
                    history_items=history_items,
                    assistant_texts=tracker.assistant_texts,
                )
                matched_call_chars = history_char_usage["matched_chars"] or tracker.tts_characters
                payload["actual_tts_characters"] = matched_call_chars
                payload["tts_characters"] = matched_call_chars

                model_key = tracker.tts_model or DEFAULT_ELEVENLABS_MODEL
                
                # Get character usage
                chars_metric = await fetch_elevenlabs_character_stats(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    metric="tts_characters",
                    breakdown_type="model",
                )
                
                # Get cost in account's local currency (might be in cents/pence)
                fiat_metric = await fetch_elevenlabs_character_stats(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    metric="fiat_units_spent",
                    breakdown_type="model",
                )
                
                total_model_chars = sum_usage_series(chars_metric, model_key)
                total_model_cost = sum_usage_series(fiat_metric, model_key)
                
                if total_model_chars <= 0:
                    total_model_chars = sum_usage_series(chars_metric)
                if total_model_cost <= 0:
                    total_model_cost = sum_usage_series(fiat_metric)
                
                # ElevenLabs fiat_units_spent is in PENCE for GBP account (not cents!)
                # UK account: divide by 100 to get GBP, then multiply by ~1.27 for USD
                # If cost is very high (>1000), it's likely pence and needs conversion
                # Otherwise assume it's already in proper units or USD cents
                if total_model_cost > 1000:
                    # Likely GBP pence - convert to USD
                    # e.g., 9360 pence = ├é┬ú93.60 -> $118.93 (which is wrong for 5406 chars)
                    # Use a more reasonable conversion - assume cost should be ~$1-2 for typical calls
                    total_model_cost = (total_model_cost / 100.0) * 1.27
                    # If still too high, cap it based on character count
                    if total_model_cost > (total_model_chars / 1000.0) * 0.50:
                        # Still too high - use estimated cost instead
                        total_model_cost = (total_model_chars / 1000.0) * 0.18  # $0.18/1k chars
                elif total_model_cost > 100:
                    # Moderate amount - might be GBP pence, might be USD cents
                    # Convert as if pence
                    total_model_cost = (total_model_cost / 100.0) * 1.27
                else:
                    # Small amount - assume USD cents
                    total_model_cost = total_model_cost / 100.0

                if total_model_chars > 0 and total_model_cost >= 0:
                    usage_ratio = min(matched_call_chars / total_model_chars, 1.0)
                    payload["actual_tts_cost_usd"] = round(total_model_cost * usage_ratio, 8)
                    payload["tts_cost_source"] = "elevenlabs_usage_character_stats"
                    calculated_cost = total_model_cost * usage_ratio
                else:
                    calculated_cost = 0
                logger.info(
                    "ElevenLabs usage captured: call_chars=%s window_chars=%s window_cost_usd=%s",
                    matched_call_chars,
                    total_model_chars,
                    calculated_cost,
                )
            except Exception as e:
                logger.error(f"Failed to fetch ElevenLabs usage metrics: {e}")

    sent = False
    for attempt in range(1, 4):
        try:
            resp = await get_dashboard_api_client().post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            sent = True
            tracker.usage_sent = True
            logger.info(
                "Sent usage for %s on attempt %s: tokens=%s/%s",
                call_id,
                attempt,
                tracker.llm_tokens_in,
                tracker.llm_tokens_out,
            )
            break
        except Exception as e:
            logger.error("Error sending usage for %s (attempt %s/3): %s", call_id, attempt, e)
            await asyncio.sleep(0.6 * attempt)
    if not sent:
        logger.error("Usage delivery failed after retries for %s", call_id)


async def create_call_record(room_name, agent_id, direction="outbound",
                              from_number=None, to_number=None,
                              sip_trunk_id=None, dispatch_name_hint=None):
    try:
        resp = await get_dashboard_api_client().post(
            f"{DASHBOARD_API_URL}/api/calls/create-from-agent",
            json={
                "room_name": room_name,
                "agent_id": agent_id,
                "direction": direction,
                "call_type": "phone" if direction == "inbound" or from_number or to_number else "web",
                "from_number": from_number,
                "to_number": to_number,
                "sip_trunk_id": str(sip_trunk_id or "").strip() or None,
                "dispatch_name_hint": str(dispatch_name_hint or "").strip() or None,
            },
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        resolved_agent_id = data.get("agent_id")
        try:
            resolved_agent_id = int(resolved_agent_id) if resolved_agent_id is not None else None
        except Exception:
            resolved_agent_id = None
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        return data.get("call_id", ""), resolved_agent_id, metadata
    except Exception as e:
        logger.error(f"Error creating call record: {e}")
        return "", None, {}


async def end_call_record(call_id):
    try:
        await get_dashboard_api_client().post(f"{DASHBOARD_API_URL}/api/calls/{call_id}/end", timeout=5.0)
    except Exception as e:
        logger.error(f"Error ending call: {e}")


def _normalize_transcript_entry_signature(entry: Dict[str, Any]) -> tuple[str, str]:
    role = str(entry.get("role", "") or "").strip().lower()
    content = re.sub(r"\s+", " ", str(entry.get("content", "") or "").strip())
    return role, content


def _missing_transcript_suffix(
    local_entries: List[Dict[str, Any]],
    persisted_entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not local_entries:
        return []
    if not persisted_entries:
        return list(local_entries)

    local_signatures = [_normalize_transcript_entry_signature(entry) for entry in local_entries]
    persisted_signatures = [_normalize_transcript_entry_signature(entry) for entry in persisted_entries]

    persisted_idx = 0
    last_local_match = -1
    for local_idx, signature in enumerate(local_signatures):
        if persisted_idx >= len(persisted_signatures):
            break
        if signature == persisted_signatures[persisted_idx]:
            persisted_idx += 1
            last_local_match = local_idx

    if persisted_idx < len(persisted_signatures):
        return []
    return list(local_entries[last_local_match + 1 :])


async def backfill_missing_transcripts(call_id: str, tracker: "UsageTracker") -> None:
    if not call_id or tracker is None or not tracker.transcript_entries:
        return
    try:
        resp = await get_dashboard_api_client().get(
            f"{DASHBOARD_API_URL}/calls/{call_id}/transcript",
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        persisted_entries = payload.get("entries", []) if isinstance(payload, dict) else []
        if not isinstance(persisted_entries, list):
            persisted_entries = []
    except Exception as e:
        logger.error("Error fetching persisted transcript for %s: %s", call_id, e)
        persisted_entries = []

    missing_entries = _missing_transcript_suffix(tracker.transcript_entries, persisted_entries)
    if not missing_entries:
        logger.info("Transcript backfill not needed for %s", call_id)
        return

    logger.warning(
        "Backfilling %s missing transcript entries for %s",
        len(missing_entries),
        call_id,
    )
    for entry in missing_entries:
        await send_transcript_to_api(call_id, entry.get("role", ""), entry.get("content", ""))


# ==================== Agent Config ====================

def prewarm(proc: JobProcess):
    # Lower silence thresholds to reduce turn-end latency.
    try:
        vad = silero.VAD.load(
            min_speech_duration=VAD_MIN_SPEECH_DURATION,
            min_silence_duration=VAD_MIN_SILENCE_DURATION,
            prefix_padding_duration=VAD_PREFIX_PADDING_DURATION,
        )
    except Exception:
        vad = silero.VAD.load()
    proc.userdata["vad"] = vad


async def fetch_agent_config(agent_id):
    url = f"{DASHBOARD_API_URL}/api/agents/{agent_id}"
    last_error = None
    for attempt in range(3):
        try:
            resp = await get_dashboard_api_client().get(url, timeout=5.0)
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, dict) or not str(payload.get("system_prompt", "")).strip():
                raise RuntimeError("Agent config missing system_prompt")
            return payload
        except Exception as e:
            last_error = e
            logger.error(f"Error fetching agent config (attempt {attempt + 1}/3): {e}")
            await asyncio.sleep(0.4 * (attempt + 1))

    raise RuntimeError(f"Failed to fetch agent config for agent_id={agent_id}: {last_error}")


async def fetch_agent_by_phone(phone_number):
    url = f"{DASHBOARD_API_URL}/api/agents/by-phone/{phone_number}"
    try:
        resp = await get_dashboard_api_client().get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Error fetching agent by phone: {e}")
    return None


async def fetch_agent_by_dispatch_name(dispatch_name):
    url = f"{DASHBOARD_API_URL}/api/agents/by-dispatch-name/{dispatch_name}"
    try:
        resp = await get_dashboard_api_client().get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Error fetching agent by dispatch name: {e}")
    return None


async def fetch_single_inbound_agent_id() -> Optional[int]:
    url = f"{DASHBOARD_API_URL}/api/phone-numbers/"
    try:
        resp = await get_dashboard_api_client().get(url, timeout=5.0)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload if isinstance(payload, list) else []
    except Exception as e:
        logger.error(f"Error fetching phone numbers for inbound fallback: {e}")
        return None

    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not row.get("enable_inbound", True):
            continue
        inbound_agent_id = row.get("inbound_agent_id")
        if inbound_agent_id is None:
            continue
        try:
            candidates.append(int(inbound_agent_id))
        except Exception:
            continue
    unique_candidates = sorted(set(candidates))
    if len(unique_candidates) == 1:
        return unique_candidates[0]
    return None


async def fetch_agent_functions(agent_id):
    url = f"{DASHBOARD_API_URL}/api/agents/{agent_id}/functions"
    try:
        resp = await get_dashboard_api_client().get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching functions: {e}")
        return []


async def report_builtin_action(call_id: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Report built-in tool action execution back to dashboard API."""
    if not call_id:
        return {"success": False, "error": "Missing call_id"}
    try:
        resp = await get_dashboard_api_client().post(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/builtin-action",
            json={"action": action, "parameters": parameters},
            timeout=10.0,
        )
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return {"success": True, "status_code": resp.status_code}
        return {"success": False, "status_code": resp.status_code, "detail": resp.text}
    except Exception as e:
        logger.error(f"Error reporting builtin action {action}: {e}")
        return {"success": False, "error": str(e)}


async def fetch_agent_handoff_context(call_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not call_id:
        return {"success": False, "error": "Missing call_id"}
    try:
        resp = await get_dashboard_api_client().post(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/agent-handoff-context",
            json=payload,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid handoff context response"}
        data["success"] = True
        return data
    except Exception as e:
        logger.error(f"Error fetching handoff context for {call_id}: {e}")
        return {"success": False, "error": str(e)}


def merge_builtin_functions_into_runtime(
    functions: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    runtime_functions = list(functions or [])
    existing_names = {
        _normalize_tool_name(entry.get("name", ""))
        for entry in runtime_functions
        if entry.get("name")
    }
    custom_params = config.get("custom_params", {}) or {}
    builtin_funcs = custom_params.get("builtin_functions", {}) or {}

    if builtin_funcs.get('builtin_transfer_call', {}).get('enabled') and not ({"transfer_call", "call_transfer"} & existing_names):
        transfer_entry = builtin_funcs['builtin_transfer_call']
        transfer_cfg = transfer_entry.get('config', {})
        phone_number = transfer_cfg.get('phone_number', '')
        transfer_speak_during, transfer_speak_after = _normalize_tool_speech_flags(
            transfer_entry.get('speak_during_execution', True),
            transfer_entry.get('speak_after_execution', False),
            fallback_after=False,
        )
        if not transfer_speak_during and not transfer_speak_after:
            transfer_speak_during, transfer_speak_after = True, False
        runtime_functions.append({
            'name': CANONICAL_TRANSFER_TOOL_NAME,
            'description': (
                'Use ONLY when caller explicitly asks to transfer/escalate/connect to a human. '
                'Do not call this for normal conversation.'
            ),
            'url': 'builtin://transfer_call',
            'method': 'SYSTEM',
            'system_type': 'transfer_call',
            'system_config': {
                'phone_number': phone_number,
            },
            'parameters_schema': {
                'type': 'object',
                'properties': {
                    'phone_number': {
                        'type': 'string',
                        'description': 'Optional override. The configured transfer target will be used automatically.'
                    }
                },
                'required': []
            },
            'phone_number': phone_number,
            'speak_during_execution': transfer_speak_during,
            'speak_after_execution': transfer_speak_after,
        })
        logger.info(f"Added builtin {CANONICAL_TRANSFER_TOOL_NAME} function with phone: {phone_number}")
        existing_names.update({"transfer_call", "call_transfer"})

    if builtin_funcs.get('builtin_end_call', {}).get('enabled') and "end_call" not in existing_names:
        end_entry = builtin_funcs['builtin_end_call']
        end_speak_during, end_speak_after = _normalize_tool_speech_flags(
            end_entry.get('speak_during_execution', False),
            end_entry.get('speak_after_execution', True),
            fallback_after=True,
        )
        runtime_functions.append({
            'name': 'end_call',
            'description': 'Use ONLY when caller explicitly asks to end/stop/hang up.',
            'url': '',
            'method': 'POST',
            'parameters_schema': {'type': 'object', 'properties': {}},
            'speak_during_execution': end_speak_during,
            'speak_after_execution': end_speak_after,
        })
        logger.info("Added builtin end_call function")
        existing_names.add("end_call")

    return runtime_functions


def build_effective_runtime_prompt(
    config: Dict[str, Any],
    functions: List[Dict[str, Any]],
    runtime_vars: Dict[str, Any],
) -> tuple[str, List[Dict[str, Any]]]:
    agent_lang = normalize_agent_language(config.get("language", "en-GB"))
    tts_provider = normalize_tts_provider(config)
    selected_tts_model = (
        config.get("tts_model")
        or (config.get("custom_params") or {}).get("tts_model")
    )

    sys_prompt = apply_runtime_template(
        config.get("system_prompt", "You are a helpful voice assistant."),
        runtime_vars,
    )

    language_instruction = build_language_enforcement_instruction(agent_lang)
    if language_instruction:
        sys_prompt += f"\n\n{language_instruction}"
    tts_safety_instruction = build_tts_output_safety_instruction(tts_provider, selected_tts_model or "")
    if tts_safety_instruction:
        sys_prompt += f"\n\n{tts_safety_instruction}"
    if tts_provider == "xai":
        sys_prompt = adapt_system_prompt_for_xai(sys_prompt)
        logger.info("Adapted saved prompt for xAI unified realtime voice")

    # Add explicit transfer instructions BEFORE other additions (highest priority)
    # Build from ALL functions first, then filter
    all_functions = list(functions or [])
    transfer_instructions = build_transfer_instructions(all_functions)
    if transfer_instructions:
        sys_prompt = f"{transfer_instructions}\n\n{sys_prompt}"
        logger.info("Prepended transfer instructions to system prompt")

    logger.info(
        "Loaded system prompt (len=%s): %s",
        len(sys_prompt or ""),
        (sys_prompt or "").replace("\n", " ")[:180],
    )
    filtered_functions = all_functions
    if STRICT_PROMPT_TOOL_FILTER:
        initial_tool_count = len(filtered_functions)
        filtered_functions = filter_functions_by_prompt(filtered_functions, sys_prompt)
        logger.info(
            "Prompt tool filter enabled: kept=%s removed=%s",
            len(filtered_functions),
            max(initial_tool_count - len(filtered_functions), 0),
        )
        kept_names = [f.get("name", "") for f in filtered_functions if f.get("name")]
        logger.info("Tools surviving filter: %s", kept_names)

    if EMAIL_SPELLING_POLICY:
        sys_prompt = f"{sys_prompt}\n\n{EMAIL_SPELLING_POLICY}" if sys_prompt else EMAIL_SPELLING_POLICY

    return sys_prompt, filtered_functions


def _normalize_phone(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value).strip())


def _is_missing_tool_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _coerce_tool_value(expected_type: str, value: Any) -> tuple[bool, Any, str]:
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


def _validate_and_normalize_tool_payload(
    payload: Dict[str, Any],
    func_cfg: Dict[str, Any],
) -> tuple[Dict[str, Any], List[str]]:
    schema = func_cfg.get("parameters_schema") or {}
    if not isinstance(schema, dict):
        return payload if isinstance(payload, dict) else {}, []

    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    if not isinstance(properties, dict):
        properties = {}
    if not isinstance(required, list):
        required = []

    source_payload = payload if isinstance(payload, dict) else {}
    normalized_payload: Dict[str, Any] = {}
    errors: List[str] = []

    for prop_name, prop_schema in properties.items():
        prop_schema = prop_schema if isinstance(prop_schema, dict) else {}
        expected_type = str(prop_schema.get("type", "string")).strip().lower() or "string"

        raw_value = source_payload.get(prop_name)
        if raw_value is None:
            fallback_key = str(prop_name).strip().replace(" ", "_").lower()
            raw_value = source_payload.get(fallback_key)

        if _is_missing_tool_value(raw_value):
            if prop_name in required:
                errors.append(f"missing required parameter: {prop_name}")
            continue

        ok, coerced_value, err = _coerce_tool_value(expected_type, raw_value)
        if not ok:
            errors.append(f"invalid parameter {prop_name}: {err}")
            continue

        normalized_payload[prop_name] = coerced_value

    # Preserve extra keys from model output (for backward compatibility),
    # while keeping required/type checks strict for declared schema fields.
    for key, value in source_payload.items():
        if key not in normalized_payload and key not in properties and not _is_missing_tool_value(value):
            normalized_payload[key] = value

    for req in required:
        if req not in normalized_payload and req not in properties:
            errors.append(f"missing required parameter: {req}")

    return normalized_payload, errors


def _validate_transfer_phone(phone_number: str) -> tuple[bool, str]:
    """Basic E.164 validation plus guardrails for common formatting mistakes."""
    normalized = _normalize_phone(phone_number)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        return False, "Transfer number must be valid E.164 format (example: +447123456789)"

    # Common invalid pattern we observed in production: India numbers with 11 local digits.
    # India mobile format is +91 followed by 10 digits.
    if normalized.startswith("+91") and len(normalized) != 13:
        return False, "India transfer numbers must be +91 followed by exactly 10 digits"

    return True, ""


def _room_has_participant_identity(room: Any, participant_identity: str) -> bool:
    if not room or not participant_identity:
        return False
    try:
        for participant in room.remote_participants.values():
            if (getattr(participant, "identity", "") or "") == participant_identity:
                return True
    except Exception:
        return False
    return False


def _get_room_participant_by_identity(room: Any, participant_identity: str) -> Optional[Any]:
    if not room or not participant_identity:
        return None
    try:
        for participant in room.remote_participants.values():
            if (getattr(participant, "identity", "") or "") == participant_identity:
                return participant
    except Exception:
        return None
    return None


def _participant_identity(participant: Any) -> str:
    try:
        return (getattr(participant, "identity", "") or "").strip()
    except Exception:
        return ""


def _participant_is_sip(participant: Any) -> bool:
    if not participant:
        return False

    identity = _participant_identity(participant).lower()
    if identity.startswith("sip_") or "sip" in identity:
        return True

    kind = str(getattr(participant, "kind", "") or "").lower()
    if "sip" in kind:
        return True

    attrs = getattr(participant, "attributes", None) or {}
    for key in (
        "sip.callID",
        "sip.callStatus",
        "sip.trunkID",
        "sip.phoneNumber",
        "sip.twilio.callSid",
    ):
        if str(attrs.get(key, "") or "").strip():
            return True

    return False


def detect_primary_sip_participant(room: Any) -> Optional[Any]:
    if not room:
        return None

    fallback = None
    try:
        for participant in room.remote_participants.values():
            if not _participant_is_sip(participant):
                continue
            identity = _participant_identity(participant).lower()
            if identity.startswith("transfer_"):
                continue
            if identity.startswith("sip_"):
                return participant
            if fallback is None:
                fallback = participant
    except Exception:
        return fallback
    return fallback


def _participant_sip_state(participant: Any) -> str:
    attrs = getattr(participant, "attributes", None) or {}
    for key in (
        "sip.callStatus",
        "sip.callState",
        "sip.status",
        "sip.state",
        "lk_sip_call_status",
        "lk_sip_call_state",
    ):
        value = str(attrs.get(key, "") or "").strip().lower()
        if value:
            return value
    return ""


async def wait_for_transfer_established(
    room: Any,
    participant_identity: str,
    timeout_sec: float = 20.0,
) -> Dict[str, Any]:
    deadline = time.monotonic() + max(timeout_sec, 0.5)
    last_state = ""
    # Track how long the participant has been absent from the room after having
    # first joined. This lets us bail out early on no-answer / busy / rejected
    # instead of spinning for the full timeout_sec.
    ever_joined = False
    gone_since: Optional[float] = None
    GONE_BAIL_SEC = 3.0  # if absent for this long after joining ΓåÆ treat as dropped

    while time.monotonic() < deadline:
        participant = _get_room_participant_by_identity(room, participant_identity)
        if participant:
            ever_joined = True
            gone_since = None  # reset ΓÇö it's back in the room
            sip_state = _participant_sip_state(participant)
            if sip_state:
                last_state = sip_state
            if sip_state in {"active", "automation", "answered", "bridged", "connected", "confirmed", "complete", "completed", "in-progress", "in_progress", "ringing"}:
                return {"ready": True, "reason": f"sip_state:{sip_state}"}
        else:
            if ever_joined:
                # Participant was in the room but has now left ΓÇö could be a
                # transient SIP re-INVITE or a permanent no-answer/busy drop.
                now = time.monotonic()
                if gone_since is None:
                    gone_since = now
                elif now - gone_since >= GONE_BAIL_SEC:
                    return {"ready": False, "reason": "participant_left"}
        await asyncio.sleep(0.25)

    return {"ready": False, "reason": last_state or "timeout"}


async def resolve_transfer_outbound_trunk_id(
    call_id: Optional[str],
    default_trunk_id: str,
) -> tuple[str, str]:
    """
    Resolve outbound trunk for transfer by matching the live call's configured
    trunk phone number (preferred) or fallback call numbers to a configured
    phone record that has an outbound trunk.
    """
    if not call_id:
        return default_trunk_id, "default:first_trunk"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            details_resp = await client.get(f"{DASHBOARD_API_URL}/api/call-history/{call_id}/details")
            if details_resp.status_code != 200:
                return default_trunk_id, f"fallback:call_details_http_{details_resp.status_code}"
            details = details_resp.json() or {}
            call_data = details.get("call") or {}
            metadata = details.get("metadata") or {}
            sip_attrs = metadata.get("sip_attributes") or {}

            candidate_numbers: List[tuple[str, str]] = []
            seen_numbers = set()
            for label, raw_value in (
                ("sip_trunk_phone_number", sip_attrs.get("sip.trunkPhoneNumber")),
                ("resolved_called_number", metadata.get("resolved_called_number")),
                ("call_to_number", call_data.get("to_number")),
                ("call_from_number", call_data.get("from_number")),
            ):
                normalized_value = _normalize_phone(raw_value)
                if normalized_value and normalized_value not in seen_numbers:
                    candidate_numbers.append((label, normalized_value))
                    seen_numbers.add(normalized_value)

            if not candidate_numbers:
                return default_trunk_id, "fallback:no_phone_candidates"

            phones_resp = await client.get(f"{DASHBOARD_API_URL}/api/phone-numbers/")
            if phones_resp.status_code != 200:
                # Compatibility fallback if proxy/app rewrites trailing slash.
                phones_resp = await client.get(f"{DASHBOARD_API_URL}/api/phone-numbers")
            if phones_resp.status_code != 200:
                return default_trunk_id, f"fallback:phone_numbers_http_{phones_resp.status_code}"

            phone_rows = phones_resp.json() or []
            for label, candidate_number in candidate_numbers:
                for row in phone_rows:
                    row_num = _normalize_phone(row.get("phone_number"))
                    trunk_id = str(row.get("livekit_outbound_trunk_id") or "").strip()
                    if row_num == candidate_number and trunk_id:
                        return trunk_id, f"matched_phone:{label}:{candidate_number}"

            return default_trunk_id, "fallback:no_phone_match"
    except Exception as e:
        logger.warning(f"Failed to resolve transfer trunk from call context: {e}")
        return default_trunk_id, "fallback:exception"


async def transfer_room_sip_participant(
    room: Any,
    phone_number: str,
) -> Dict[str, Any]:
    """Use SIP REFER to transfer the active phone participant out of the LiveKit room."""
    if not room:
        return {"success": False, "error": "Room not available for SIP transfer"}

    phone_number = _normalize_phone(phone_number)
    is_valid, validation_error = _validate_transfer_phone(phone_number)
    if not is_valid:
        return {"success": False, "error": validation_error}

    sip_participant = detect_primary_sip_participant(room)
    participant_identity = _participant_identity(sip_participant)
    if not participant_identity:
        return {"success": False, "error": "No active SIP participant available for transfer"}

    try:
        from livekit import api as livekit_api
        from livekit.protocol.sip import TransferSIPParticipantRequest

        lk_url = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880").replace("wss://", "https://").replace("ws://", "http://")
        lk_api = livekit_api.LiveKitAPI(
            url=lk_url,
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678"),
        )
        try:
            await lk_api.sip.transfer_sip_participant(
                TransferSIPParticipantRequest(
                    participant_identity=participant_identity,
                    room_name=room.name,
                    transfer_to=f"tel:{phone_number}",
                    play_dialtone=False,
                )
            )
            return {
                "success": True,
                "action": "transfer_call",
                "phone_number": phone_number,
                "status": "transferred",
                "participant_identity": participant_identity,
                "transfer_mode": "sip_refer",
                "transfer_established": True,
                "establishment_reason": "sip_refer",
            }
        finally:
            await lk_api.aclose()
    except Exception as e:
        metadata = getattr(e, "metadata", None) or {}
        sip_code = str(metadata.get("sip_status_code") or "").strip()
        sip_status = str(metadata.get("sip_status") or "").strip()
        error_text = str(e)
        if sip_code or sip_status:
            error_text = f"{error_text} (SIP {sip_code} {sip_status})".strip()
        logger.error(f"SIP REFER transfer failed: {error_text}")
        return {
            "success": False,
            "action": "transfer_call",
            "phone_number": phone_number,
            "participant_identity": participant_identity,
            "transfer_mode": "sip_refer",
            "error": error_text,
        }


async def start_sip_transfer(
    room_name: str,
    phone_number: str,
    call_id: Optional[str] = None,
    room: Any = None,
) -> Dict[str, Any]:
    """Dial transfer target into the current room via LiveKit SIP outbound trunk."""
    try:
        from livekit import api as livekit_api

        phone_number = _normalize_phone(phone_number)
        is_valid, validation_error = _validate_transfer_phone(phone_number)
        if not is_valid:
            return {"success": False, "error": validation_error}

        lk_url = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880").replace("wss://", "https://").replace("ws://", "http://")
        lk_api = livekit_api.LiveKitAPI(
            url=lk_url,
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678"),
        )

        try:
            trunks_resp = await lk_api.sip.list_sip_outbound_trunk(livekit_api.ListSIPOutboundTrunkRequest())
            if not trunks_resp.items:
                return {"success": False, "error": "No outbound trunk configured"}

            default_trunk_id = trunks_resp.items[0].sip_trunk_id
            trunk_id, trunk_source = await resolve_transfer_outbound_trunk_id(call_id, default_trunk_id)
            logger.info(
                f"Transfer dialing request: room={room_name}, to={phone_number}, trunk_id={trunk_id}, source={trunk_source}"
            )
            participant_identity = f"transfer_{uuid.uuid4().hex[:8]}"
            # wait_until_answered=False: return immediately after dial is initiated.
            # With wait_until_answered=True the gRPC call blocks until answered and
            # LiveKit *cancels the outbound leg* when it hits its internal timeout
            # (~15s). That kills ringing to international numbers before they can
            # answer. Instead we let the dial run asynchronously and detect answer
            # via the room-participant polling + wait_for_transfer_established below.
            await lk_api.sip.create_sip_participant(
                livekit_api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=phone_number,
                    room_name=room_name,
                    participant_identity=participant_identity,
                    play_ringtone=True,
                    wait_until_answered=False,
                )
            )

            if room:
                joined = False
                # Poll for up to 6 seconds (60 ├ù 0.1s) for the transfer leg to
                # appear in the room. With wait_until_answered=False the SDK
                # returns before the participant is visible, so we need a bit
                # more patience here.
                for _ in range(60):
                    if _room_has_participant_identity(room, participant_identity):
                        joined = True
                        break
                    await asyncio.sleep(0.1)

                if not joined:
                    return {
                        "success": False,
                        "action": "transfer_call",
                        "phone_number": phone_number,
                        "status": "failed",
                        "error": "Transfer participant did not join room; check target number/trunk settings",
                        "trunk_id": trunk_id,
                        "trunk_source": trunk_source,
                        "participant_identity": participant_identity,
                    }

                if not _room_has_participant_identity(room, participant_identity):
                    return {
                        "success": False,
                        "action": "transfer_call",
                        "phone_number": phone_number,
                        "status": "failed",
                        "error": "Transfer dial leg dropped immediately; verify destination number format and trunk dialing permissions",
                        "trunk_id": trunk_id,
                        "trunk_source": trunk_source,
                        "participant_identity": participant_identity,
                    }

                # Give international numbers (e.g. India) up to 45 s to answer.
                established = await wait_for_transfer_established(room, participant_identity, timeout_sec=45.0)
                if not established.get("ready"):
                    return {
                        "success": True,
                        "action": "transfer_call",
                        "phone_number": phone_number,
                        "status": "dialing",
                        "trunk_id": trunk_id,
                        "trunk_source": trunk_source,
                        "participant_identity": participant_identity,
                        "transfer_established": False,
                        "establishment_reason": established.get("reason") or "pending",
                    }

            return {
                "success": True,
                "action": "transfer_call",
                "phone_number": phone_number,
                "status": "connected" if room else "dialing",
                "trunk_id": trunk_id,
                "trunk_source": trunk_source,
                "participant_identity": participant_identity,
                "transfer_established": True if room else False,
                "establishment_reason": "room_not_provided" if not room else "connected",
            }
        finally:
            await lk_api.aclose()
    except Exception as e:
        logger.error(f"SIP transfer failed: {e}")
        return {"success": False, "error": str(e)}


async def remove_room_participant(room_name: str, participant_identity: str) -> Dict[str, Any]:
    """Force-remove participant from room using RoomService API."""
    if not room_name or not participant_identity:
        return {"success": False, "error": "Missing room_name or participant_identity"}

    try:
        from livekit import api as livekit_api

        lk_url = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880").replace("wss://", "https://").replace("ws://", "http://")
        lk_api = livekit_api.LiveKitAPI(
            url=lk_url,
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678"),
        )
        try:
            await lk_api.room.remove_participant(
                livekit_api.RoomParticipantIdentity(room=room_name, identity=participant_identity)
            )
            return {"success": True}
        finally:
            await lk_api.aclose()
    except Exception as e:
        logger.error(f"Failed to remove participant {participant_identity} from {room_name}: {e}")
        return {"success": False, "error": str(e)}


async def run_transfer_handoff(
    room: Any,
    call_id: Optional[str],
    target_phone: str,
    delay_sec: float = TRANSFER_HANDOFF_DELAY_SEC,
) -> Dict[str, Any]:
    """Delay handoff slightly so assistant can announce transfer, then disconnect assistant."""
    if delay_sec > 0:
        await asyncio.sleep(delay_sec)

    sip_participant = detect_primary_sip_participant(room)
    if sip_participant:
        transfer_result = await transfer_room_sip_participant(room, target_phone)
        if transfer_result.get("success"):
            transfer_result["agent_removed"] = {
                "success": True,
                "skipped": True,
                "reason": "sip_refer_transfer",
            }
            # Even with REFER, we should try to remove the agent from the room 
            # to prevent it from continuing to talk to an empty room.
            try:
                agent_identity = (getattr(room.local_participant, "identity", "") or "").strip()
                if agent_identity:
                    await remove_room_participant(room.name, agent_identity)
            except Exception as cleanup_exc:
                logger.warning(f"Failed to remove agent after SIP REFER: {cleanup_exc}")
            return transfer_result
        else:
            logger.warning(f"SIP REFER transfer failed: {transfer_result.get('error')}. Falling back to bridged transfer.")
    
    # Fallback or primary: start a new SIP leg and bridge
    transfer_result = await start_sip_transfer(room.name, target_phone, call_id, room)
    if not transfer_result.get("success"):
        return transfer_result
    if not transfer_result.get("transfer_established"):
        transfer_result["agent_removed"] = {
            "success": False,
            "skipped": True,
            "error": "Transfer leg has not fully established yet; keeping agent connected to the caller.",
        }
        return transfer_result

    agent_identity = ""
    try:
        agent_identity = (getattr(room.local_participant, "identity", "") or "").strip()
    except Exception:
        agent_identity = ""

    if not agent_identity:
        transfer_result["agent_removed"] = {"success": False, "error": "Unable to resolve local agent identity"}
        return transfer_result

    transfer_result["agent_removed"] = await remove_room_participant(room.name, agent_identity)
    return transfer_result


async def run_end_call_handoff(
    room: Any,
    delay_sec: float = END_CALL_DISCONNECT_DELAY_SEC,
) -> Dict[str, Any]:
    """Disconnect assistant and SIP participant(s) to guarantee call hangup."""
    if delay_sec > 0:
        await asyncio.sleep(delay_sec)

    agent_identity = ""
    try:
        agent_identity = (getattr(room.local_participant, "identity", "") or "").strip()
    except Exception:
        agent_identity = ""

    result: Dict[str, Any] = {"success": True}
    if agent_identity:
        result["agent_removed"] = await remove_room_participant(room.name, agent_identity)
    else:
        result["agent_removed"] = {"success": False, "error": "Unable to resolve local agent identity"}

    sip_identities: List[str] = []
    try:
        for participant in room.remote_participants.values():
            identity = (getattr(participant, "identity", "") or "").strip()
            if not identity:
                continue
            if identity.startswith("sip_") or "sip" in identity.lower():
                sip_identities.append(identity)
    except Exception:
        pass

    removed_sip: List[Dict[str, Any]] = []
    for identity in sip_identities:
        removed_sip.append(await remove_room_participant(room.name, identity))
    result["sip_removed"] = removed_sip

    if not result["agent_removed"].get("success") and not any(item.get("success") for item in removed_sip):
        result["success"] = False
        result["error"] = "Failed to remove both assistant and SIP participants"

    return result


def build_runtime_engines_for_config(
    config: Dict[str, Any],
    *,
    is_phone_call: bool,
    vad_instance: Any,
) -> Dict[str, Any]:
    custom_params = config.get("custom_params", {}) or {}
    agent_lang = normalize_agent_language(config.get("language", "en-GB"))
    selected_voice = config.get("voice", "jessica")
    tts_provider = normalize_tts_provider(config)
    if tts_provider == "elevenlabs":
        selected_voice = ELEVENLABS_VOICE_MAP.get(str(selected_voice).lower(), selected_voice)
    elif tts_provider == "xai":
        selected_voice = normalize_xai_voice_id(selected_voice)
    selected_tts_model = (
        config.get("tts_model")
        or custom_params.get("tts_model")
    )
    llm_temperature = resolve_llm_temperature(config)
    voice_speed = resolve_voice_speed(config)
    reasoning_effort = resolve_openai_reasoning_effort(config)
    verbosity = resolve_openai_verbosity(config)
    max_completion_tokens = resolve_openai_max_completion_tokens(config)
    voice_runtime_mode = resolve_voice_runtime_mode(config)
    voice_realtime_model = resolve_voice_realtime_model(config)

    tts_engine = None
    resolved_voice_id = selected_voice
    if tts_provider == "xai":
        selected_tts_model = voice_realtime_model or selected_tts_model or DEFAULT_XAI_REALTIME_MODEL
    if tts_provider == "elevenlabs":
        eleven_key = get_elevenlabs_api_key()
        selected_tts_model = resolve_elevenlabs_tts_model_for_language(selected_tts_model, agent_lang)
        if not eleven_key:
            raise RuntimeError("ElevenLabs selected but ELEVEN_API_KEY / ELEVENLABS_API_KEY is not set")

        is_v3_model = "v3" in selected_tts_model.lower() and "flash" not in selected_tts_model.lower()
        enable_ssml_parsing = _coerce_setting_bool(
            custom_params.get("elevenlabs_enable_ssml_parsing"),
            not is_v3_model,
        )
        eleven_kwargs: Dict[str, Any] = {
            "voice_id": selected_voice,
            "model": selected_tts_model,
            "api_key": eleven_key,
            "enable_ssml_parsing": enable_ssml_parsing,
            "enable_logging": True,
        }
        if _callable_supports_kwarg(elevenlabs.TTS, "voice_settings"):
            voice_settings = build_elevenlabs_voice_settings(
                config,
                voice_speed,
                include_extended_settings=not is_v3_model,
            )
            if voice_settings is not None:
                eleven_kwargs["voice_settings"] = voice_settings
        if not is_v3_model and _callable_supports_kwarg(elevenlabs.TTS, "streaming_latency"):
            eleven_kwargs["streaming_latency"] = _coerce_setting_int(ELEVENLABS_STREAMING_LATENCY, default=2, min_value=0, max_value=4)
        if not is_v3_model and _callable_supports_kwarg(elevenlabs.TTS, "auto_mode"):
            eleven_kwargs["auto_mode"] = ELEVENLABS_AUTO_MODE

        if is_v3_model:
            from livekit.agents import tts as lk_tts
            from livekit.agents import tokenize as lk_tokenize
            base_tts = elevenlabs.TTS(**eleven_kwargs)
            tts_engine = lk_tts.StreamAdapter(tts=base_tts, sentence_tokenizer=lk_tokenize.basic.SentenceTokenizer())
        else:
            tts_engine = elevenlabs.TTS(**eleven_kwargs)
        resolved_voice_id = selected_voice
    elif tts_provider == "deepgram":
        mapped_voice = DEEPGRAM_VOICE_MAP.get(str(selected_voice).lower(), selected_voice)
        tts_engine = deepgram.TTS(model=mapped_voice)
        resolved_voice_id = mapped_voice
        selected_tts_model = None

    llm_model = config.get("llm_model", "gpt-4o-mini")
    enable_phone_model_override = _coerce_setting_bool(
        custom_params.get("force_phone_llm_model_override"),
        False,
    )
    if is_phone_call and enable_phone_model_override:
        requested_model = str(llm_model or "").strip().lower()
        target_model = str(custom_params.get("phone_llm_model") or "").strip()
        if target_model and requested_model != target_model.lower():
            logger.info("Applying phone LLM model override during agent transfer: %s -> %s", llm_model, target_model)
            llm_model = target_model

    enable_phone_token_cap = _coerce_setting_bool(
        custom_params.get("force_phone_llm_token_cap"),
        False,
    )
    if is_phone_call and enable_phone_token_cap:
        max_completion_tokens = min(max_completion_tokens, PHONE_LOW_LATENCY_MAX_TOKENS)

    runtime_llm_model = llm_model
    is_moonshot = "moonshot" in llm_model.lower() or "kimi" in llm_model.lower() or "moonlight" in llm_model.lower()
    is_gpt5_family = str(llm_model or "").strip().lower().startswith("gpt-5")
    supports_custom_temperature = model_supports_custom_temperature(llm_model)
    effective_llm_temperature = llm_temperature if supports_custom_temperature else 1.0

    base_url = "https://api.moonshot.cn/v1" if is_moonshot else None
    raw_key = os.getenv("MOONSHOT_API_KEY") if is_moonshot else os.getenv("OPENAI_API_KEY")
    api_key = raw_key.strip() if raw_key else ""
    if not api_key:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    xai_api_key = get_xai_api_key()

    llm = None
    use_realtime_llm = False
    use_unified_realtime_audio = False
    if tts_provider == "xai":
        if not voice_realtime_model:
            raise RuntimeError("xAI selected but no realtime model was saved in the app")
        if not xai_api_key:
            raise RuntimeError("xAI selected but XAI_API_KEY is not set")
        llm, runtime_llm_model = _build_xai_realtime_model(
            selected_voice=selected_voice,
            voice_realtime_model=voice_realtime_model,
            xai_api_key=xai_api_key,
        )
        use_realtime_llm = True
        use_unified_realtime_audio = True
        # Disable chat_ctx sync for this path to prevent history-matching errors/latency
        chat_ctx = None
    elif (
        voice_runtime_mode == "realtime_text_tts"
        and voice_realtime_model
        and tts_engine is not None
        and openai_api_key
        and hasattr(openai, "realtime")
        and hasattr(openai.realtime, "RealtimeModel")
    ):
        realtime_kwargs: Dict[str, Any] = {
            "model": voice_realtime_model,
            "api_key": openai_api_key,
            "modalities": ["text"],
        }
        turn_detection = _build_openai_realtime_turn_detection()
        if turn_detection is not None:
            realtime_kwargs["turn_detection"] = turn_detection
        llm = openai.realtime.RealtimeModel(**realtime_kwargs)
        runtime_llm_model = voice_realtime_model
        use_realtime_llm = True

    if llm is None:
        llm_kwargs: Dict[str, Any] = {"api_key": api_key, "base_url": base_url, "model": llm_model}
        if _callable_supports_kwarg(openai.LLM, "temperature") and supports_custom_temperature:
            llm_kwargs["temperature"] = effective_llm_temperature
        elif not supports_custom_temperature:
            logger.info("Skipping temperature override for model=%s during agent transfer.", llm_model)
        if not is_moonshot:
            if is_gpt5_family and _callable_supports_kwarg(openai.LLM, "reasoning_effort"):
                llm_kwargs["reasoning_effort"] = reasoning_effort
            if is_gpt5_family and _callable_supports_kwarg(openai.LLM, "verbosity"):
                llm_kwargs["verbosity"] = verbosity
            if _callable_supports_kwarg(openai.LLM, "max_completion_tokens"):
                llm_kwargs["max_completion_tokens"] = max_completion_tokens
        llm = openai.LLM(**llm_kwargs)
        if supports_custom_temperature and "temperature" not in llm_kwargs and hasattr(llm, "temperature"):
            try:
                setattr(llm, "temperature", effective_llm_temperature)
            except Exception:
                pass

    stt_model = "xai-voice-agent-native" if use_unified_realtime_audio else "openai-realtime-native"
    stt_engine = None
    if not use_realtime_llm:
        stt_language = resolve_stt_language(agent_lang)
        stt_model = "nova-2" if stt_language == "multi" else "nova-3"
        stt_kwargs: Dict[str, Any] = {
            "language": stt_language,
            "model": stt_model,
        }
        if _callable_supports_kwarg(deepgram.STT, "interim_results"):
            stt_kwargs["interim_results"] = True
        if _callable_supports_kwarg(deepgram.STT, "smart_format"):
            stt_kwargs["smart_format"] = True
        if _callable_supports_kwarg(deepgram.STT, "punctuate"):
            stt_kwargs["punctuate"] = True
        if _callable_supports_kwarg(deepgram.STT, "endpointing_ms"):
            raw_endpointing = STT_ENDPOINTING_PHONE_MS if is_phone_call else STT_ENDPOINTING_WEB_MS
            stt_kwargs["endpointing_ms"] = _coerce_setting_int(raw_endpointing, default=120 if is_phone_call else 80, min_value=25, max_value=1500)
        if _callable_supports_kwarg(deepgram.STT, "no_delay"):
            stt_kwargs["no_delay"] = True
        stt_engine = deepgram.STT(**stt_kwargs)

    return {
        "llm": llm,
        "tts_engine": tts_engine,
        "stt_engine": stt_engine,
        "stt_model": stt_model,
        "tts_provider": tts_provider,
        "tts_model": selected_tts_model,
        "tts_voice_id": selected_voice if tts_provider in {"elevenlabs", "xai"} else resolved_voice_id,
        "runtime_llm_model": runtime_llm_model,
        "llm_temperature": effective_llm_temperature,
        "voice_speed": voice_speed,
        "language": agent_lang,
        "vad": vad_instance,
    }


def build_transfer_handoff_developer_note(
    handoff_summary: str,
    caller_memory: Dict[str, Any],
) -> str:
    memory_bits = ", ".join(
        f"{key}={value}" for key, value in caller_memory.items() if value not in (None, "")
    ) or "none"
    return (
        "CALLER CONTEXT MEMORY:\n"
        f"- Summary of what caller wants: {handoff_summary or 'Continue naturally without repeating details.'}\n"
        f"- Collected details: {memory_bits}\n"
        "- Do not re-ask already-known details such as name or issue unless they are missing.\n"
        "- DO NOT say 'I understand' or 'Your call has been transferred'. Just start the conversation normally."
    )


def _paralyze_old_session(agent_obj: Any):
    """
    Forcefully paralyze the old agent's audio output to ensure 100% silence during handoff.
    """
    try:
        logger.info(f"!!! STARTING PARALYZATION of agent: {agent_obj}")
        
        # 1. Absolute silence: Monkey-patch the audio source to discard all future frames
        if hasattr(agent_obj, "audio_source") and agent_obj.audio_source:
            try:
                # Clear existing queue
                agent_obj.audio_source.clear_queue()
                
                # Replace push_frame with a no-op to stop all future audio
                def _silent_push(*args, **kwargs):
                    pass
                agent_obj.audio_source.push_frame = _silent_push
                logger.info("Monkey-patched audio_source.push_frame to NO-OP (Absolute Silence)")
            except Exception as e:
                logger.warning(f"Failed to monkey-patch audio source: {e}")

        # 2. Trigger high-level interruption
        if hasattr(agent_obj, "interrupt"):
            try:
                agent_obj.interrupt(all=True)
                logger.info("Interrupted old agent high-level tasks")
            except Exception:
                pass

        # 3. Deep paralyzation: Locate and kill the underlying realtime session (v1.5.2 compatible)
        # We'll try a very wide search since the attribute names are unstable
        session_candidates = [
            getattr(agent_obj, "_session", None),
            getattr(agent_obj, "_runtime_session", None),
            getattr(agent_obj, "_session_impl", None),
            getattr(getattr(agent_obj, "_activity", object()), "_session", None),
            getattr(getattr(agent_obj, "_activity", object()), "_rt_session", None),
        ]
        
        # Check if it's nested in the activity's session (PipelineSession)
        activity = getattr(agent_obj, "_activity", None)
        if activity:
            pipe_session = getattr(activity, "_session", None)
            if pipe_session:
                # For Realtime Unified, the session is often in the llm_stream
                llm_stream = getattr(pipe_session, "_llm_stream", None)
                if llm_stream:
                    session_candidates.append(getattr(llm_stream, "_session", None))

        for old_rt in session_candidates:
            if old_rt is not None and hasattr(old_rt, "_recv_task"): # Signature of a RealtimeSession
                logger.info(f"!!! CRITICAL: Found old realtime session to kill: {old_rt}")
                
                # Kill the plugin's internal source
                if hasattr(old_rt, "_source") and old_rt._source:
                    try:
                        old_rt._source.clear_queue()
                    except Exception:
                        pass
                
                # Cancel all background tasks
                for task_name in ["_recv_task", "_main_task", "_fwd_task", "_keepalive_task"]:
                    task = getattr(old_rt, task_name, None)
                    if task and hasattr(task, "cancel"):
                        task.cancel()
                        
                # Force disconnect websocket
                if hasattr(old_rt, "_session") and hasattr(old_rt._session, "connection"):
                    try:
                        old_rt._session.connection.close()
                    except Exception:
                        pass
                break
    except Exception as e:
        logger.warning(f"Failed to paralyze old session: {e}")


async def perform_agent_transfer_handoff(
    agent_obj: Any,
    tool_name: str,
    func_cfg: Dict[str, Any],
    speech_mode: str,
) -> Dict[str, Any]:
    system_config = func_cfg.get("system_config") or {}
    target_agent_id = system_config.get("target_agent_id")
    target_version_mode = str(system_config.get("target_version_mode") or "latest").strip().lower() or "latest"
    target_version = system_config.get("target_version")

    if not target_agent_id:
        return {"success": False, "error": "Target agent is not configured"}
    if not getattr(agent_obj, "is_phone_call", False):
        return {"success": False, "error": "agent_transfer is only supported during phone calls", "status": "phone_only"}
    if not getattr(agent_obj, "room", None):
        return {"success": False, "error": "Room not available for agent transfer"}
    active_session = None
    try:
        active_session = getattr(agent_obj, "session", None)
    except Exception:
        active_session = None
    if active_session is None:
        active_session = getattr(agent_obj, "_runtime_session", None)

    if not active_session:
        return {"success": False, "error": "Session not available for agent transfer"}
    if getattr(agent_obj, "_agent_transfer_in_progress", False):
        return {"success": False, "error": "Agent transfer is already in progress"}

    call_id = getattr(agent_obj, "call_id", None)
    if not call_id:
        return {"success": False, "error": "Missing call_id"}

    handoff_payload = {
        "source_agent_id": getattr(agent_obj, "agent_id", None),
        "tool_name": tool_name,
        "target_agent_id": target_agent_id,
        "target_version_mode": target_version_mode,
        "target_version": target_version,
    }
    handoff_context = await fetch_agent_handoff_context(call_id, handoff_payload)
    if not handoff_context.get("success"):
        return {"success": False, "error": handoff_context.get("error") or "Failed to build handoff context"}

    target_payload = handoff_context.get("target_agent") or {}
    if not isinstance(target_payload, dict) or not str(target_payload.get("system_prompt", "")).strip():
        return {"success": False, "error": "Target agent runtime payload is incomplete"}

    merged_runtime_vars = dict(getattr(agent_obj, "runtime_vars", {}) or {})
    merged_runtime_vars.update(handoff_context.get("runtime_vars") or {})
    target_functions = merge_builtin_functions_into_runtime(
        list(target_payload.get("functions") or []),
        target_payload,
    )
    target_prompt, target_functions = build_effective_runtime_prompt(
        target_payload,
        target_functions,
        merged_runtime_vars,
    )
    runtime_bundle = build_runtime_engines_for_config(
        target_payload,
        is_phone_call=True,
        vad_instance=getattr(agent_obj, "vad_instance", None),
    )
    
    # Forcefully paralyze the old agent's realtime session to stop it from 
    # hallucinating fallback responses or crashing.
    _paralyze_old_session(agent_obj)

    # Interrupt the primary agent immediately so its speech pipeline drains
    # before we start building the subagent. This prevents bleed-through speech.
    if hasattr(agent_obj, "interrupt"):
        agent_obj.interrupt()

    # Forcefully close the old realtime session
    if hasattr(agent_obj, "_activity") and hasattr(agent_obj._activity, "_rt_session"):
        old_rt = getattr(agent_obj._activity, "_rt_session", None)
        if old_rt is not None:
            # Create a background task to close it so we don't block
            asyncio.create_task(old_rt.aclose())

    current_chat_ctx = None
    try:
        current_chat_ctx = agent_obj.chat_ctx if hasattr(agent_obj, "chat_ctx") else None
    except Exception:
        current_chat_ctx = None
    if current_chat_ctx is None:
        try:
            current_chat_ctx = getattr(active_session.agent, "chat_ctx", None)
        except Exception:
            current_chat_ctx = None

    # Detect if the target agent uses a realtime LLM (xAI / OpenAI Realtime).
    # Realtime models push chat_ctx over a WebSocket and time out on large histories.
    # For them, pass only the developer handoff note; the system prompt carries persona.
    _target_tts = normalize_tts_provider(target_payload)
    _target_runtime_mode = resolve_voice_runtime_mode(target_payload)
    _is_realtime_target = _target_tts == "xai" or _target_runtime_mode == "realtime_text_tts"

    new_chat_ctx = llm_module.ChatContext.empty()
    note_content = build_transfer_handoff_developer_note(
        str(handoff_context.get("handoff_summary") or "").strip(),
        handoff_context.get("caller_memory") or {},
    )
    
    if _is_realtime_target:
        # For realtime models, we append the note directly to the system prompt
        # instead of passing it as a developer message. This prevents the VAD
        # from treating it as a conversational turn that requires an apology or
        # an "I understand" acknowledgement.
        target_prompt += f"\n\n--- HANDOFF CONTEXT ---\n{note_content}\n-----------------------\n"
        target_prompt += "CRITICAL INSTRUCTION: You MUST begin your response using the EXACT greeting specified in your instructions. DO NOT acknowledge the handoff context or say 'I understand'."
    else:
        # For non-realtime models, we can safely use the developer message approach
        new_chat_ctx.add_message(
            role="developer",
            content=note_content,
        )
    if not _is_realtime_target and current_chat_ctx is not None:
        # For non-realtime (pipeline) models, include a short recent history window.
        try:
            copied_ctx = current_chat_ctx.copy(
                exclude_instructions=True,
                exclude_function_call=True,
                exclude_handoff=True,
                exclude_config_update=True,
            )
            copied_ctx.truncate(max_items=8)
            new_chat_ctx.merge(copied_ctx, exclude_instructions=True, exclude_function_call=True, exclude_config_update=True)
        except Exception as chat_ctx_err:
            logger.warning("Failed to merge chat context for agent transfer: %s", chat_ctx_err)

    agent_obj._agent_transfer_in_progress = True
    target_llm = runtime_bundle.get("llm")
    try:
        if _target_tts == "xai":
            # Recreate xAI realtime model for a fresh WebSocket session.
            # IMPORTANT: use resolve_voice_realtime_model() — NOT llm_model —
            # because llm_model holds the text-generation model name (e.g. gpt-5.1)
            # which is invalid for the xAI realtime/audio API.
            _target_realtime_model = resolve_voice_realtime_model(target_payload) or DEFAULT_XAI_REALTIME_MODEL
            _target_voice = target_payload.get("voice") or "ara"
            logger.info("Building xAI realtime model for subagent | model=%s | voice=%s", _target_realtime_model, _target_voice)
            target_llm, _ = _build_xai_realtime_model(
                selected_voice=_target_voice,
                voice_realtime_model=_target_realtime_model,
                xai_api_key=os.environ.get("XAI_API_KEY"),
            )
    except Exception as llm_err:
        logger.warning("Could not instantiate fresh RealtimeModel for subagent; falling back to shared session: %s", llm_err)

    try:
        # Give the interruption a moment to settle before swapping agents.
        await asyncio.sleep(max(0.05, TRANSFER_HANDOFF_DELAY_SEC))
        
        target_agent = create_dynamic_agent_class(
            functions_config=target_functions,
            base_instructions=target_prompt,
            current_room=agent_obj.room,
            call_id=call_id,
            session=active_session,
            agent_id=target_payload.get("agent_id"),
            agent_label=target_payload.get("name"),
            is_phone_call=True,
            runtime_vars=merged_runtime_vars,
            vad_instance=runtime_bundle.get("vad"),
            llm_engine=target_llm,
            tts_engine=runtime_bundle.get("tts_engine"),
            stt_engine=runtime_bundle.get("stt_engine"),
            chat_ctx=new_chat_ctx,
            is_subagent=True,
            is_realtime_target=_is_realtime_target,
        )

        if call_id:
            await report_builtin_action(
                call_id,
                "agent_transfer",
                {
                    "tool_name": tool_name,
                    "source_agent_id": getattr(agent_obj, "agent_id", None),
                    "source_agent_name": getattr(agent_obj, "agent_label", None),
                    "target_agent_id": target_agent_id,
                    "target_version_mode": target_version_mode,
                    "target_version": target_version,
                    "handoff_summary": str(handoff_context.get("handoff_summary") or "").strip(),
                    "caller_memory": handoff_context.get("caller_memory") or {},
                    "recent_transcript": handoff_context.get("recent_transcript") or [],
                },
            )

        # For v1.5.2, returning the target_agent natively handles the handoff
        # gracefully. The framework will update the chat context and then cleanly swap.
        
        # The subagent's on_enter() method will fire generate_reply once
        # the session swaps to it. No separate background task needed.
        logger.info("Agent swap complete — subagent on_enter will trigger greeting for: %s", target_payload.get("name"))
        return target_agent
    except Exception as handoff_exc:
        logger.error("agent_transfer handoff failed: %s", handoff_exc)
        return {"success": False, "error": str(handoff_exc)}
    finally:
        agent_obj._agent_transfer_in_progress = False


def create_dynamic_agent_class(
    functions_config,
    base_instructions,
    current_room=None,
    call_id=None,
    session=None,
    agent_id=None,
    agent_label=None,
    is_phone_call=False,
    runtime_vars=None,
    vad_instance=None,
    llm_engine=None,
    tts_engine=None,
    stt_engine=None,
    chat_ctx=None,
    is_subagent=False,
    is_realtime_target=False,
):
    if not functions_config:
        agent = Agent(
            instructions=base_instructions,
            chat_ctx=chat_ctx,
            llm=llm_engine,
            tts=tts_engine,
            stt=stt_engine,
            vad=vad_instance,
        )
        return agent

    on_enter_method = ""
    if is_subagent:
        on_enter_method = """
    async def on_enter(self):
        try:
            await self.session.generate_reply(
                allow_interruptions=True,
                input_modality="audio",
            )
        except Exception as _oe_err:
            logger.warning("on_enter greeting skipped: %s", _oe_err)
"""

    class_def = f"""
class DynamicPropertyAgent(Agent):
    def __init__(self, instructions, functions_config, room=None, call_id=None, session=None, agent_id=None, agent_label=None, is_phone_call=False, runtime_vars=None, vad_instance=None, llm_engine=None, tts_engine=None, stt_engine=None, chat_ctx=None):
        self.functions_config = functions_config
        self.room = room
        self.call_id = call_id
        self._runtime_session = session
        self.agent_id = agent_id
        self.agent_label = agent_label
        self.is_phone_call = is_phone_call
        self.runtime_vars = runtime_vars or {{}}
        self.vad_instance = vad_instance
        self._transfer_in_progress = False
        self._agent_transfer_in_progress = False
        self._recent_tool_call_times = {{}}
        self._pending_transfer_fallback_tasks = {{}}
        self._last_transfer_request_ts = 0.0
        self._last_transfer_target = ""
        self._pending_end_call_after_speech = False
        self._end_call_handoff_started = False
        super().__init__(instructions=instructions, chat_ctx=chat_ctx, llm=llm_engine, tts=tts_engine, stt=stt_engine, vad=vad_instance)
    def _mark_tool_call_observed(self, tool_name):
        normalized = _canonical_tool_name(tool_name)
        if not normalized:
            return
        self._recent_tool_call_times[normalized] = time.time()
        pending = self._pending_transfer_fallback_tasks.pop(normalized, None)
        if pending and not pending.done():
            pending.cancel()

    def _get_function_cfg(self, tool_name):
        normalized = _canonical_tool_name(tool_name)
        for cfg in self.functions_config:
            if _canonical_tool_name(cfg.get("name", "")) == normalized:
                return cfg
        return None

    async def _execute_configured_pstn_transfer(self, func_cfg, payload=None, tool_name=""):
        import json
        payload = payload or {{}}
        normalized_name = _canonical_tool_name(tool_name or func_cfg.get("name", ""))
        url = str(func_cfg.get("url", "")).strip()
        system_type = _normalize_tool_name(func_cfg.get("system_type", ""))

        sys_cfg = func_cfg.get("system_config") or {{}}
        if isinstance(sys_cfg, str):
            try:
                sys_cfg = json.loads(sys_cfg)
            except Exception:
                sys_cfg = {{}}

        vars_cfg = func_cfg.get("variables") or {{}}
        target_phone = (
            str(sys_cfg.get("phone_number") or "").strip()
            or str(vars_cfg.get("__transfer_phone__") or "").strip()
            or str(func_cfg.get("phone_number") or "").strip()
            or str(payload.get("phone_number") or "").strip()
        )

        self._mark_tool_call_observed(normalized_name)
        logger.info(f"PSTN Transfer Triggered ({{normalized_name}}) -> {{target_phone}}")

        if not (
            system_type == "transfer_call"
            or url == "builtin://transfer_call"
            or str(func_cfg.get("variables", {{}})).find("__transfer_phone__") != -1
        ):
            return {{"success": False, "error": "Function is not configured as a PSTN transfer"}}
        if not target_phone:
            return {{"success": False, "error": "Transfer phone number is not configured"}}
        if not self.room:
            return {{"success": False, "error": "Room not available for transfer"}}
        if self._transfer_in_progress:
            return {{"success": False, "error": "Transfer is already in progress"}}
        now_ts = time.time()
        if (
            self._last_transfer_target
            and target_phone == self._last_transfer_target
            and (now_ts - float(self._last_transfer_request_ts or 0.0)) < TRANSFER_DUPLICATE_SUPPRESS_SEC
        ):
            return {{
                "success": True,
                "action": normalized_name,
                "phone_number": target_phone,
                "status": "duplicate_suppressed",
                "message": "Transfer already initiated recently; skipping duplicate request.",
            }}

        _paralyze_old_session(self)
        if hasattr(self, "interrupt"):
            self.interrupt()
        self._last_transfer_request_ts = now_ts
        self._last_transfer_target = target_phone
        if hasattr(self, "call_id") and self.call_id:
            await report_builtin_action(
                self.call_id,
                "transfer_call",
                {{"tool_name": normalized_name, "phone_number": target_phone, "status": "handoff_queued"}},
            )
        self._transfer_in_progress = True

        async def _do_pstn_handoff():
            try:
                handoff_result = await run_transfer_handoff(
                    self.room,
                    getattr(self, "call_id", None),
                    target_phone,
                )
                logger.info(f"PSTN handoff result: {{handoff_result}}")
                if hasattr(self, "call_id") and self.call_id:
                    payload = {{"tool_name": normalized_name, "phone_number": target_phone}}
                    if isinstance(handoff_result, dict):
                        payload.update(handoff_result)
                    await report_builtin_action(self.call_id, "transfer_call", payload)
            except Exception as handoff_exc:
                logger.error(f"PSTN handoff failed: {{handoff_exc}}")
                if hasattr(self, "call_id") and self.call_id:
                    await report_builtin_action(
                        self.call_id,
                        "transfer_call",
                        {{
                            "tool_name": normalized_name,
                            "phone_number": target_phone,
                            "status": "failed",
                            "error": str(handoff_exc),
                        }},
                    )
            finally:
                self._transfer_in_progress = False

        asyncio.create_task(_do_pstn_handoff())
        return {{
            "success": True,
            "action": "transfer_call",
            "phone_number": target_phone,
            "status": "handoff_queued",
            "message": "Handoff queued; announce transfer to caller now.",
        }}

    def _match_spoken_transfer_tool(self, content):
        text = re.sub(r"\\s+", " ", str(content or "").strip().lower())
        if not text:
            return ""
        transfer_language = (
            "transfer" in text
            or "connecting you" in text
            or "connect you" in text
            or "put you through" in text
            or "putting you through" in text
        )
        generic_transfer_tool = ""
        for func_cfg in self.functions_config:
            if not _is_transfer_tool(func_cfg):
                continue
            tool_name = _normalize_tool_name(func_cfg.get("name", ""))
            if not tool_name:
                continue
            hints = _spoken_transfer_hints_for_tool(tool_name)
            if tool_name in text:
                return tool_name
            if _is_generic_transfer_tool_name(tool_name):
                if any(hint and hint in text for hint in hints):
                    return tool_name
                if not generic_transfer_tool:
                    generic_transfer_tool = tool_name
                continue
            if transfer_language and any(hint and hint in text for hint in hints):
                return tool_name
        if transfer_language and generic_transfer_tool:
            return generic_transfer_tool
        return ""

    def _schedule_spoken_transfer_fallback(self, content):
        tool_name = self._match_spoken_transfer_tool(content)
        normalized_tool_name = _canonical_tool_name(tool_name)
        if not normalized_tool_name:
            return
        if (
            self._last_transfer_target
            and (time.time() - float(self._last_transfer_request_ts or 0.0)) < TRANSFER_DUPLICATE_SUPPRESS_SEC
        ):
            return
        existing = self._pending_transfer_fallback_tasks.get(normalized_tool_name)
        if existing and not existing.done():
            return

        async def _runner():
            try:
                await asyncio.sleep(0.35)
                if self._transfer_in_progress or self._agent_transfer_in_progress:
                    return
                last_seen = float(self._recent_tool_call_times.get(normalized_tool_name, 0.0) or 0.0)
                if last_seen and (time.time() - last_seen) < 1.0:
                    return

                func_cfg = self._get_function_cfg(normalized_tool_name)
                if not func_cfg:
                    return

                # Immediately silence the agent before the actual handoff so it
                # stops producing bleed-through speech while the transfer executes.
                _paralyze_old_session(self)
                if hasattr(self, "interrupt"):
                    self.interrupt()

                logger.warning(
                    "Transfer speech detected without tool call; forcing fallback for %s",
                    normalized_tool_name,
                )
                fallback_payload = {{"trigger": "spoken_transfer_fallback"}}
                if hasattr(self, "call_id") and self.call_id:
                    try:
                        msg = f"[Calling tool: {{normalized_tool_name}}] {{json.dumps(fallback_payload)}}"
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_call", msg))
                    except Exception:
                        pass
                if self.room:
                    try:
                        asyncio.ensure_future(self.room.local_participant.publish_data(
                            json.dumps({{"type": "tool_call", "tool_name": normalized_tool_name, "args": fallback_payload, "speech_mode": "default"}}),
                            topic="room"
                        ))
                    except Exception as publish_exc:
                        logger.error(f"Failed to publish spoken transfer fallback tool_call event: {{publish_exc}}")
                system_type = _normalize_tool_name(func_cfg.get("system_type", ""))
                url = str(func_cfg.get("url", "")).strip()
                if (
                    system_type == "transfer_call"
                    or url == "builtin://transfer_call"
                    or str(func_cfg.get("variables", {{}})).find("__transfer_phone__") != -1
                ):
                    result = await self._execute_configured_pstn_transfer(
                        func_cfg,
                        tool_name=normalized_tool_name,
                    )
                else:
                    self._mark_tool_call_observed(normalized_tool_name)
                    result = await perform_agent_transfer_handoff(
                        self,
                        normalized_tool_name,
                        func_cfg,
                        "default",
                    )
                if hasattr(self, "call_id") and self.call_id:
                    try:
                        msg = f"[Tool response: {{normalized_tool_name}}] {{json.dumps(result)}}"
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_response", msg))
                    except Exception:
                        pass
                if self.room:
                    try:
                        asyncio.ensure_future(self.room.local_participant.publish_data(
                            json.dumps({{"type": "tool_response", "tool_name": normalized_tool_name, "response": result}}),
                            topic="room"
                        ))
                    except Exception as publish_exc:
                        logger.error(f"Failed to publish spoken transfer fallback tool_response event: {{publish_exc}}")
                logger.info("Forced transfer fallback result (%s): %s", normalized_tool_name, result)
            except asyncio.CancelledError:
                pass
            except Exception as fallback_exc:
                logger.error(
                    "Forced transfer fallback failed for %s: %s",
                    normalized_tool_name,
                    fallback_exc,
                )
            finally:
                self._pending_transfer_fallback_tasks.pop(normalized_tool_name, None)

        self._pending_transfer_fallback_tasks[normalized_tool_name] = asyncio.create_task(_runner())
{on_enter_method}"""

    for func in functions_config:
        func_name = _normalize_tool_name(func.get("name", ""))
        if not func_name:
            continue
        logger.info("Creating tool method for: %s (system_type=%s)", func_name, func.get("system_type", ""))

        speak_during, speak_after = _normalize_tool_speech_flags(
            func.get("speak_during_execution", False),
            func.get("speak_after_execution", True),
            fallback_after=True,
        )
        speech_mode = "during" if speak_during else "after" if speak_after else "default"
        # Transfer tools: never speak after execution to prevent double-talk
        if _is_transfer_tool(func):
            speak_after = False
            speech_mode = "default"
            desc = func.get('description', '').strip().replace('"', "'").replace('\n', ' ')
            desc = f"{desc} IMPORTANT: First say 'I am transferring you now', THEN call this tool immediately."
        else:
            speech_hint = (
                "Before calling this tool, first tell the caller what you are doing; then share a concise result."
                if speak_during
                else "Call this tool first, then explain the result after it finishes."
            )
            desc = f"{func.get('description', '').strip()} {speech_hint}".strip().replace('"', "'").replace('\n', ' ')

        variables = func.get("variables", {})
        if not variables:
            schema = func.get("parameters_schema", {})
            if isinstance(schema, dict) and "properties" in schema:
                variables = schema.get("properties", {})

        args_def = ["self", "ctx: RunContext"]
        args_dict_str = []
        for v_name, v_info in variables.items():
            clean_v_name = v_name.strip().replace(" ", "_").lower()
            v_desc = str(v_info.get("description", "")).replace('"', "'").replace('\n', ' ')
            v_type = v_info.get("type", "string")
            py_type = "str"
            if v_type in ["integer", "number"]:
                py_type = "int"
            elif v_type == "boolean":
                py_type = "bool"

            args_def.append(f'{clean_v_name}: Annotated[{py_type}, "{v_desc}"] = ""')
            args_dict_str.append(f'"{clean_v_name}": {clean_v_name}')

        args_str = ", ".join(args_def)
        payload_body_str = ", ".join(args_dict_str)

        method_def = f"""
    @function_tool(description="{desc}")
    async def {func_name}({args_str}) -> dict:
        import json
        payload = {{ {payload_body_str} }}
        normalized_tool_name = _canonical_tool_name("{func_name}")
        speech_mode = "{speech_mode}"
        # For builtin transfer, force payload phone_number from dashboard config.
        # This prevents model-provided numbers from overriding configured transfer target.
        _is_pstn_transfer = False
        _configured_phone = ""
        for _cfg in self.functions_config:
            if _canonical_tool_name(_cfg.get("name", "")) == normalized_tool_name:
                _url = _cfg.get("url", "")
                _sys_type = _normalize_tool_name(_cfg.get("system_type", ""))
                if _sys_type == "transfer_call" or _url == "builtin://transfer_call":
                    _is_pstn_transfer = True
                    _sys_cfg_val = _cfg.get("system_config") or {{}}
                    if isinstance(_sys_cfg_val, str):
                        try:
                            import json as _json
                            _sys_cfg_val = _json.loads(_sys_cfg_val)
                        except:
                            _sys_cfg_val = {{}}
                    _configured_phone = str(_cfg.get("phone_number", "") or _sys_cfg_val.get("phone_number", "")).strip()
                break
        
        if _is_pstn_transfer and _configured_phone:
            payload["phone_number"] = _configured_phone
        logger.info(f"Tool {{normalized_tool_name}} called with args: {{payload}}")
        self._mark_tool_call_observed(normalized_tool_name)
        
        # Send tool call transcript
        if hasattr(self, 'call_id') and self.call_id:
            try:
                import httpx
                msg = f"[Calling tool: {{normalized_tool_name}}] {{json.dumps(payload)}}"
                asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_call", msg))
            except:
                pass

        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_call", "tool_name": normalized_tool_name, "args": payload, "speech_mode": speech_mode}}),
                    topic="room"
                ))
            except Exception as e:
                logger.error(f"Failed to publish tool_call event: {{e}}")

        result = {{"error": "Tool execution failed"}}

        for func_cfg in self.functions_config:
            if _canonical_tool_name(func_cfg.get("name", "")) == normalized_tool_name:
                normalized_name = _canonical_tool_name(func_cfg.get("name", ""))
                url = func_cfg.get("url", "")
                method = func_cfg.get("method", "POST").upper()
                timeout_ms = func_cfg.get("timeout_ms", 120000)
                headers = func_cfg.get("headers", {{}})
                system_type = _normalize_tool_name(func_cfg.get("system_type", ""))

                payload, validation_errors = _validate_and_normalize_tool_payload(payload, func_cfg)
                if validation_errors:
                    result = {{
                        "success": False,
                        "error": "Tool parameter validation failed",
                        "details": validation_errors,
                    }}
                    break

                normalized_name = normalized_tool_name
                if system_type == "transfer_call" or url == "builtin://transfer_call" or str(func_cfg.get("variables", {{}})).find("__transfer_phone__") != -1:
                    result = await self._execute_configured_pstn_transfer(
                        func_cfg,
                        payload=payload,
                        tool_name=normalized_name,
                    )
                    break
                elif system_type == "agent_transfer" or url == "builtin://agent_transfer" or normalized_tool_name.endswith("_agent_transfer"):
                    if hasattr(self, "interrupt"):
                        self.interrupt()
                    result = await perform_agent_transfer_handoff(
                        self,
                        normalized_tool_name,
                        func_cfg,
                        speech_mode,
                    )
                elif normalized_name == "end_call":
                    if hasattr(self, "call_id") and self.call_id:
                        result = await report_builtin_action(
                            self.call_id,
                            "end_call",
                            {{"reason": str(payload.get("reason", "")).strip()}},
                        )
                        if result.get("success") and self.room:
                            if speech_mode == "after":
                                self._pending_end_call_after_speech = True
                                self._end_call_handoff_started = False
                                result["status"] = "awaiting_post_speech_handoff"
                                result["message"] = "Acknowledge the call ending, then hang up."
                            else:
                                self._pending_end_call_after_speech = False
                                self._end_call_handoff_started = True
                                async def _do_end_handoff():
                                    try:
                                        end_handoff_result = await run_end_call_handoff(self.room)
                                        logger.info(f"end_call handoff result: {{end_handoff_result}}")
                                    except Exception as end_handoff_exc:
                                        logger.error(f"end_call handoff failed: {{end_handoff_exc}}")
                                asyncio.create_task(_do_end_handoff())
                    else:
                        result = {{"success": False, "error": "Missing call_id"}}
                elif url:
                    try:
                        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
                            if method == "GET":
                                response = await client.get(url, headers=headers, params=payload)
                            else:
                                response = await client.post(url, headers=headers, json=payload)

                            try:
                                result = response.json()
                            except:
                                result = {{"response": response.text, "status": response.status_code}}
                    except Exception as e:
                        logger.error(f"Error calling {{normalized_tool_name}}: {{e}}")
                        result = {{"error": str(e)}}
                else:
                    result = {{"success": False, "error": "Function URL is empty"}}
                break

        # Send tool response transcript
        if hasattr(self, 'call_id') and self.call_id:
            try:
                import httpx
                msg = f"[Tool response: {{normalized_tool_name}}] {{json.dumps(result)}}"
                asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_response", msg))
            except:
                pass

        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_response", "tool_name": normalized_tool_name, "response": result}}),
                    topic="room"
                ))
            except:
                pass

        return result
"""
        class_def += method_def

    local_vars = {}
    exec(class_def, globals(), local_vars)
    AgentClass = local_vars["DynamicPropertyAgent"]
    return AgentClass(
        instructions=base_instructions,
        functions_config=functions_config,
        room=current_room,
        call_id=call_id,
        session=session,
        agent_id=agent_id,
        agent_label=agent_label,
        is_phone_call=is_phone_call,
        runtime_vars=runtime_vars,
        vad_instance=vad_instance,
        llm_engine=llm_engine,
        tts_engine=tts_engine,
        stt_engine=stt_engine,
        chat_ctx=chat_ctx,
    )


# ==================== SIP Detection ====================

def detect_sip_participant(room):
    for participant in room.remote_participants.values():
        if _participant_is_sip(participant):
            return participant
    return None


def get_sip_phone_numbers(participant):
    from_number = None
    to_number = None
    if hasattr(participant, 'attributes') and participant.attributes:
        attrs = participant.attributes
        from_number = attrs.get("sip.callerNumber") or attrs.get("sip.from", "")
        to_number = (
            attrs.get("sip.calledNumber")
            or attrs.get("sip.phoneNumber")
            or attrs.get("sip.trunkPhoneNumber")
            or attrs.get("sip.to", "")
        )
    
    def normalize_phone(phone):
        if not phone:
            return None
        phone = str(phone).strip()
        if phone.lower().startswith("phone "):
            phone = phone[6:].strip()
        return phone if phone else None
    
    from_number = normalize_phone(from_number)
    to_number = normalize_phone(to_number)
    return from_number, to_number


def get_sip_trunk_id(participant: Any) -> Optional[str]:
    attrs = getattr(participant, "attributes", None) or {}
    for key in ("sip.trunkID", "sip.trunkId", "sip.trunk_id"):
        value = str(attrs.get(key, "") or "").strip()
        if value:
            return value
    return None


async def wait_for_inbound_sip_participant(room: Any, timeout_sec: float = 8.0):
    deadline = time.monotonic() + max(timeout_sec, 0.5)
    last_participant = None

    while time.monotonic() < deadline:
        participant = detect_sip_participant(room)
        if participant:
            last_participant = participant
            from_number, to_number = get_sip_phone_numbers(participant)
            if from_number or to_number or _participant_sip_state(participant):
                return participant
        await asyncio.sleep(0.25)

    return last_participant


# ==================== Transcript Collector ====================

class TranscriptCollector:
    """Collects transcripts by monitoring chat context changes"""
    def __init__(self, call_id, usage, llm_model):
        self.call_id = call_id
        self.usage = usage
        self.llm_model = llm_model
        self.last_user_msg_count = 0
        self.last_agent_msg_count = 0
        self._running = True
        self._session = None

    def set_session(self, session):
        self._session = session

    def stop(self):
        self._running = False

    @staticmethod
    def _resolve_message_attr(item: Any, attr_name: str) -> Any:
        value = getattr(item, attr_name, None)
        if callable(value):
            try:
                value = value()
            except TypeError:
                return None
            except Exception:
                return None
        return value

    @classmethod
    def _extract_message_text(cls, item: Any) -> str:
        content = cls._resolve_message_attr(item, "content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(str(c) for c in content if c)

        text = cls._resolve_message_attr(item, "text")
        if isinstance(text, str):
            return text
        if isinstance(text, list):
            return " ".join(str(c) for c in text if c)

        return ""

    async def monitor_chat_context(self, session):
        """Periodically check chat context for new messages"""
        self._session = session
        seen_messages = set()
        
        while self._running:
            try:
                await asyncio.sleep(1)
                if not self._session:
                    continue
                    
                # Access chat context correctly - session.agent.chat_ctx
                ctx = None
                try:
                    if hasattr(self._session, 'agent') and self._session.agent:
                        agent = self._session.agent
                        if hasattr(agent, 'chat_ctx'):
                            ctx = agent.chat_ctx
                        else:
                            logger.debug(f"No chat_ctx on agent: {dir(agent)[:50]}")
                    else:
                        logger.debug(f"No agent on session or session.agent is None")
                except Exception as e:
                    logger.debug(f"Error getting chat_ctx: {e}")
                
                if not ctx:
                    continue
                
                messages = []
                try:
                    if hasattr(ctx, 'messages'):
                        messages = ctx.messages
                        if callable(messages):
                            messages = messages()
                except Exception as e:
                    logger.debug(f"Error reading messages: {e}")
                
                for msg in messages:
                    role = self._resolve_message_attr(msg, 'role') or ''
                    content = self._extract_message_text(msg)
                    
                    if not content or role == 'system':
                        continue
                    
                    msg_key = f"{role}:{content[:50]}"
                    if msg_key in seen_messages:
                        continue
                    seen_messages.add(msg_key)
                    
                    if role == 'user':
                        word_count = len(content.split())
                        est_duration = int((word_count / 150.0) * 60 * 1000)
                        self.usage.add_stt_duration(est_duration)
                        self.usage.add_llm_usage(tokens_in=len(content) // 4, model=self.llm_model)
                        self.usage.add_transcript("user", content)
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "user", content))
                        logger.info(f"[transcript] User: {content[:60]}...")
                    elif role == 'assistant':
                        self.usage.add_tts_characters(len(content))
                        self.usage.add_llm_usage(tokens_out=len(content) // 4, model=self.llm_model)
                        self.usage.add_transcript("agent", content)
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "agent", content))
                        logger.info(f"[transcript] Agent: {content[:60]}...")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Monitor error: {e}")
                await asyncio.sleep(2)


# ==================== Main Entrypoint ====================

async def entrypoint(ctx: JobContext):
    global _active_call_id, _active_usage

    logger.info(f"Starting session for room: {ctx.room.name}")

    usage = UsageTracker()
    call_id = None
    agent_id = 5
    direction = "outbound"
    from_number = None
    to_number = None
    sip_trunk_id = None
    dispatch_name_hint = None

    try:
        room_name = ctx.room.name
        logger.info(f"Extracting agent_id from room: {room_name}")

        if room_name.startswith("call_"):
            parts = room_name.split("_")
            if len(parts) >= 3 and parts[1].isdigit():
                try:
                    agent_id = int(parts[1])
                    direction = "outbound"
                    logger.info(f"Web/outbound call for agent_id: {agent_id}")
                except:
                    agent_id = 5
            else:
                # Room like "call_sarah" from dispatch rule - treat as inbound.
                direction = "inbound"
                dispatch_name_hint = room_name[len("call_"):].strip() or None
                logger.info(f"Inbound call (dispatch room): {room_name}")
        elif room_name.startswith("call-") or room_name.startswith("sip-"):
            direction = "inbound"
            dispatch_name_hint = room_name.replace("call-", "", 1).replace("sip-", "", 1).strip() or None
            logger.info(f"Inbound call detected: {room_name}")
        else:
            parts = room_name.split("_")
            if len(parts) > 1:
                try:
                    agent_id = int(parts[1])
                except:
                    agent_id = 5
    except Exception as e:
        logger.error(f"Error parsing room name: {e}")

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    if direction == "inbound":
        phone_agent = None
        sip_participant = await wait_for_inbound_sip_participant(ctx.room)
        if sip_participant:
            from_number, to_number = get_sip_phone_numbers(sip_participant)
            sip_trunk_id = get_sip_trunk_id(sip_participant)
            logger.info(f"Inbound from: {from_number} to: {to_number} (trunk_id={sip_trunk_id})")

            # Try to find agent by phone number - try both to_number and from_number
            if to_number:
                phone_agent = await fetch_agent_by_phone(to_number)
                if phone_agent:
                    logger.info(f"Found agent by to_number {to_number}: agent_id={phone_agent.get('agent_id')}")

            # If not found, try from_number
            if not phone_agent and from_number:
                phone_agent = await fetch_agent_by_phone(from_number)
                if phone_agent:
                    logger.info(f"Found agent by from_number {from_number}: agent_id={phone_agent.get('agent_id')}")
        else:
            logger.warning("Inbound call did not expose SIP participant metadata within wait window for room %s", ctx.room.name)

        # If SIP numbers are missing/unreliable, resolve by dispatch worker name hint.
        if (
            not phone_agent
            and dispatch_name_hint
            and dispatch_name_hint.lower() != DEFAULT_WORKER_DISPATCH_NAME
        ):
            dispatch_agent = await fetch_agent_by_dispatch_name(dispatch_name_hint)
            if dispatch_agent:
                phone_agent = dispatch_agent
                logger.info(
                    "Found agent by dispatch name %s: agent_id=%s",
                    dispatch_name_hint,
                    dispatch_agent.get("agent_id"),
                )

        if phone_agent:
            new_agent_id = phone_agent.get("agent_id", agent_id)
            if new_agent_id != agent_id:
                logger.info(f"Updating agent_id from {agent_id} to {new_agent_id} based on inbound routing")
                agent_id = new_agent_id
        else:
            single_inbound_agent = await fetch_single_inbound_agent_id()
            if single_inbound_agent and single_inbound_agent != agent_id:
                logger.info(
                    "Using single inbound phone mapping fallback, agent_id=%s",
                    single_inbound_agent,
                )
                agent_id = single_inbound_agent
            else:
                logger.warning(
                    "No agent found for inbound routing - from: %s, to: %s, dispatch_hint: %s, dispatch_fallback_enabled: %s",
                    from_number,
                    to_number,
                    dispatch_name_hint,
                    USE_DISPATCH_NAME_INBOUND_FALLBACK,
                )

    # Create call record
    call_id, resolved_agent_id, call_metadata = await create_call_record(
        room_name=ctx.room.name,
        agent_id=agent_id,
        direction=direction,
        from_number=from_number,
        to_number=to_number,
        sip_trunk_id=sip_trunk_id,
        dispatch_name_hint=dispatch_name_hint,
    )
    if resolved_agent_id and resolved_agent_id != agent_id:
        logger.info(
            "Adjusted agent_id from %s to %s based on call record routing",
            agent_id,
            resolved_agent_id,
        )
        agent_id = resolved_agent_id
    logger.info(f"Call record created: {call_id}")

    metadata = call_metadata if isinstance(call_metadata, dict) else {}
    metadata_runtime_vars = normalize_runtime_vars(metadata.get("runtime_vars"))
    runtime_vars: Dict[str, str] = dict(metadata_runtime_vars)
    call_meta_from = str(metadata.get("from_number", "") or "").strip()
    call_meta_to = str(metadata.get("to_number", "") or "").strip()
    if not from_number and call_meta_from:
        from_number = call_meta_from
    if not to_number and call_meta_to:
        to_number = call_meta_to
    if call_meta_from:
        runtime_vars.setdefault("from_number", call_meta_from)
    if call_meta_to:
        runtime_vars.setdefault("to_number", call_meta_to)
    if call_id:
        runtime_vars.setdefault("call_id", call_id)
    if runtime_vars:
        logger.info("Loaded runtime template vars for this call: %s", sorted(runtime_vars.keys()))

    # Register for atexit cleanup
    _active_call_id = call_id
    _active_usage = usage

    # Fetch config and function metadata in parallel so the worker can start speaking sooner.
    config, functions = await asyncio.gather(
        fetch_agent_config(agent_id),
        fetch_agent_functions(agent_id),
    )
    custom_params = config.get("custom_params", {}) or {}

    functions = merge_builtin_functions_into_runtime(functions, config)
    logger.info(f"Agent: {config.get('name')}, Functions: {len(functions)}")

    transfer_guidance = build_transfer_instructions(functions)
    if transfer_guidance:
        sys_prompt = f"{sys_prompt}\n\n{transfer_guidance}"
        logger.info("Appended transfer instructions to system prompt (length now %d)", len(sys_prompt))

    is_phone_call = bool(
        from_number
        or to_number
        or runtime_vars.get("from_number")
        or runtime_vars.get("to_number")
        or str(call_id or "").startswith(("inbound_", "outbound_"))
        or direction == "inbound"
    )
    agent_lang = normalize_agent_language(config.get("language", "en-GB"))

    # Voice / TTS provider config
    selected_voice = config.get("voice", "jessica")
    tts_provider = normalize_tts_provider(config)
    if tts_provider == "elevenlabs":
        selected_voice = ELEVENLABS_VOICE_MAP.get(selected_voice.lower(), selected_voice)
    elif tts_provider == "xai":
        selected_voice = normalize_xai_voice_id(selected_voice)
    selected_tts_model = (
        config.get("tts_model")
        or (config.get("custom_params") or {}).get("tts_model")
    )
    llm_temperature = resolve_llm_temperature(config)
    voice_speed = resolve_voice_speed(config)
    reasoning_effort = resolve_openai_reasoning_effort(config)
    verbosity = resolve_openai_verbosity(config)
    max_completion_tokens = resolve_openai_max_completion_tokens(config)
    voice_runtime_mode = resolve_voice_runtime_mode(config)
    voice_realtime_model = resolve_voice_realtime_model(config)

    tts_engine = None
    resolved_voice_id = selected_voice
    if tts_provider == "xai":
        selected_tts_model = voice_realtime_model or selected_tts_model or DEFAULT_XAI_REALTIME_MODEL
    if tts_provider == "elevenlabs":
        eleven_key = get_elevenlabs_api_key()
        selected_tts_model = resolve_elevenlabs_tts_model_for_language(
            selected_tts_model,
            agent_lang,
        )
        if not eleven_key:
            raise RuntimeError("ElevenLabs selected but ELEVEN_API_KEY / ELEVENLABS_API_KEY is not set")

        # ElevenLabs v3 doesn't support the websocket multi-stream-input endpoint.
        # Use native LiveKit tts.StreamAdapter to force HTTP mode for v3 models.
        # For v2/v2.5, use the standard plugin with websocket streaming for low latency.
        is_v3_model = "v3" in selected_tts_model.lower() and "flash" not in selected_tts_model.lower()
        enable_ssml_parsing = _coerce_setting_bool(
            custom_params.get("elevenlabs_enable_ssml_parsing"),
            not is_v3_model,
        )
        
        eleven_kwargs: Dict[str, Any] = {
            "voice_id": selected_voice,
            "model": selected_tts_model,
            "api_key": eleven_key,
            "enable_ssml_parsing": enable_ssml_parsing,
            "enable_logging": True,
        }
        if _callable_supports_kwarg(elevenlabs.TTS, "voice_settings"):
            voice_settings = build_elevenlabs_voice_settings(
                config,
                voice_speed,
                include_extended_settings=not is_v3_model,
            )
            if voice_settings is not None:
                eleven_kwargs["voice_settings"] = voice_settings
        if not is_v3_model and _callable_supports_kwarg(elevenlabs.TTS, "streaming_latency"):
            eleven_kwargs["streaming_latency"] = _coerce_setting_int(ELEVENLABS_STREAMING_LATENCY, default=2, min_value=0, max_value=4)
        if not is_v3_model and _callable_supports_kwarg(elevenlabs.TTS, "auto_mode"):
            eleven_kwargs["auto_mode"] = ELEVENLABS_AUTO_MODE

        if is_v3_model:
            # eleven_v3 doens't support websocket streaming; use LiveKit's native StreamAdapter
            # which wraps the TTS plugin in HTTP (non-streaming) mode.
            logger.info("ElevenLabs v3 detected: using tts.StreamAdapter (HTTP mode) for voice synthesis.")
            from livekit.agents import tts as lk_tts
            from livekit.agents import tokenize as lk_tokenize
            base_tts = elevenlabs.TTS(**eleven_kwargs)
            tts_engine = lk_tts.StreamAdapter(tts=base_tts, sentence_tokenizer=lk_tokenize.basic.SentenceTokenizer())
        else:
            tts_engine = elevenlabs.TTS(**eleven_kwargs)
        resolved_voice_id = selected_voice


        logger.info(
            "TTS initialized: provider=elevenlabs, model=%s, voice=%s",
            selected_tts_model,
            selected_voice,
        )

    if tts_provider == "deepgram":
        mapped_voice = DEEPGRAM_VOICE_MAP.get(str(selected_voice).lower(), selected_voice)
        deepgram_kwargs: Dict[str, Any] = {"model": mapped_voice}
        tts_engine = deepgram.TTS(**deepgram_kwargs)
        resolved_voice_id = mapped_voice
        selected_tts_model = None

    llm_model = config.get("llm_model", "gpt-4o-mini")
    is_phone_call_for_llm = is_phone_call
    enable_phone_model_override = _coerce_setting_bool(
        custom_params.get("force_phone_llm_model_override"),
        False,
    )
    if is_phone_call_for_llm and enable_phone_model_override:
        requested_model = str(llm_model or "").strip().lower()
        target_model = str(custom_params.get("phone_llm_model") or "").strip()
        if target_model and requested_model != target_model.lower():
            logger.info(
                "Applying phone LLM model override: %s -> %s",
                llm_model,
                target_model,
            )
            llm_model = target_model

    enable_phone_token_cap = _coerce_setting_bool(
        custom_params.get("force_phone_llm_token_cap"),
        False,
    )
    if is_phone_call_for_llm and enable_phone_token_cap:
        capped_tokens = min(max_completion_tokens, PHONE_LOW_LATENCY_MAX_TOKENS)
        if capped_tokens != max_completion_tokens:
            logger.info(
                "Applying low-latency cap for %s on phone call: max_completion_tokens %s -> %s",
                llm_model,
                max_completion_tokens,
                capped_tokens,
            )
            max_completion_tokens = capped_tokens
    runtime_llm_model = llm_model
    is_moonshot = "moonshot" in llm_model.lower() or "kimi" in llm_model.lower() or "moonlight" in llm_model.lower()
    is_gpt5_family = str(llm_model or "").strip().lower().startswith("gpt-5")
    supports_custom_temperature = model_supports_custom_temperature(llm_model)
    effective_llm_temperature = llm_temperature if supports_custom_temperature else 1.0

    base_url = "https://api.moonshot.cn/v1" if is_moonshot else None
    raw_key = os.getenv("MOONSHOT_API_KEY") if is_moonshot else os.getenv("OPENAI_API_KEY")
    api_key = raw_key.strip() if raw_key else ""
    if not api_key:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    xai_api_key = get_xai_api_key()

    llm = None
    use_realtime_llm = False
    use_unified_realtime_audio = False
    if tts_provider == "xai":
        if not voice_realtime_model:
            raise RuntimeError("xAI selected but no realtime model was saved in the app")
        if not xai_api_key:
            raise RuntimeError("xAI selected but XAI_API_KEY is not set")
        try:
            llm, runtime_llm_model = _build_xai_realtime_model(
                selected_voice=selected_voice,
                voice_realtime_model=voice_realtime_model,
                xai_api_key=xai_api_key,
            )
            base_url = XAI_REALTIME_BASE_URL
            use_realtime_llm = True
            use_unified_realtime_audio = True
            # Disable chat_ctx sync for this path to prevent history-matching errors/latency
            chat_ctx = None
        except Exception as realtime_err:
            raise RuntimeError(f"xAI unified realtime voice path unavailable: {realtime_err}") from realtime_err
    elif (
        voice_runtime_mode == "realtime_text_tts"
        and voice_realtime_model
        and tts_engine is not None
        and openai_api_key
        and hasattr(openai, "realtime")
        and hasattr(openai.realtime, "RealtimeModel")
    ):
        realtime_kwargs: Dict[str, Any] = {
            "model": voice_realtime_model,
            "api_key": openai_api_key,
            "modalities": ["text"],
        }
        turn_detection = _build_openai_realtime_turn_detection()
        if turn_detection is not None:
            realtime_kwargs["turn_detection"] = turn_detection
        try:
            llm = openai.realtime.RealtimeModel(**realtime_kwargs)
            runtime_llm_model = voice_realtime_model
            use_realtime_llm = True
        except Exception as realtime_err:
            logger.warning("OpenAI Realtime voice path unavailable; falling back to pipeline LLM: %s", realtime_err)
    elif voice_runtime_mode == "realtime_text_tts" and not voice_realtime_model:
        logger.warning(
            "voice_runtime_mode=realtime_text_tts was requested, but no voice_realtime_model was saved in the app. Falling back to pipeline."
        )

    logger.info(
        "Using tts_provider=%s, voice=%s, tts_model=%s, llm_model=%s, runtime_mode=%s, base_url=%s, llm_temperature=%.2f, voice_speed=%.2f, reasoning=%s, verbosity=%s, max_tokens=%s",
        tts_provider,
        resolved_voice_id,
        selected_tts_model,
        runtime_llm_model,
        voice_runtime_mode,
        base_url,
        effective_llm_temperature,
        voice_speed,
        reasoning_effort,
        verbosity,
        max_completion_tokens,
    )
    usage.llm_model = runtime_llm_model
    usage.tts_provider = tts_provider
    usage.tts_model = selected_tts_model or ""
    usage.tts_voice_id = selected_voice if tts_provider in {"elevenlabs", "xai"} else resolved_voice_id
    usage.llm_temperature = effective_llm_temperature
    usage.voice_speed = voice_speed
    usage.language = agent_lang

    if llm is None:
        llm_kwargs: Dict[str, Any] = {"api_key": api_key, "base_url": base_url, "model": llm_model}
        if _callable_supports_kwarg(openai.LLM, "temperature") and supports_custom_temperature:
            llm_kwargs["temperature"] = effective_llm_temperature
        elif not supports_custom_temperature:
            logger.info(
                "Skipping temperature override for model=%s; provider currently enforces default temperature.",
                llm_model,
            )
        if not is_moonshot:
            if is_gpt5_family and _callable_supports_kwarg(openai.LLM, "reasoning_effort"):
                llm_kwargs["reasoning_effort"] = reasoning_effort
            if is_gpt5_family and _callable_supports_kwarg(openai.LLM, "verbosity"):
                llm_kwargs["verbosity"] = verbosity
            if _callable_supports_kwarg(openai.LLM, "max_completion_tokens"):
                llm_kwargs["max_completion_tokens"] = max_completion_tokens
        llm = openai.LLM(**llm_kwargs)
        if supports_custom_temperature and "temperature" not in llm_kwargs and hasattr(llm, "temperature"):
            try:
                setattr(llm, "temperature", effective_llm_temperature)
            except Exception:
                pass

    # Build system prompt - DO NOT MODIFY based on welcome settings
    welcome_type = config.get("welcome_message_type", "user_speaks_first")
    welcome_msg = apply_runtime_template(config.get("welcome_message", ""), runtime_vars)
    welcome_message_mode = resolve_welcome_message_mode(config.get("custom_params"))
    welcome_type_normalized = str(welcome_type or "user_speaks_first").strip().lower()
    should_agent_greet = welcome_type_normalized in {
        "agent_greets",
        "agent_greets_first",
        "agent_speaks_first",
    }
    logger.info(f"Welcome type: {welcome_type}, Welcome msg: {welcome_msg}, Direction: {direction}")
    sys_prompt, functions = build_effective_runtime_prompt(config, functions, runtime_vars)

    is_phone_call = bool(
        from_number
        or to_number
        or runtime_vars.get("from_number")
        or runtime_vars.get("to_number")
        or str(call_id or "").startswith(("inbound_", "outbound_"))
        or direction == "inbound"
    )
    session_kwargs: Dict[str, Any] = {
        "llm": llm,
        "min_endpointing_delay": max(0.05, SESSION_MIN_ENDPOINTING_DELAY),
        "max_endpointing_delay": max(max(0.05, SESSION_MIN_ENDPOINTING_DELAY), SESSION_MAX_ENDPOINTING_DELAY),
        "preemptive_generation": SESSION_PREEMPTIVE_GENERATION,
    }
    if tts_engine is not None:
        session_kwargs["tts"] = tts_engine
    stt_model = "xai-voice-agent-native" if use_unified_realtime_audio else "openai-realtime-native"
    if not use_realtime_llm:
        stt_language = resolve_stt_language(agent_lang)
        # Use Nova-2 for multilingual (language=multi) because it has better code-switching
        # Use Nova-3 for specific languages (faster, more accurate)
        if stt_language == "multi":
            stt_model = "nova-2"
        else:
            stt_model = "nova-3"
        stt_kwargs: Dict[str, Any] = {
            "language": stt_language,
            "model": stt_model,
        }
        if _callable_supports_kwarg(deepgram.STT, "interim_results"):
            stt_kwargs["interim_results"] = True
        if _callable_supports_kwarg(deepgram.STT, "smart_format"):
            stt_kwargs["smart_format"] = True
        if _callable_supports_kwarg(deepgram.STT, "punctuate"):
            stt_kwargs["punctuate"] = True
        if _callable_supports_kwarg(deepgram.STT, "endpointing_ms"):
            raw_endpointing = STT_ENDPOINTING_PHONE_MS if is_phone_call else STT_ENDPOINTING_WEB_MS
            stt_kwargs["endpointing_ms"] = _coerce_setting_int(raw_endpointing, default=120 if is_phone_call else 80, min_value=25, max_value=1500)
        if _callable_supports_kwarg(deepgram.STT, "no_delay"):
            stt_kwargs["no_delay"] = True
        logger.info("STT config: model=%s language=%s endpointing_ms=%s", stt_model, stt_kwargs.get("language"), stt_kwargs.get("endpointing_ms"))
        session_kwargs["stt"] = deepgram.STT(**stt_kwargs)

    # ALWAYS provide VAD to the session, even for realtime unified audio, 
    # as AgentSession requires it to monitor the room's audio input path.
    session_kwargs["vad"] = ctx.proc.userdata["vad"]

    if use_realtime_llm:
        if use_unified_realtime_audio:
            logger.info("Realtime voice path enabled: using xAI unified voice realtime for STT, generation, and speech output")
        else:
            logger.info("Realtime voice path enabled: using OpenAI Realtime for speech understanding and turn detection")

    session = AgentSession(**session_kwargs)
    agent = create_dynamic_agent_class(
        functions_config=functions,
        base_instructions=sys_prompt,
        current_room=ctx.room,
        call_id=call_id,
        session=session,
        agent_id=agent_id,
        agent_label=config.get("name"),
        is_phone_call=is_phone_call,
        runtime_vars=runtime_vars,
        vad_instance=ctx.proc.userdata["vad"],
        llm_engine=llm,
        tts_engine=tts_engine,
        stt_engine=session_kwargs.get("stt"),
    )

    # Track the active speech-input path for usage and post-call diagnostics.
    usage.stt_model = stt_model

    # Track transcripts using session events
    transcript_tracker = TranscriptCollector(call_id, usage, runtime_llm_model)
    conversation_event_seen = False
    last_activity_ts = time.time()
    silence_prompt_count = 0
    silence_prompt_lock = asyncio.Lock()
    initial_greeting_in_progress = False
    has_user_spoken = False
    greeting_sent_ts: Optional[float] = None
    pre_user_checkin_sent = False
    transcript_monitor_task: Optional[asyncio.Task] = None
    silence_watchdog_task: Optional[asyncio.Task] = None
    initial_greeting_sent = False
    initial_greeting_lock = asyncio.Lock()
    initial_greeting_task: Optional[asyncio.Task] = None



    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        nonlocal conversation_event_seen, last_activity_ts, has_user_spoken
        try:
            conversation_event_seen = True
            item = event.item
            if not item:
                return
            role = TranscriptCollector._resolve_message_attr(item, 'role') or ''
            content = TranscriptCollector._extract_message_text(item)
            if not content or role == 'system':
                return
                
            if role == 'user':
                has_user_spoken = True
                last_activity_ts = time.time()
                word_count = max(1, len(content.split()))
                est_duration = max(700, int((word_count / 2.5) * 1000))
                usage.add_stt_duration(est_duration)
                usage.add_llm_usage(tokens_in=max(1, len(content) // 4), model=runtime_llm_model)
                usage.add_transcript("user", content)
                asyncio.ensure_future(send_transcript_to_api(call_id, "user", content))
                logger.info(f"[transcript] User: {content[:60]}...")
            elif role == 'assistant':
                last_activity_ts = time.time()
                usage.add_tts_characters(len(content))
                usage.add_llm_usage(tokens_out=max(1, len(content) // 4), model=runtime_llm_model)
                usage.add_transcript("agent", content)
                asyncio.ensure_future(send_transcript_to_api(call_id, "agent", content))
                logger.info(f"[transcript] Agent: {content[:60]}...")
                if hasattr(agent, "_schedule_spoken_transfer_fallback"):
                    agent._schedule_spoken_transfer_fallback(content)

                if getattr(agent, "_pending_end_call_after_speech", False) and not getattr(agent, "_end_call_handoff_started", False):
                    setattr(agent, "_pending_end_call_after_speech", False)
                    setattr(agent, "_end_call_handoff_started", True)
                    word_count = max(2, len(content.split()))
                    dynamic_delay = max(0.8, min(8.0, word_count / 2.4))

                    async def _complete_end_after_speech():
                        try:
                            end_handoff_result = await run_end_call_handoff(ctx.room, delay_sec=dynamic_delay)
                            logger.info(f"end_call post-speech handoff result: {end_handoff_result}")
                        except Exception as end_handoff_exc:
                            logger.error(f"end_call post-speech handoff failed: {end_handoff_exc}")

                    asyncio.create_task(_complete_end_after_speech())
        except Exception as e:
            logger.error(f"Error in conversation_item_added: {e}")

    @session.on("function_calls_collected")
    def on_function_calls_collected(event):
        try:
            for fc in event.function_calls:
                tool_name = _canonical_tool_name(fc.function.name)
                if hasattr(agent, "_mark_tool_call_observed"):
                    agent._mark_tool_call_observed(tool_name)
                args_str = str(fc.function.arguments)
                msg = f"[Calling tool: {tool_name}] {args_str}"
                usage.add_transcript("tool_call", msg)
                asyncio.ensure_future(send_transcript_to_api(call_id, "tool_call", msg))
                logger.info(f"[transcript] Tool call: {tool_name}")
        except Exception as e:
            logger.error(f"Error in function_calls_collected: {e}")

    @session.on("function_calls_finished")
    def on_function_calls_finished(event):
        try:
            for fc in event.function_calls:
                tool_name = _canonical_tool_name(fc.function.name)
                output = fc.output if fc.output else str(fc.exception) if fc.exception else "no output"
                msg = f"[Tool response: {tool_name}] {output}"
                usage.add_transcript("tool_response", msg)
                asyncio.ensure_future(send_transcript_to_api(call_id, "tool_response", msg))
                logger.info(f"[transcript] Tool response: {tool_name}")
        except Exception as e:
            logger.error(f"Error in function_calls_finished: {e}")

    chat_reply_lock = asyncio.Lock()
    recent_chat_payloads: Dict[str, float] = {}

    async def _handle_chat_user_input(message_text: str):
        nonlocal last_activity_ts
        text = (message_text or "").strip()
        if not text:
            return
        try:
            last_activity_ts = time.time()
            async with chat_reply_lock:
                logger.info(f"[chat] user message received: {text[:120]}")
                await asyncio.wait_for(
                    session.generate_reply(user_input=text, input_modality="text"),
                    timeout=CHAT_REPLY_TIMEOUT_SEC,
                )
        except Exception as chat_exc:
            logger.error(f"[chat] generate_reply failed: {chat_exc}")
            try:
                await ctx.room.local_participant.publish_data(
                    json.dumps({"type": "error", "error": f"chat_reply_failed: {chat_exc}"}),
                    topic="room",
                )
            except Exception:
                pass

    def _extract_data_received_parts(event_args):
        payload = b""
        participant = None
        topic = ""

        if len(event_args) >= 3:
            payload, participant, topic = event_args[0], event_args[1], event_args[2]
        elif len(event_args) == 2:
            payload, participant = event_args[0], event_args[1]
            topic = getattr(payload, "topic", "") or ""
        elif len(event_args) == 1:
            evt = event_args[0]
            payload = getattr(evt, "data", evt)
            topic = getattr(evt, "topic", "") or ""
            participant = getattr(evt, "participant", None)

            if participant is None:
                participant_identity = getattr(evt, "participant_identity", "") or ""
                if participant_identity:
                    if participant_identity == getattr(ctx.room.local_participant, "identity", ""):
                        participant = ctx.room.local_participant
                    else:
                        participant = ctx.room.remote_participants.get(participant_identity)

        return payload, participant, topic

    def _decode_payload(payload_obj) -> str:
        if payload_obj is None:
            return ""
        if isinstance(payload_obj, str):
            return payload_obj
        if isinstance(payload_obj, memoryview):
            return payload_obj.tobytes().decode("utf-8", errors="ignore")
        if isinstance(payload_obj, (bytes, bytearray)):
            return bytes(payload_obj).decode("utf-8", errors="ignore")

        nested = getattr(payload_obj, "data", None)
        if nested is not None and nested is not payload_obj:
            return _decode_payload(nested)

        return str(payload_obj)

    @ctx.room.on("data_received")
    def on_data_received(*event_args):
        try:
            payload, participant, topic = _extract_data_received_parts(event_args)

            if topic == "lk.chat":
                try:
                    sender_identity = getattr(participant, "identity", "") if participant else ""
                    if sender_identity and "agent" in sender_identity.lower():
                        return

                    decoded = _decode_payload(payload)
                    message_text = ""
                    try:
                        payload_json = json.loads(decoded)
                        if isinstance(payload_json, dict):
                            message_text = (
                                payload_json.get("text")
                                or payload_json.get("message")
                                or payload_json.get("content")
                                or ""
                            )
                        elif isinstance(payload_json, str):
                            message_text = payload_json
                    except Exception:
                        message_text = decoded

                    if message_text.strip():
                        sender_identity = getattr(participant, "identity", "") if participant else ""
                        dedupe_key = f"{sender_identity}:{message_text.strip()}"
                        now_ts = time.time()
                        # Keep small in-memory dedupe window to avoid accidental double processing
                        # from duplicate data events in unstable network conditions.
                        for key, ts in list(recent_chat_payloads.items()):
                            if now_ts - ts > 5:
                                recent_chat_payloads.pop(key, None)
                        last_seen = recent_chat_payloads.get(dedupe_key)
                        if last_seen and (now_ts - last_seen) < 1.5:
                            logger.debug("[chat] duplicate message dropped")
                            return
                        recent_chat_payloads[dedupe_key] = now_ts
                        asyncio.ensure_future(_handle_chat_user_input(message_text))
                except Exception as chat_parse_exc:
                    logger.debug(f"[chat] data parse error: {chat_parse_exc}")
                return

            if topic == "room":
                data = json.loads(_decode_payload(payload))
                if data.get("type") == "tool_call":
                    tool_name = _canonical_tool_name(data.get("tool_name", "unknown"))
                    args = data.get("args", {})
                    msg = f"[Tool invoked: {tool_name}] {json.dumps(args)}"
                    usage.add_transcript("tool_invocation", msg)
                    asyncio.ensure_future(send_transcript_to_api(call_id, "tool_invocation", msg))
                    logger.info(f"[transcript] Tool invoked: {tool_name}")
                elif data.get("type") == "tool_response":
                    tool_name = _canonical_tool_name(data.get("tool_name", "unknown"))
                    response = data.get("response", {})
                    msg = f"[Tool result: {tool_name}] {json.dumps(response)}"
                    usage.add_transcript("tool_result", msg)
                    asyncio.ensure_future(send_transcript_to_api(call_id, "tool_result", msg))
                    logger.info(f"[transcript] Tool result: {tool_name}")
        except Exception as e:
            logger.debug(f"Error processing room data: {e}")

    # Event setup BEFORE session start
    shutdown = asyncio.Event()

    async def _emit_initial_greeting_once(source: str):
        nonlocal initial_greeting_in_progress, greeting_sent_ts, last_activity_ts, initial_greeting_sent
        if not should_agent_greet or shutdown.is_set():
            return
        wait_deadline = time.time() + max(1.0, INITIAL_GREETING_WAIT_FOR_PARTICIPANT_SEC)
        while (
            not shutdown.is_set()
            and len(ctx.room.remote_participants) == 0
            and time.time() < wait_deadline
        ):
            await asyncio.sleep(0.1)
        if shutdown.is_set():
            return
        if len(ctx.room.remote_participants) == 0:
            logger.warning(
                "Skipping initial greeting (%s): no remote participant within %.1fs",
                source,
                INITIAL_GREETING_WAIT_FOR_PARTICIPANT_SEC,
            )
            return
        try:
            async with initial_greeting_lock:
                if initial_greeting_sent or shutdown.is_set():
                    return
                initial_greeting_sent = True
                initial_greeting_in_progress = True

                if tts_engine is None:  # realtime path (xAI / OpenAI realtime)
                    pass

                if welcome_message_mode == "custom" and welcome_msg.strip():
                    greeting_text = welcome_msg.strip()
                    if tts_engine is None:
                        logger.info("Sending custom greeting via generate_reply (no TTS engine, realtime path) (%s)", source)
                        asyncio.ensure_future(session.generate_reply(
                            allow_interruptions=True,
                        ))
                    else:
                        logger.info("Sending custom greeting via direct TTS (%s)", source)
                        session.say(greeting_text, add_to_chat_ctx=True, allow_interruptions=True)
                else:
                    if tts_engine is None:
                        logger.info("Triggering initial greeting via generate_reply (audio-listening mode) (%s)", source)
                        # Short sleep to ensure WebSocket session is fully established
                        await asyncio.sleep(0.5)
                        asyncio.ensure_future(session.generate_reply(
                            allow_interruptions=True,
                            input_modality="audio",
                        ))
                    else:
                        greeting_text = build_safe_auto_greeting(agent_lang, sys_prompt)
                        logger.info("Sending dynamic greeting via direct TTS (%s)", source)
                        session.say(greeting_text, add_to_chat_ctx=True, allow_interruptions=True)

                logger.info("Greeting queued successfully (%s)", source)
                greeting_sent_ts = time.time()
                last_activity_ts = greeting_sent_ts
        except Exception as greeting_err:
            logger.error(f"Failed to send greeting ({source}): {greeting_err}")
        finally:
            initial_greeting_in_progress = False

    async def _run_transcript_monitor_if_needed():
        await asyncio.sleep(8)
        if shutdown.is_set():
            return
        if conversation_event_seen:
            logger.info("Conversation events active; transcript fallback monitor not required")
            return
        logger.warning("conversation_item_added not observed; starting transcript fallback monitor")
        await transcript_tracker.monitor_chat_context(session)

    async def _silence_reprompt_watchdog():
        nonlocal last_activity_ts, silence_prompt_count, initial_greeting_in_progress, has_user_spoken, greeting_sent_ts, pre_user_checkin_sent
        if SILENCE_REPROMPT_SEC <= 0:
            return
        while not shutdown.is_set():
            await asyncio.sleep(1.0)
            if silence_prompt_count >= SILENCE_REPROMPT_MAX_PER_CALL:
                continue
            if initial_greeting_in_progress:
                continue
            if len(ctx.room.remote_participants) == 0:
                continue
            if not has_user_spoken:
                # Avoid a duplicated "opening line" while call is still ringing/answering.
                # Send at most one light check-in if caller stays silent well after greeting.
                if greeting_sent_ts is None or pre_user_checkin_sent:
                    continue
                pre_user_wait_sec = max(SILENCE_REPROMPT_SEC + 15.0, 35.0)
                if (time.time() - greeting_sent_ts) < pre_user_wait_sec:
                    continue
                try:
                    async with silence_prompt_lock:
                        if pre_user_checkin_sent or shutdown.is_set():
                            continue
                        pre_user_checkin_sent = True
                        logger.info("Pre-user silence check-in triggered")
                        await asyncio.wait_for(
                            session.generate_reply(
                                instructions=(
                                    "The caller has not responded yet. In one short sentence, "
                                    "politely check if they can hear you and invite a brief reply."
                                )
                            ),
                            timeout=CHAT_REPLY_TIMEOUT_SEC,
                        )
                        last_activity_ts = time.time()
                except Exception as pre_user_silence_err:
                    logger.debug(f"Pre-user silence check-in skipped due runtime error: {pre_user_silence_err}")
                continue
            idle_for = time.time() - last_activity_ts
            if idle_for < SILENCE_REPROMPT_SEC:
                continue
            try:
                async with silence_prompt_lock:
                    idle_for = time.time() - last_activity_ts
                    if idle_for < SILENCE_REPROMPT_SEC:
                        continue
                    logger.info("Silence reprompt triggered after %.1fs idle", idle_for)
                    await asyncio.wait_for(
                        session.generate_reply(
                            instructions=(
                                "The caller has been silent for a while. Re-engage politely in one short sentence, "
                                "rephrasing your most recent question in a natural way. Keep the same topic."
                            )
                        ),
                        timeout=CHAT_REPLY_TIMEOUT_SEC,
                    )
                    silence_prompt_count += 1
                    last_activity_ts = time.time()
            except Exception as silence_err:
                logger.debug(f"Silence reprompt skipped due runtime error: {silence_err}")
    
    @ctx.room.on("disconnected")
    def on_disconnected():
        logger.info("Room disconnected")
        shutdown.set()
    
    disconnect_grace_task: Optional[asyncio.Task] = None

    def _cancel_disconnect_grace():
        nonlocal disconnect_grace_task
        if disconnect_grace_task and not disconnect_grace_task.done():
            disconnect_grace_task.cancel()
        disconnect_grace_task = None

    async def _delayed_shutdown_if_empty():
        await asyncio.sleep(DISCONNECT_GRACE_SEC)
        try:
            # If a participant rejoined in grace period, keep session alive.
            if len(ctx.room.remote_participants) > 0:
                logger.info("[stability] participant rejoined during grace period, keeping session alive")
                return
            logger.info(f"[stability] no participants after {DISCONNECT_GRACE_SEC}s grace, shutting down")
            shutdown.set()
        except Exception as e:
            logger.debug(f"[stability] delayed shutdown check failed: {e}")
            shutdown.set()

    @ctx.room.on("participant_connected")
    def on_participant_joined(participant):
        nonlocal last_activity_ts, initial_greeting_task
        logger.info(f"Participant joined: {participant.identity}")
        last_activity_ts = time.time()
        _cancel_disconnect_grace()
        if should_agent_greet and not initial_greeting_sent:
            if initial_greeting_task is None or initial_greeting_task.done():
                initial_greeting_task = asyncio.create_task(
                    _emit_initial_greeting_once("participant_connected")
                )

    @ctx.room.on("participant_disconnected")
    def on_participant_left(participant):
        nonlocal disconnect_grace_task
        logger.info(f"Participant left: {participant.identity}")
        _cancel_disconnect_grace()
        disconnect_grace_task = asyncio.create_task(_delayed_shutdown_if_empty())
    
    try:
        await session.start(
            agent=agent,
            room=ctx.room,
            room_options=RoomOptions(close_on_disconnect=False),
        )
        logger.info("Session started successfully")
        transcript_monitor_task = asyncio.create_task(_run_transcript_monitor_if_needed())
        silence_watchdog_task = asyncio.create_task(_silence_reprompt_watchdog())
        if should_agent_greet:
            initial_greeting_task = asyncio.create_task(
                _emit_initial_greeting_once("session_start")
            )

        # Wait for shutdown signal from SDK
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=MAX_CALL_DURATION)
        except asyncio.TimeoutError:
            logger.warning(f"Call timed out after {MAX_CALL_DURATION}s")

    except Exception as e:
        logger.error(f"Session error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if disconnect_grace_task and not disconnect_grace_task.done():
            disconnect_grace_task.cancel()
        shutdown.set()
        transcript_tracker.stop()
        for task in (transcript_monitor_task, silence_watchdog_task, initial_greeting_task):
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        # Wait briefly to ensure all metrics are collected
        await asyncio.sleep(1)
        # ALWAYS send usage, even on crash/disconnect
        logger.info(f"Sending final usage for {call_id}: LLM={usage.llm_tokens_in}/{usage.llm_tokens_out}, STT={usage.stt_duration_ms}ms, TTS={usage.tts_characters}chars")
        if call_id:
            await backfill_missing_transcripts(call_id, usage)
            await send_usage_to_api(call_id, usage)
            await end_call_record(call_id)
        _active_call_id = None
        _active_usage = None

    logger.info(f"Session ended - Duration: {usage.get_call_duration()}s")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        agent_name=DEFAULT_WORKER_DISPATCH_NAME
    ))
