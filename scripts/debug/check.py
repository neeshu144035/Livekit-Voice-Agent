import inspect
from livekit.plugins import elevenlabs

try:
    print("TTS kwargs:", inspect.signature(elevenlabs.TTS.__init__))
except Exception as e:
    print("Error:", e)
    
try:
    print("Voice class:", getattr(elevenlabs, "Voice", None))
except Exception as e:
    print("Voice Error:", e)
    
try:
    print("Voice class kwargs:", getattr(elevenlabs.Voice, "__init__", "None"))
except Exception:
    pass
