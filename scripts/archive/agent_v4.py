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

# Pre-warm LLM at startup
_llm_cache = {}
_tts_cache = {}

def _get_llm(model_name: str, api_key: str):
    if model_name not in _llm_cache:
        _llm_cache[model_name] = openai.LLM(
            api_key=api_key,
            model=model_name,
            base_url="https://api.moonshot.ai/v1",
        )
    return _llm_cache[model_name]

def _get_tts(voice: str):
    voice_mapping = {
        'jessica': 'aura-asteria-en',
        'mark': 'aura-orion-en',
        'sarah': 'aura-luna-en',
        'michael': 'aura-perseus-en',
        'emma': 'aura-hera-en',
        'james': 'aura-zeus-en',
    }
    tts_voice = voice_mapping.get(voice, 'aura-asteria-en')
    if tts_voice not in _tts_cache:
        _tts_cache[tts_voice] = deepgram.TTS(model=tts_voice)
    return _tts_cache[tts_voice]


async def fetch_agent_config(agent_id: int = 1) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{DASHBOARD_API_URL}/agents/{agent_id}")
            resp.raise_for_status()
            config = resp.json()
            logger.info(f"Fetched agent config: name={config.get('name')}, model={config.get('llm_model')}, voice={config.get('voice')}, language={config.get('language')}")
            return config
    except Exception as e:
        logger.error(f"Failed to fetch agent config from API: {e}")
        return {
            "name": "Default Assistant",
            "system_prompt": "You are a friendly and helpful AI voice assistant.",
            "llm_model": "moonshot-v1-8k",
            "voice": "jessica",
            "language": "en-GB",
        }


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    # Pre-warm LLM and TTS
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        _get_llm("moonshot-v1-8k", api_key)
        _get_tts("jessica")


async def entrypoint(ctx: JobContext):
    room_name = ctx.room.name
    try:
        agent_id = int(room_name.split('-')[-1])
    except (ValueError, IndexError):
        agent_id = 1
    
    logger.info(f"Room: {room_name}, Agent ID: {agent_id}")
    
    config = await fetch_agent_config(agent_id=agent_id)
    
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    model_name = config.get("llm_model", "moonshot-v1-8k")
    voice_name = config.get("voice", "jessica")
    language = config.get("language", "en-GB")
    
    logger.info(f"Using Model: {model_name}")
    logger.info(f"Using Voice: {voice_name}")
    logger.info(f"Using Language: {language}")
    logger.info(f"System Prompt: {system_prompt[:200]}...")

    # Use cached LLM
    kimi_llm = _get_llm(model_name, os.getenv("OPENAI_API_KEY"))
    
    # Use cached TTS
    tts = _get_tts(voice_name)

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

    logger.info(f"Voice agent '{config.get('name')}' started and listening.")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
