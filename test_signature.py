import asyncio
from agent_retell import create_dynamic_agent_class

functions = [
    {
        "name": "test_tool",
        "description": "test desc",
        "variables": {
            "arg1": {"type": "string", "description": "arg desc"}
        }
    }
]

agent = create_dynamic_agent_class(functions, "test instructions")
tool = getattr(agent, "test_tool")
print("Function arguments signature:")
print(tool._func.__signature__)
