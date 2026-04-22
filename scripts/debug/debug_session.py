import livekit.agents
from livekit.agents import Agent, AgentSession

session = AgentSession(vad=None, stt=None, llm=None, tts=None)
print("AgentSession dir:", dir(session))
print("Agent dir:", dir(Agent))

# Check for events
if hasattr(session, "on"):
    print("AgentSession has .on() method")
