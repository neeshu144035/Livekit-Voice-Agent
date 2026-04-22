import os
import logging
import httpx
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, openai, silero

load_dotenv()

logger = logging.getLogger("voice-agent")

DASHBOARD_API_URL = "http://13.135.81.172:8000"

# Pre-warm everything at worker startup
_logger = logging.getLogger("voice-agent")
_logger.info("Pre-warming LLM and TTS...")

_prewarmed_llms = {}
_prewarmed_tts = {}

def _get_llm(model_name: str):
    if model_name not in _prewarmed_llms:
        api_key = os.getenv("OPENAI_API_KEY", "")
        _prewarmed_llms[model_name] = openai.LLM(
            api_key=api_key,
            model=model_name,
            base_url="https://api.moonshot.ai/v1",
        )
    return _prewarmed_llms[model_name]

def _get_tts(voice: str):
    if voice not in _prewarmed_tts:
        _prewarmed_tts[voice] = deepgram.TTS(model=voice)
    return _prewarmed_tts[voice]


async def fetch_agent_config(agent_id: int = 1) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{DASHBOARD_API_URL}/agents/{agent_id}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch config: {e}")
        return {
            "name": "Default Assistant",
            "system_prompt": "You are a helpful AI assistant.",
            "llm_model": "moonshot-v1-8k",
            "voice": "jessica",
            "language": "en-GB",
        }


def prewarm(proc: JobProcess):
    # Pre-warm VAD
    proc.userdata["vad"] = silero.VAD.load()
    
    # Pre-warm common LLMs and TTS
    for model in ["moonshot-v1-8k", "kimi-k2.5"]:
        try:
            _get_llm(model)
            logger.info(f"Pre-warmed LLM: {model}")
        except Exception as e:
            logger.error(f"Failed to pre-warm LLM {model}: {e}")
    
    for voice in ["aura-asteria-en", "aura-orion-en"]:
        try:
            _get_tts(voice)
            logger.info(f"Pre-warmed TTS: {voice}")
        except Exception as e:
            logger.error(f"Failed to pre-warm TTS {voice}: {e}")


async def entrypoint(ctx: JobContext):
    room_name = ctx.room.name
    try:
        agent_id = int(room_name.split('-')[-1])
    except (ValueError, IndexError):
        agent_id = 1
    
    logger.info(f"Room: {room_name}, Agent ID: {agent_id}")
    
    # Fetch config
    config = await fetch_agent_config(agent_id)
    
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    model_name = config.get("llm_model", "moonshot-v1-8k")
    voice_name = config.get("voice", "jessica")
    language = config.get("language", "en-GB")
    
    logger.info(f"Using Model: {model_name}, Voice: {voice_name}, Lang: {language}")

    # Use pre-warmed LLM
    kimi_llm = _get_llm(model_name)
    
    # Use pre-warmed TTS
    voice_map = {
        'jessica': 'aura-asteria-en',
        'mark': 'aura-orion-en',
        'sarah': 'aura-luna-en',
        'michael': 'aura-perseus-en',
        'emma': 'aura-hera-en',
        'james': 'aura-zeus-en',
    }
    tts_voice = voice_map.get(voice_name, 'aura-asteria-en')
    tts = _get_tts(tts_voice)

    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = Agent(instructions=system_prompt)

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model='nova-2-general', interim_results=True, language=language),
        llm=kimi_llm,
        tts=tts,
    )

    await session.start(agent=agent, room=ctx.room)
    logger.info(f"Agent '{config.get('name')}' ready and listening.")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
