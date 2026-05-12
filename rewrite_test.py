import asyncio
import inspect
import json
from typing import Annotated

# We will write a snippet that mocks what we want to replace `exec` with.

class Agent:
    def __init__(self, instructions):
        pass

def function_tool(description=""):
    def decorator(func):
        # MOCK
        func._is_tool = True
        return func
    return decorator

def create_dynamic_agent_class(functions_config, base_instructions, current_room=None, call_id=None):
    if not functions_config:
        return Agent(instructions=base_instructions)

    class DynamicPropertyAgent(Agent):
        def __init__(self, instructions, functions_config, room=None, call_id=None):
            self.functions_config = functions_config
            self.room = room
            self.call_id = call_id
            self._transfer_in_progress = False
            self._pending_end_call_after_speech = False
            self._end_call_handoff_started = False
            super().__init__(instructions=instructions)

    for func in functions_config:
        func_name = func.get("name", "").strip().replace(" ", "_").lower()
        if not func_name:
            continue

        speak_during = func.get("speak_during_execution", False)
        speak_after = func.get("speak_after_execution", True)
        speech_mode = "during" if speak_during else "after" if speak_after else "default"

        desc = func.get("description", "").strip()

        variables = func.get("variables", {})
        if not variables:
            schema = func.get("parameters_schema", {})
            if isinstance(schema, dict) and "properties" in schema:
                variables = schema.get("properties", {})

        # Build dynamic tool function
        async def tool_wrapper(self, **kwargs) -> dict:
            # Replicating original logic
            payload = kwargs
            normalized_tool_name = func_name
            # simplified for test
            print(f"Executing {func_name} with args {kwargs}")
            return {"success": True, "action": "test", "payload": payload}

        tool_wrapper.__name__ = func_name

        # Build signature dynamically
        params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]

        for v_name, v_info in variables.items():
            clean_v_name = v_name.strip().replace(" ", "_").lower()
            v_desc = str(v_info.get("description", ""))
            v_type = v_info.get("type", "string")
            py_type = str
            if v_type in ["integer", "number"]:
                py_type = int
            elif v_type == "boolean":
                py_type = bool

            params.append(
                inspect.Parameter(
                    clean_v_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Annotated[py_type, v_desc],
                    default=""
                )
            )

        tool_wrapper.__signature__ = inspect.Signature(params)

        decorated_tool = function_tool(description=desc)(tool_wrapper)
        setattr(DynamicPropertyAgent, func_name, decorated_tool)

    return DynamicPropertyAgent(instructions=base_instructions, functions_config=functions_config, room=current_room, call_id=call_id)

functions_config = [
    {
        "name": "test_tool",
        "description": "A tool for testing",
        "variables": {
            "test_arg": {"type": "string", "description": "a test arg"}
        }
    }
]

agent = create_dynamic_agent_class(functions_config, "test")
print(dir(agent))
asyncio.run(agent.test_tool(test_arg="hello"))
