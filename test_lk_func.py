import asyncio
from typing import Annotated
from livekit.agents.llm import function_tool

class Agent:
    pass

class DynamicAgent(Agent):
    pass

def make_dynamic_tool(func_name, desc, variables):
    async def dynamic_func(self, **kwargs) -> dict:
        print("Called", func_name, "with", kwargs)
        return {"success": True}

    dynamic_func.__name__ = func_name

    # We need to set annotations dynamically
    annotations = {"return": dict}
    for v_name, v_info in variables.items():
        v_type = v_info.get("type", "string")
        py_type = str
        if v_type in ["integer", "number"]: py_type = int
        elif v_type == "boolean": py_type = bool

        v_desc = v_info.get("description", "")
        annotations[v_name] = Annotated[py_type, v_desc]

    dynamic_func.__annotations__ = annotations

    # Now decorate it
    decorated = function_tool(description=desc)(dynamic_func)
    return decorated

tool = make_dynamic_tool("test_func", "A desc", {"arg1": {"type": "string", "description": "arg1 desc"}})
setattr(DynamicAgent, "test_func", tool)

agent = DynamicAgent()
print("Tools:", [m for m in dir(agent) if hasattr(getattr(agent, m), '__livekit_tool_info')])

# Does it have tool_info?
t = getattr(agent, "test_func")
print(t.info)


import inspect
print(inspect.signature(t._func))

from livekit.agents.llm import ToolContext
ctx = ToolContext()
# how to add the agent? agent is a subclass of ToolContext? Wait, what does llm module say
