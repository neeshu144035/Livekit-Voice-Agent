import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Default LiveKit settings
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://oyik.info/rtc")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "ws://localhost:7880")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

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

VALID_LLM_MODELS = [
    'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k', 'kimi-k2.5',
    'kimi-k2-thinking', 'kimi-k2-instruct', 'moonlight-16b-a3b', 'gpt-4',
    'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4o', 'gpt-4o-mini',
    'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-5.4', 'gpt-5.4-pro', 'gpt-5.2',
    'gpt-5.2-pro', 'gpt-5.1', 'gpt-5', 'gpt-5-pro', 'gpt-5-mini', 'gpt-5-nano',
    'o1', 'o1-pro', 'o3', 'o3-mini', 'o4-mini',
]

VALID_VOICES = [
    'jessica', 'mark', 'sarah', 'michael', 'emma', 'james',
    'aura-asteria-en', 'aura-luna-en', 'aura-hera-en',
    'aura-orion-en', 'aura-perseus-en', 'aura-zeus-en',
]

VALID_LANGUAGES = [
    'en', 'en-US', 'en-GB', 'en-AU', 'en-IN', 'es', 'fr', 'de', 'it', 'hi', 'hi-IN', 'ml', 'ml-IN', 'multi'
]

VALID_TTS_PROVIDERS = ["deepgram", "elevenlabs"]
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"
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
    "sarah": "aura-luna-en",
    "emma": "aura-hera-en",
    "mark": "aura-orion-en",
    "michael": "aura-perseus-en",
    "james": "aura-zeus-en",
}
