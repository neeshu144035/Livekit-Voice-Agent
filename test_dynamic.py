class Agent:
    def __init__(self, instructions):
        self.instructions = instructions

def function_tool(description):
    def decorator(func):
        func.__tool_description__ = description
        return func
    return decorator

def create_dynamic_agent_class():
    functions_config = [{"name": "test_func", "description": "A test func"}]
    class DynamicPropertyAgent(Agent):
        pass

    # how to dynamically add tool?
