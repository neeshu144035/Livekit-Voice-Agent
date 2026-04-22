import os
import logging
import asyncio
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
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, openai, silero

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")

# Dashboard API URL
DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://13.135.81.172:8000")

def prewarm(proc: JobProcess):
    """Load VAD once at worker startup."""
    proc.userdata["vad"] = silero.VAD.load()

async def fetch_agent_config(agent_id: int) -> dict:
    """Fetch the latest agent config from the dashboard backend."""
    url = f"{DASHBOARD_API_URL}/agents/{agent_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            config = resp.json()
            logger.info(f"Loaded config for agent {agent_id}: {config.get('name')}")
            return config
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id} config from {url}: {e}")
        return {
            "name": "LiveKit Assistant",
            "system_prompt": "You are a helpful AI voice assistant.",
            "llm_model": "moonshot-v1-8k",
            "voice": "jessica",
            "language": "en-GB"
        }

async def entrypoint(ctx: JobContext):
    logger.info(f"Starting job for room: {ctx.room.name}")

    # Parse agent_id from room name (format: agent-test-{id})
    try:
        agent_id = int(ctx.room.name.split('-')[-1])
    except (ValueError, IndexError):
        agent_id = 1

    # Fetch configuration
    config = await fetch_agent_config(agent_id)
    
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    model_name = config.get("llm_model", "moonshot-v1-8k")
    voice_name = config.get("voice", "jessica")
    language = config.get("language", "en-GB")

    # FIX: If the model is 'gpt-4o' but we are using Moonshot API, fallback to a moonshot model
    if model_name == "gpt-4o":
        model_name = "moonshot-v1-8k"
        logger.info(f"Model gpt-4o requested but using moonshot fallback: {model_name}")

    # Map dashboard voice names to Deepgram Aura voices
    voice_map = {
        'jessica': 'aura-asteria-en',
        'mark': 'aura-orion-en',
        'sarah': 'aura-luna-en',
        'michael': 'aura-perseus-en',
        'emma': 'aura-hera-en',
        'james': 'aura-zeus-en',
    }
    tts_voice = voice_map.get(voice_name, 'aura-asteria-en')

    # Initialize LLM (Kimi/Moonshot)
    # Using .ai URL as it was used in previous working 'agent_fast.py'
    llm_instance = openai.LLM(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=model_name,
        base_url="https://api.moonshot.ai/v1",
    )

    # Initial context (System Prompt)
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_prompt,
    )

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to room. Starting VoiceAssistant pipeline...")

    # Create VoiceAssistant
    assistant = VoiceAssistant(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(language=language, model="nova-2-general"),
        llm=llm_instance,
        tts=deepgram.TTS(model=tts_voice),
        chat_ctx=initial_ctx,
        min_endpointing_delay=0.6,
    )

    # Start the assistant
    assistant.start(ctx.room)
    
    # GREETING: This confirms the agent joined and TTS is working
    await assistant.say("Hello, how can I help you today?")

    # KEEP ALIVE: Keep the entrypoint function running while the room is active
    # This prevents the job from exiting immediately
    while not ctx.room.is_disconnected():
        await asyncio.sleep(1)

    logger.info(f"Agent '{config.get('name')}' (ID: {agent_id}) session ended.")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
