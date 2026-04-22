import os
import json
import logging
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero, elevenlabs
from livekit.agents import llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
AGENT_WORKER_NAME = os.getenv("AGENT_WORKER_NAME", "voice-agent")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "") or os.getenv("ELEVENLABS_API_KEY", "")


async def get_openai_usage(start_date: str, end_date: str) -> dict:
    """Get actual OpenAI usage for a date range"""
    try:
        if not OPENAI_API_KEY:
            return {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.openai.com/v1/usage",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "aggregation": "daily",
                },
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                # Get today's usage
                today = datetime.now().strftime("%Y-%m-%d")
                for day_data in data.get("data", []):
                    if day_data.get("date") == today:
                        return {
                            "prompt_tokens": day_data.get("line_items", [{}])[0].get("prompt_tokens", 0) if day_data.get("line_items") else 0,
                            "completion_tokens": day_data.get("line_items", [{}])[0].get("completion_tokens", 0) if day_data.get("line_items") else 0,
                            "total_tokens": day_data.get("line_items", [{}])[0].get("total_tokens", 0) if day_data.get("line_items") else 0,
                        }
            logger.warning(f"OpenAI usage API error: {resp.status_code}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching OpenAI usage: {e}")
        return {}


async def get_deepgram_usage() -> dict:
    """Get actual Deepgram usage"""
    try:
        if not DEEPGRAM_API_KEY:
            return {}
        
        # Get usage for today
        today = datetime.now().strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.deepgram.com/v1/projects/usage",
                params={
                    "start": today,
                    "end": today,
                },
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                # Sum up all usage for today
                total_minutes = 0
                for result in data.get("results", []):
                    total_minutes += result.get("minutes", 0)
                return {"total_minutes": total_minutes}
            logger.warning(f"Deepgram usage API error: {resp.status_code}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching Deepgram usage: {e}")
        return {}
MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "1800"))  # 30 min default
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"

VOICE_MAP = {
    'jessica': 'aura-asteria-en',
    'mark': 'aura-orion-en',
    'sarah': 'aura-luna-en',
    'michael': 'aura-perseus-en',
    'emma': 'aura-hera-en',
    'james': 'aura-zeus-en',
    'aura-asteria-en': 'aura-asteria-en',
    'aura-orion-en': 'aura-orion-en',
    'aura-luna-en': 'aura-luna-en',
    'aura-perseus-en': 'aura-perseus-en',
    'aura-hera-en': 'aura-hera-en',
    'aura-zeus-en': 'aura-zeus-en',
}


def normalize_tts_provider(value: str) -> str:
    provider = str(value or "").strip().lower()
    if provider not in ("deepgram", "elevenlabs"):
        return DEFAULT_TTS_PROVIDER
    return provider


def get_elevenlabs_api_key() -> str:
    return (os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY") or "").strip()


# ==================== Usage Tracking ====================

class UsageTracker:
    """Track LLM tokens, STT duration, TTS characters for cost calculation"""
    def __init__(self):
        self.llm_tokens_in = 0
        self.llm_tokens_out = 0
        self.llm_model = ""
        self.stt_duration_ms = 0
        self.tts_characters = 0
        self.transcript_entries = []
        self.call_start_time = time.time()
    
    def add_llm_usage(self, tokens_in: int = 0, tokens_out: int = 0, model: str = ""):
        self.llm_tokens_in += tokens_in
        self.llm_tokens_out += tokens_out
        if model:
            self.llm_model = model
    
    def add_stt_duration(self, duration_ms: int):
        self.stt_duration_ms += duration_ms
    
    def add_tts_characters(self, chars: int):
        self.tts_characters += chars
    
    def add_transcript(self, role: str, content: str):
        self.transcript_entries.append({"role": role, "content": content})
    
    def get_transcript_summary(self) -> str:
        if not self.transcript_entries:
            return ""
        lines = []
        for entry in self.transcript_entries[-10:]:
            prefix = "Agent" if entry["role"] == "agent" else "User"
            text = entry["content"][:100]
            lines.append(f"{prefix}: {text}")
        return "\n".join(lines)
    
    def get_call_duration(self) -> int:
        return int(time.time() - self.call_start_time)


# ==================== API Helpers ====================

async def send_transcript_to_api(call_id: str, role: str, content: str,
                                   is_final: bool = True, stt_ms: int = None,
                                   llm_ms: int = None, tts_ms: int = None):
    """Send transcript entry to the backend API."""
    url = f"{DASHBOARD_API_URL}/api/calls/{call_id}/transcript"
    payload = {
        "role": role,
        "content": content,
        "is_final": is_final,
    }
    if stt_ms:
        payload["stt_latency_ms"] = stt_ms
    if llm_ms:
        payload["llm_latency_ms"] = llm_ms
    if tts_ms:
        payload["tts_latency_ms"] = tts_ms
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error sending transcript: {e}")


async def send_usage_to_api(call_id: str, tracker: UsageTracker):
    """Send accumulated usage metrics to backend with actual API usage"""
    try:
        # Get actual usage from API providers
        # Note: We now capture real per-call token usage from the LLM response events
        # instead of using the OpenAI daily usage API which only returns aggregate totals
        openai_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        deepgram_usage = await get_deepgram_usage()
        
        payload = {
            "llm_tokens_in": tracker.llm_tokens_in,
            "llm_tokens_out": tracker.llm_tokens_out,
            "llm_model_used": tracker.llm_model,
            "stt_duration_ms": tracker.stt_duration_ms,
            "tts_characters": tracker.tts_characters,
            "transcript_summary": tracker.get_transcript_summary(),
            "actual_duration_seconds": tracker.get_call_duration(),
            # Actual usage from APIs - now captured in real-time from LLM responses
            "actual_llm_tokens_in": tracker.llm_tokens_in,  # Real per-call tokens
            "actual_llm_tokens_out": tracker.llm_tokens_out,  # Real per-call tokens
            "actual_stt_minutes": deepgram_usage.get("total_minutes", 0),
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
                json=payload
            )
            logger.info(f"[{AGENT_WORKER_NAME}] Sent usage for {call_id}")
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error sending usage to API: {e}")


async def create_call_record(room_name: str, agent_id: int, direction: str = "web",
                              call_type: str = "web",
                              from_number: str = None, to_number: str = None) -> str:
    """Create a call record in the backend and return call_id"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/create-from-agent",
                json={
                    "room_name": room_name,
                    "agent_id": agent_id,
                    "direction": direction,
                    "call_type": call_type,
                    "from_number": from_number,
                    "to_number": to_number,
                }
            )
            data = resp.json()
            return data.get("call_id", "")
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error creating call record: {e}")
        return ""


async def fetch_agent_by_phone(phone_number: str) -> dict:
    """Fetch agent config by phone number (for inbound calls)"""
    url = f"{DASHBOARD_API_URL}/api/agents/by-phone/{phone_number}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error fetching agent by phone {phone_number}: {e}")
    return None


def prewarm(proc: JobProcess):
    """Pre-warm: Load models at worker startup to reduce cold start latency."""
    from livekit.plugins import deepgram
    
    logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming: Loading VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming complete: VAD loaded")
    
    # Pre-warm TTS to reduce agent speaks first latency
    try:
        logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming: Loading TTS model...")
        tts_for_prewarm = deepgram.TTS(model="aura-asteria-en")
        proc.userdata["tts_deepgram"] = tts_for_prewarm
        logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming complete: TTS loaded")
    except Exception as e:
        logger.warning(f"TTS prewarm failed: {e}")
    
    # Pre-warm LLM to reduce first-call latency
    try:
        logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming: Loading LLM...")
        llm_for_prewarm = openai.LLM(model="gpt-4o-mini")
        # Do a dummy chat to warm up
        import asyncio
        async def warm_llm():
            try:
                await llm_for_prewarm.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    temperature=0
                )
            except Exception as e:
                logger.warning(f"LLM warmup chat failed: {e}")
        asyncio.run(warm_llm())
        proc.userdata["llm_warmed"] = True
        logger.info(f"[{AGENT_WORKER_NAME}] Pre-warming complete: LLM loaded and warmed")
    except Exception as e:
        logger.warning(f"[{AGENT_WORKER_NAME}] LLM pre-warm failed: {e}")


async def fetch_agent_config(agent_id: int) -> dict:
    """Fetch agent configuration from dashboard API."""
    url = f"{DASHBOARD_API_URL}/api/agents/{agent_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            config = resp.json()
            logger.info(f"[{AGENT_WORKER_NAME}] Loaded config for agent {agent_id}: {config.get('name')}")
            return config
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error fetching agent {agent_id} config: {e}")
        return {
            "name": "LiveKit Assistant",
            "system_prompt": "You are a helpful AI voice assistant.",
            "llm_model": "gpt-4o-mini",
            "voice_id": "aura-asteria-en",
            "voice_speed": 1.0,
            "stt_language": "en",
            "temperature": 0.7,
            "max_tokens": 150,
            "enable_interruptions": True,
            "silence_timeout_ms": 1500,
            "welcome_message": "Hello, how can I help you today?"
        }


# ==================== Fetch Functions ====================

async def fetch_functions(agent_id: int) -> list:
    """Fetch custom functions and built-in functions for an agent"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch custom functions
            resp = await client.get(f"{DASHBOARD_API_URL}/api/agents/{agent_id}/functions")
            custom_funcs = resp.json() if resp.status_code == 200 else []
            
            # Fetch built-in functions
            resp2 = await client.get(f"{DASHBOARD_API_URL}/api/agents/{agent_id}/builtin-functions")
            builtin_funcs = resp2.json() if resp2.status_code == 200 else []
            
            return custom_funcs + builtin_funcs
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error fetching functions: {e}")
        return []


async def execute_builtin_action(call_id: str, action: str, parameters: dict):
    """Execute a built-in action (end_call, transfer_call)"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/builtin-action",
                json={"action": action, "parameters": parameters}
            )
            if resp.status_code == 200:
                logger.info(f"[{AGENT_WORKER_NAME}] Executed {action}: {resp.json()}")
                return resp.json()
            else:
                logger.error(f"[{AGENT_WORKER_NAME}] Failed to execute {action}: {resp.status_code}")
                return None
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error executing {action}: {e}")
        return None


# ==================== Detect Inbound SIP Participants ====================

def detect_sip_participant(room):
    """Check if there's a SIP participant in the room (indicates inbound call)"""
    for participant in room.remote_participants.values():
        identity = participant.identity or ""
        if identity.startswith("sip_") or "sip" in identity.lower():
            return participant
    return None


def get_sip_phone_numbers(participant):
    """Extract phone numbers from SIP participant attributes"""
    from_number = None
    to_number = None
    if hasattr(participant, 'attributes') and participant.attributes:
        attrs = participant.attributes
        from_number = attrs.get("sip.callerNumber") or attrs.get("sip.from", "")
        to_number = attrs.get("sip.calledNumber") or attrs.get("sip.to", "")
    return from_number, to_number


async def entrypoint(ctx: JobContext):
    """Main entrypoint for each voice agent session."""
    
    logger.info(f"[{AGENT_WORKER_NAME}] Starting job for room: {ctx.room.name}")
    
    usage = UsageTracker()
    agent_id = 1
    call_id = None
    direction = "outbound"
    from_number = None
    to_number = None
    
    # Parse room name to determine agent and call type
    try:
        room_name = ctx.room.name
        if room_name.startswith("call_"):
            # Web/outbound format: call_{agent_id}_{uuid}
            parts = room_name.split('_')
            if len(parts) >= 2:
                agent_id = int(parts[1]) if parts[1].isdigit() else 1
                if len(parts) >= 3:
                    call_id = '_'.join(parts[:3])
                direction = "outbound"
        elif room_name.startswith("call-") or room_name.startswith("sip-"):
            # Inbound SIP format: call-{uuid} or sip-{uuid}
            direction = "inbound"
            logger.info(f"[{AGENT_WORKER_NAME}] Inbound call detected: {room_name}")
        else:
            parts = room_name.split('_')
            if len(parts) > 1 and parts[1].isdigit():
                agent_id = int(parts[1])
    except (ValueError, IndexError):
        pass
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"[{AGENT_WORKER_NAME}] Connected to room: {ctx.room.name}")
    
    # For inbound calls, detect SIP participant and find correct agent
    if direction == "inbound":
        await asyncio.sleep(1)
        sip_participant = detect_sip_participant(ctx.room)
        if sip_participant:
            from_number, to_number = get_sip_phone_numbers(sip_participant)
            logger.info(f"[{AGENT_WORKER_NAME}] Inbound from: {from_number} to: {to_number}")
            
            if to_number:
                phone_agent = await fetch_agent_by_phone(to_number)
                if phone_agent:
                    agent_id = phone_agent.get("agent_id", agent_id)
                    logger.info(f"[{AGENT_WORKER_NAME}] Found agent {agent_id} for phone {to_number}")
    
    # Create call record if not already available
    if not call_id:
        call_id = await create_call_record(
            room_name=ctx.room.name,
            agent_id=agent_id,
            direction=direction,
            call_type="phone" if from_number or to_number else "web",
            from_number=from_number,
            to_number=to_number,
        )
        logger.info(f"[{AGENT_WORKER_NAME}] Call record created: {call_id}")
    
    config = await fetch_agent_config(agent_id)
    
    # Fetch functions for this agent
    functions = await fetch_functions(agent_id)
    
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    model_name = config.get("llm_model", "gpt-4o-mini")
    
    # Add function descriptions to system prompt
    if functions:
        func_descriptions = []
        for func in functions:
            func_name = func.get('name', '')
            func_desc = func.get('description', '')
            if func_name and func_desc:
                func_descriptions.append(f"- {func_name}: {func_desc}")
        
        if func_descriptions:
            system_prompt += "\n\nAvailable functions you can call:\n" + "\n".join(func_descriptions)
            system_prompt += "\n\nWhen a user wants to use a function, you should acknowledge and help them. For 'end_call', say goodbye before ending. For 'call_transfer', confirm the number and explain the transfer."
            logger.info(f"[{AGENT_WORKER_NAME}] Added {len(func_descriptions)} functions to system prompt")
    voice_id = config.get("voice_id") or config.get("voice", "jessica")
    custom_params = config.get("custom_params") or {}
    tts_provider = normalize_tts_provider(config.get("tts_provider") or custom_params.get("tts_provider") or DEFAULT_TTS_PROVIDER)
    eleven_model = config.get("tts_model") or custom_params.get("tts_model") or ""
    voice_speed = config.get("voice_speed", 1.0)
    stt_language = config.get("stt_language") or config.get("language", "en")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 150)
    enable_interruptions = config.get("enable_interruptions", True)
    silence_timeout_ms = config.get("silence_timeout_ms", 1500)
    welcome_message = config.get("welcome_message", "")
    welcome_message_type = config.get("welcome_message_type", "agent_speaks_first")
    
    # Determine LLM provider
    is_moonshot = "moonshot" in model_name.lower()
    if is_moonshot:
        api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = "https://api.moonshot.cn/v1"
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None
    
    tts_voice = VOICE_MAP.get(voice_id, 'aura-asteria-en')
    usage.llm_model = model_name
    
    llm_kwargs = {
        "api_key": api_key,
        "model": model_name,
    }
    if base_url:
        llm_kwargs["base_url"] = base_url
    
    llm_instance = openai.LLM(**llm_kwargs)
    
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_prompt,
    )
    
    vad = ctx.proc.userdata.get("vad", silero.VAD.load())
    
    # Create function context with built-in functions
    fnc_ctx = None
    if call_id:
        # Define function schemas for LLM
        fnc_ctx = {
            "end_call": {
                "description": "End the current call immediately. Use this when the user wants to hang up, says goodbye, or when the conversation is complete.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for ending the call"
                        }
                    }
                }
            },
            "call_transfer": {
                "description": "Transfer the current call to another phone number. Use this when the user needs to speak to a different department or person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Phone number to transfer to (E.164 format, e.g., +1234567890)"
                        }
                    },
                    "required": ["phone_number"]
                }
            }
        }
    
    # Provider-aware TTS. Do not silently fall back to Deepgram if ElevenLabs is selected.
    tts = None
    resolved_voice_id = voice_id
    resolved_tts_model = None

    if tts_provider == "elevenlabs":
        eleven_key = get_elevenlabs_api_key()
        if not eleven_key:
            raise RuntimeError("ElevenLabs selected but ELEVEN_API_KEY / ELEVENLABS_API_KEY is not set")
        
        resolved_tts_model = eleven_model or DEFAULT_ELEVENLABS_MODEL
        
        # Check for v3 models - they require HTTP instead of WebSocket
        model_lower = str(resolved_tts_model or "").strip().lower()
        is_v3 = "v3" in model_lower and model_lower not in ("eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_multilingual_v2")
        
        if is_v3:
            try:
                from elevenlabs import ElevenLabs
                from livekit.agents import tts as tts_module
                
                eleven_client = ElevenLabs(api_key=eleven_key)
                logger.info(f"[{AGENT_WORKER_NAME}] Using ElevenLabs {resolved_tts_model} via HTTP (v3)")
                
                class ElevenLabsV3HTTP(tts_module.TTS):
                    def __init__(self, voice_id: str, model: str, client):
                        self._voice_id = voice_id
                        self._model = model
                        self._client = client
                        super().__init__(
                            capabilities=tts_module.TTSCapabilities(streaming=False, aligned_transcript=False),
                            sample_rate=44100,
                            num_channels=1,
                        )
                    
                    @property
                    def identity(self):
                        return f"elevenlabs-v3:{self._voice_id}"
                    
                    def synthesize(self, text: str, conn_options=None):
                        return _ElevenLabsV3Stream(
                            tts=self,
                            input_text=text,
                            conn_options=conn_options or tts_module.DEFAULT_API_CONNECT_OPTIONS,
                        )
                
                class _ElevenLabsV3Stream(tts_module.ChunkedStream):
                    def __init__(self, *, tts: ElevenLabsV3HTTP, input_text: str, conn_options):
                        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
                        self._tts = tts
                    
                    async def _run(self, output_emitter: tts_module.AudioEmitter) -> None:
                        output_emitter.initialize(sample_rate=44100, num_channels=1, mime_type="audio/mpeg")
                        
                        audio_stream = self._tts._client.text_to_speech.stream(
                            voice_id=self._tts._voice_id,
                            text=self._input_text,
                            model_id=self._tts._model,
                            output_format="mp3_44100_128",
                        )
                        
                        audio_data = b"".join(audio_stream)
                        output_emitter.write(audio_data)
                        output_emitter.end()
                
                tts = ElevenLabsV3HTTP(voice_id=voice_id, model=resolved_tts_model, client=eleven_client)
                
            except ImportError:
                logger.warning("ELEVENLABS_V3_SDK_MISSING: falling back to eleven_flash_v2_5")
                resolved_tts_model = "eleven_flash_v2_5"
                tts = elevenlabs.TTS(voice_id=voice_id, model=resolved_tts_model, api_key=eleven_key)
            except Exception as e:
                logger.error(f"ELEVENLABS_V3_INIT_FAILED: {e}, falling back to eleven_flash_v2_5")
                resolved_tts_model = "eleven_flash_v2_5"
                tts = elevenlabs.TTS(voice_id=voice_id, model=resolved_tts_model, api_key=eleven_key)
        else:
            tts = elevenlabs.TTS(
                voice_id=voice_id,
                model=resolved_tts_model,
                api_key=eleven_key,
            )
    else:
        # Use pre-warmed Deepgram TTS if available, otherwise create new.
        resolved_voice_id = tts_voice
        resolved_tts_model = None
        tts = ctx.proc.userdata.get("tts_deepgram")
        if tts is None:
            tts = deepgram.TTS(model=tts_voice)

    logger.info(
        f"[{AGENT_WORKER_NAME}] Using tts_provider={tts_provider} voice={resolved_voice_id} tts_model={resolved_tts_model}"
    )
    
    agent = VoicePipelineAgent(
        vad=vad,
        stt=deepgram.STT(
            language=stt_language,
            model="nova-2-general",
            interim_results=True,
        ),
        llm=llm_instance,
        tts=tts,
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,
        min_endpointing_delay=0.5,
        max_endpointing_delay=silence_timeout_ms / 1000.0,
    )
    
    @agent.on("agent_started_speaking")
    def on_agent_started():
        logger.info(f"[{AGENT_WORKER_NAME}] Agent started speaking")
    
    @agent.on("agent_stopped_speaking")
    def on_agent_stopped():
        logger.info(f"[{AGENT_WORKER_NAME}] Agent stopped speaking")
    
    @agent.on("user_started_speaking")
    def on_user_started():
        logger.info(f"[{AGENT_WORKER_NAME}] User started speaking")
    
    @agent.on("user_stopped_speaking")
    def on_user_stopped():
        logger.info(f"[{AGENT_WORKER_NAME}] User stopped speaking")
    
    @agent.on("llm_new_message")
    def on_new_message(msg):
        content = msg.content if hasattr(msg, 'content') else str(msg)
        logger.info(f"[{AGENT_WORKER_NAME}] New LLM message: {content[:50]}...")
        if call_id and hasattr(msg, 'role') and msg.role == "assistant":
            usage.add_tts_characters(len(content))
            # Try to get actual token usage from the message if available
            if hasattr(msg, 'usage') and msg.usage:
                try:
                    usage_data = msg.usage
                    if hasattr(usage_data, 'prompt_tokens'):
                        usage.add_llm_usage(tokens_in=usage_data.prompt_tokens, model=model_name)
                    if hasattr(usage_data, 'completion_tokens'):
                        usage.add_llm_usage(tokens_out=usage_data.completion_tokens, model=model_name)
                    logger.info(f"[{AGENT_WORKER_NAME}] Real token usage from API: {usage_data}")
                except Exception as e:
                    logger.warning(f"[{AGENT_WORKER_NAME}] Could not get usage from msg: {e}")
            # Better token estimation: ~3 chars per token (more accurate than 4)
            usage.add_llm_usage(tokens_out=max(len(content) // 3, 10), model=model_name)
            usage.add_transcript("agent", content)
            asyncio.create_task(send_transcript_to_api(call_id, "agent", content))
    
    @agent.on("stt_transcript_received")
    def on_transcript(transcript):
        if transcript.is_final and call_id:
            content = transcript.text
            word_count = len(content.split())
            estimated_duration_ms = int((word_count / 150.0) * 60 * 1000)
            usage.add_stt_duration(estimated_duration_ms)
            # Better token estimation: ~3 chars per token (more accurate than 4)
            usage.add_llm_usage(tokens_in=max(len(content) // 3, 10), model=model_name)
            usage.add_transcript("user", content)
            asyncio.create_task(send_transcript_to_api(call_id, "user", content, is_final=True))
    
    agent.start(ctx.room)
    
    logger.info(f"[{AGENT_WORKER_NAME}] Agent started, welcome_message_type: {welcome_message_type}")
    
    # Only send greeting if agent speaks first, otherwise wait for user to speak
    if welcome_message_type == "agent_speaks_first" and welcome_message:
        logger.info(f"[{AGENT_WORKER_NAME}] Sending greeting...")
        await agent.say(welcome_message, allow_interruptions=enable_interruptions)
        logger.info(f"[{AGENT_WORKER_NAME}] Greeting complete, waiting for user...")
    else:
        logger.info(f"[{AGENT_WORKER_NAME}] User speaks first - waiting for user to speak...")
    
    # Wait for disconnect with timeout
    done = asyncio.Event()
    
    @ctx.room.on("disconnected")
    def on_disconnect():
        done.set()
    
    try:
        await asyncio.wait_for(done.wait(), timeout=MAX_CALL_DURATION)
    except asyncio.TimeoutError:
        logger.warning(f"[{AGENT_WORKER_NAME}] Call timed out after {MAX_CALL_DURATION}s - ending session")
    
    # Send final usage metrics
    if call_id:
        await send_usage_to_api(call_id, usage)
    
    logger.info(f"[{AGENT_WORKER_NAME}] Session ended for room: {ctx.room.name} - Duration: {usage.get_call_duration()}s")


if __name__ == "__main__":
    logger.info(f"[{AGENT_WORKER_NAME}] Starting voice agent worker...")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="sarah",  # Must match SIP dispatch rule agent_name
        )
    )
