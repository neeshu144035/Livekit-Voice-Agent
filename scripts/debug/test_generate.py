import json
import asyncio
import logging
from typing import Annotated
from livekit.agents import RunContext, Agent

# Dummy objects for testing without livekit running
def function_tool(description=""):
    def decorator(func):
        func.__livekit_tool__ = True
        return func
    return decorator

logger = logging.getLogger("test")

def create_dynamic_agent_class(functions_config, base_instructions):
    class_def = """
class DynamicPropertyAgent(Agent):
    def __init__(self, instructions: str, functions_config: list, room=None):
        self.functions_config = functions_config
        self.room = room
        super().__init__(instructions=instructions)
"""
    
    for func in functions_config:
        func_name = func.get("name", "").replace(" ", "_").lower()
        if not func_name:
            continue
            
        desc = func.get("description", "").replace('"', "'")
        variables = func.get("variables", {})
        
        args_def = ["self", "ctx: RunContext"]
        args_dict_str = []
        for v_name, v_info in variables.items():
            clean_v_name = v_name.replace(" ", "_").lower()
            v_desc = str(v_info.get("description", "")).replace('"', "'")
            v_type = v_info.get("type", "string")
            py_type = "str"
            if v_type in ["integer", "number"]:
                py_type = "int"
            elif v_type == "boolean":
                py_type = "bool"
                
            args_def.append(f'{clean_v_name}: Annotated[{py_type}, "{v_desc}"] = ""')
            args_dict_str.append(f'"{clean_v_name}": {clean_v_name}')
            
        args_str = ", ".join(args_def)
        payload_dict_str = "{" + ", ".join(args_dict_str) + "}"
        
        method_def = f"""
    @function_tool(description="{desc}")
    async def {func_name}({args_str}) -> dict:
        logger.info(f"Tool {func_name} called with args: {{ {payload_dict_str} }}")
        
        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_call", "tool_name": "{func_name}", "args": {payload_dict_str}}})
                ))
            except Exception as e:
                logger.error(f"Failed to publish tool_call event: {{e}}")
                
        result = {{"error": "Tool execution failed"}}
        
        for func_cfg in self.functions_config:
            if func_cfg.get("name", "").replace(" ", "_").lower() == "{func_name}":
                url = func_cfg.get("url", "")
                method = func_cfg.get("method", "POST").upper()
                timeout_ms = func_cfg.get("timeout_ms", 120000)
                headers = func_cfg.get("headers", {{}})
                
                if url:
                    try:
                        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
                            if method == "GET":
                                response = await client.get(url, headers=headers, params={payload_dict_str})
                            else:
                                response = await client.post(url, headers=headers, json={payload_dict_str})
                            
                            try:
                                result = response.json()
                            except:
                                result = {{"response": response.text, "status": response.status_code}}
                    except Exception as e:
                        logger.error(f"Error calling {func_name}: {{e}}")
                        result = {{"error": str(e)}}
                break
                
        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_response", "tool_name": "{func_name}", "response": result}})
                ))
            except:
                pass
                
        return result
"""
        class_def += method_def

    local_vars = {}
    exec(class_def, globals(), local_vars)
    AgentClass = local_vars["DynamicPropertyAgent"]
    return AgentClass(instructions=base_instructions, functions_config=functions_config)


agent = create_dynamic_agent_class([{"name": "test_book", "variables": {"user": {"type": "string"}}}], "You are helpful.")
print(dir(agent))
print("Test completed.")
