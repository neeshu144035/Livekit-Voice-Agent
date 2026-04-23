import os
import re
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-retell")

DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://host.docker.internal:8000").rstrip("/")
DEFAULT_WORKER_DISPATCH_NAME = (os.getenv("LIVEKIT_WORKER_AGENT_NAME", "sarah") or "sarah").strip().lower()
MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "1800"))
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"
DEFAULT_AGENT_LLM_TEMPERATURE = 0.2
DEFAULT_AGENT_VOICE_SPEED = 1.0
MIN_AGENT_LLM_TEMPERATURE = 0.0
MAX_AGENT_LLM_TEMPERATURE = 1.5
MIN_AGENT_VOICE_SPEED = 0.8
MAX_AGENT_VOICE_SPEED = 1.2
TRANSFER_HANDOFF_DELAY_SEC = float(os.getenv("TRANSFER_HANDOFF_DELAY_SEC", "2.5"))
END_CALL_DISCONNECT_DELAY_SEC = float(os.getenv("END_CALL_DISCONNECT_DELAY_SEC", "1.0"))
DISCONNECT_GRACE_SEC = float(os.getenv("DISCONNECT_GRACE_SEC", "20"))
CHAT_REPLY_TIMEOUT_SEC = float(os.getenv("CHAT_REPLY_TIMEOUT_SEC", "40"))
SILENCE_REPROMPT_SEC = float(os.getenv("SILENCE_REPROMPT_SEC", "25"))
SILENCE_REPROMPT_MAX_PER_CALL = int(os.getenv("SILENCE_REPROMPT_MAX_PER_CALL", "6"))
STT_ENDPOINTING_PHONE_MS = int(os.getenv("STT_ENDPOINTING_PHONE_MS", "40"))
STT_ENDPOINTING_WEB_MS = int(os.getenv("STT_ENDPOINTING_WEB_MS", "40"))
SESSION_MIN_ENDPOINTING_DELAY = float(os.getenv("SESSION_MIN_ENDPOINTING_DELAY", "0.02"))
SESSION_MAX_ENDPOINTING_DELAY = float(os.getenv("SESSION_MAX_ENDPOINTING_DELAY", "0.05"))
SESSION_PREEMPTIVE_GENERATION = os.getenv("SESSION_PREEMPTIVE_GENERATION", "1").strip().lower() in {"1", "true", "yes", "on"}
VAD_MIN_SPEECH_DURATION = float(os.getenv("VAD_MIN_SPEECH_DURATION", "0.010"))
VAD_MIN_SILENCE_DURATION = float(os.getenv("VAD_MIN_SILENCE_DURATION", "0.030"))
VAD_PREFIX_PADDING_DURATION = float(os.getenv("VAD_PREFIX_PADDING_DURATION", "0.08"))
ELEVENLABS_STREAMING_LATENCY = int(os.getenv("ELEVENLABS_STREAMING_LATENCY", "0"))
OPENAI_REALTIME_PREFIX_PADDING_MS = int(os.getenv("OPENAI_REALTIME_PREFIX_PADDING_MS", "120"))
OPENAI_REALTIME_SILENCE_DURATION_MS = int(os.getenv("OPENAI_REALTIME_SILENCE_DURATION_MS", "150"))
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

_dashboard_api_client: Optional[Any] = None

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
