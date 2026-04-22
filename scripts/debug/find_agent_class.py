import livekit.agents
import livekit.agents.voice
import livekit.agents.llm
import livekit.agents.stt
import livekit.agents.tts

def find_in_module(module, name):
    for attr_name in dir(module):
        if name in attr_name:
            print(f"Found something interesting in {module.__name__}: {attr_name}")

print("Searching for Assistant or Pipeline...")
find_in_module(livekit.agents, "Assistant")
find_in_module(livekit.agents, "Pipeline")
find_in_module(livekit.agents.voice, "Assistant")
find_in_module(livekit.agents.voice, "Pipeline")

try:
    from livekit.agents.voice import VoiceAssistant
    print("Found VoiceAssistant in livekit.agents.voice")
except ImportError:
    print("NOT found in livekit.agents.voice")

try:
    from livekit.agents.voice_assistant import VoiceAssistant
    print("Found VoiceAssistant in livekit.agents.voice_assistant")
except ImportError:
    print("NOT found in livekit.agents.voice_assistant")

try:
    from livekit.agents.pipeline import VoicePipelineAgent
    print("Found VoicePipelineAgent in livekit.agents.pipeline")
except ImportError:
    print("NOT found in livekit.agents.pipeline")
