import os
import asyncio
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, llm
from livekit.plugins import deepgram, silero

load_dotenv()

MOONSHOT_API_KEY = os.getenv("OPENAI_API_KEY", "")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful and friendly AI voice assistant. Keep responses short.")
VOICE = os.getenv("VOICE", "jessica")
LANGUAGE = os.getenv("LANGUAGE", "en-GB")

voice_map = {
    'jessica': 'aura-asteria-en',
    'mark': 'aura-orion-en',
    'sarah': 'aura-luna-en',
    'michael': 'aura-perseus-en',
}
tts_voice = voice_map.get(VOICE, 'aura-asteria-en')

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=SYSTEM_PROMPT,
    )

    # Use Moonshot Kimi 2.5
    llm_instance = llm.LLM(
        model="kimick2-5",
        api_key=MOONSHOT_API_KEY,
        base_url="https://api.moonshot.cn/v1",
    )

    from livekit.agents.voice_assistant import VoiceAssistant
    assistant = VoiceAssistant(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(language=LANGUAGE, model="nova-2-general"),
        llm=llm_instance,
        tts=deepgram.TTS(model=tts_voice),
        chat_ctx=initial_ctx,
        min_endpointing_delay=0.3,
    )

    assistant.start(ctx.room)
    await assistant.say("Hello! How can I help you today?")

    while not ctx.room.is_disconnected():
        await asyncio.sleep(1)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
