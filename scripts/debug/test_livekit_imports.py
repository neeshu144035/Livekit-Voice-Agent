import livekit.agents
print("dir(livekit.agents):", [x for x in dir(livekit.agents) if not x.startswith("_")])

try:
    from livekit.agents import VoiceAssistant
    print("Successfully imported VoiceAssistant from livekit.agents")
except ImportError as e:
    print("Failed to import VoiceAssistant from livekit.agents:", e)

try:
    from livekit.agents import VoicePipelineAgent
    print("Successfully imported VoicePipelineAgent from livekit.agents")
except ImportError as e:
    print("Failed to import VoicePipelineAgent from livekit.agents:", e)

try:
    import livekit.agents.pipeline as pipeline
    print("Pipeline dir:", dir(pipeline))
except ImportError as e:
    print("Pipeline import error:", e)
