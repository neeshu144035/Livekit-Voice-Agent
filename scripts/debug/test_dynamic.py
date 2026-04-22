import json
import logging
from typing import Annotated

functions_config = [
    {
        "name": "Confirmation",
        "description": "Call this tool when they want to book an viewing appointment",
        "method": "POST",
        "url": "https://oyik.cloud/webhook/test",
        "variables": {
            "property_name": {
                "description": "which property...",
                "type": "string"
            }
        }
    }
]

def create_dynamic_agent_class_code(functions_config):
    class_def = """
from livekit.agents import Agent, function_tool, RunContext
from typing import Annotated
import json
import asyncio
import httpx
import logging

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
            v_desc = v_info.get("description", "").replace('"', "'")
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
        print(f"Tool {func_name} called with args: {{ {payload_dict_str} }}")
        return {{"status": "ok"}}
"""
        class_def += method_def
        
    return class_def

code = create_dynamic_agent_class_code(functions_config)
print(code)
