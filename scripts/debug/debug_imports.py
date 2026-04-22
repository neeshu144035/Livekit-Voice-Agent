import livekit.agents
import livekit.plugins.silero
import livekit.plugins.turn_detector
import livekit.plugins.openai
import livekit.plugins.deepgram

print("LiveKit Agents version:", livekit.agents.__version__)
print("Turn Detector dir:", [x for x in dir(livekit.plugins.turn_detector) if not x.startswith("_")])

try:
    from livekit.agents.pipeline import VoicePipelineAgent
    print("Found VoicePipelineAgent in livekit.agents.pipeline")
except ImportError:
    print("VoicePipelineAgent NOT found in livekit.agents.pipeline")

try:
    from livekit.agents.voice_assistant import VoiceAssistant
    print("Found VoiceAssistant in livekit.agents.voice_assistant")
except ImportError:
    print("VoiceAssistant NOT found in livekit.agents.voice_assistant")

try:
    from livekit.agents.multimodal import MultimodalAgent
    print("Found MultimodalAgent in livekit.agents.multimodal")
except ImportError:
    print("MultimodalAgent NOT found in livekit.agents.multimodal")
