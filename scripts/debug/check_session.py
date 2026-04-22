from livekit.agents import AgentSession
import inspect

# Check session.start signature
sig = inspect.signature(AgentSession.start)
print("AgentSession.start params:")
for name, param in sig.parameters.items():
    print(f"  - {name}: {param.default}")
