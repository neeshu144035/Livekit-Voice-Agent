import livekit.agents
import pkg_resources

print("LiveKit Agents version (pkg_resources):", pkg_resources.get_distribution("livekit-agents").version)
print("LiveKit Agents file:", livekit.agents.__file__)
print("LiveKit Agents dir:", dir(livekit.agents))

try:
    import livekit.agents.pipeline
    print("Pipeline dir:", dir(livekit.agents.pipeline))
except ImportError as e:
    print("Pipeline import error:", e)

try:
    import livekit.agents.voice
    print("Voice dir:", dir(livekit.agents.voice))
except ImportError as e:
    print("Voice import error:", e)
