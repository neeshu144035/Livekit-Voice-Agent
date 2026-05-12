from livekit.agents.llm import function_tool, Agent
import logging

logger = logging.getLogger(__name__)

class DynamicPropertyAgent(Agent):
    def __init__(self, instructions, functions_config, room=None, call_id=None):
        self.functions_config = functions_config
        self.room = room
        self.call_id = call_id
        self._transfer_in_progress = False
        self._pending_end_call_after_speech = False
        self._end_call_handoff_started = False
        super().__init__(instructions=instructions)

def create_dynamic_agent_class(functions_config, base_instructions, current_room=None, call_id=None):
    if not functions_config:
        return Agent(instructions=base_instructions)

    # We dynamically create a subclass
    class CustomAgent(DynamicPropertyAgent):
        pass

    for func in functions_config:
        func_name = func.get("name", "").strip().replace(" ", "_").lower()
        if not func_name:
            continue

        speak_during = func.get("speak_during_execution", False)
        speak_after = func.get("speak_after_execution", True)
        # simplistic mode resolution for poc
        speech_mode = "during" if speak_during else "after" if speak_after else "default"

        desc = func.get("description", "").strip()
        variables = func.get("variables", {})
        if not variables:
            schema = func.get("parameters_schema", {})
            if isinstance(schema, dict) and "properties" in schema:
                variables = schema.get("properties", {})

        # We construct a python wrapper dynamically to get the right async signature
        # We only use exec to construct the signature, so it's safer if we strictly validate or avoid injecting user strings into code, OR we just use `**kwargs` and check types manually? Livekit LLM uses `inspect.signature` to figure out parameters.
        # Wait, if we use **kwargs, livekit doesn't know what the arguments are! We must give it a proper signature.
        # But wait! We can just build a function, but set its __signature__!
        pass
