import inspect
from livekit.agents.llm import function_tool, ToolContext, FunctionTool, execute_function_call

# Try subclassing Agent
class CustomAgent:
    pass

def create_func(name, description):
    async def dynamic_tool(self) -> dict:
        print("Dynamic tool called")
        return {"success": True}

    # rename function
    dynamic_tool.__name__ = name

    # decorate
    decorated = function_tool(description=description)(dynamic_tool)
    return decorated

tool1 = create_func("test_tool", "A test tool")

# Can we bind it to a class?
setattr(CustomAgent, "test_tool", tool1)

agent = CustomAgent()

print(dir(agent.test_tool))
