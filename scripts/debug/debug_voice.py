import livekit.agents
import livekit.agents.voice as v
print("Voice members:", [x for x in dir(v) if not x.startswith("_")])

try:
    from livekit.agents.voice import VoiceAssistant
    print("Successfully imported VoiceAssistant from livekit.agents.voice")
except ImportError:
    print("Failed to import VoiceAssistant from livekit.agents.voice")

try:
    from livekit.agents.pipeline import VoicePipelineAgent
    print("Successfully imported VoicePipelineAgent from livekit.agents.pipeline")
except ImportError:
    print("Failed to import VoicePipelineAgent from livekit.agents.pipeline")
