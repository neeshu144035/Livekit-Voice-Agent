from livekit.agents import tts as lk_tts
from livekit.agents import tokenize as lk_tokenize
from livekit.plugins import elevenlabs
import os

api_key = os.environ.get("ELEVEN_API_KEY", "")
base_tts = elevenlabs.TTS(voice_id="pNInz6obpgDQGcFmaJgB", model="eleven_v3", api_key=api_key)
adapted = lk_tts.StreamAdapter(tts=base_tts, sentence_tokenizer=lk_tokenize.basic.SentenceTokenizer())
print("StreamAdapter created successfully:", type(adapted))
print("capabilities.streaming:", adapted.capabilities.streaming)
