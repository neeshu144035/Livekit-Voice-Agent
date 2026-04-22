import re

with open('/home/ubuntu/livekit-agent/agent.py', 'r') as f:
    content = f.read()

# Find the section where fnc_ctx is created and add dynamic functions
old_code = '''    # Create function context with built-in functions
    fnc_ctx = None
    if call_id:
        # Define function schemas for LLM
        fnc_ctx = {
            "end_call": {
                "description": "End the current call immediately. Use this when the user wants to hang up, says goodbye, or when the conversation is complete.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for ending the call"
                        }
                    }
                }
            },
            "call_transfer": {
                "description": "Transfer the current call to another phone number. Use this when the user needs to speak to a different department or person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Phone number to transfer to (E.164 format, e.g., +1234567890)"
                        }
                    },
                    "required": ["phone_number"]
                }
            }
        }'''

new_code = '''    # Create function context with built-in functions
    fnc_ctx = None
    if call_id:
        # Define function schemas for LLM
        fnc_ctx = {
            "end_call": {
                "description": "End the current call immediately. Use this when the user wants to hang up, says goodbye, or when the conversation is complete.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for ending the call"
                        }
                    }
                }
            },
            "call_transfer": {
                "description": "Transfer the current call to another phone number. Use this when the user needs to speak to a different department or person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Phone number to transfer to (E.164 format, e.g., +1234567890)"
                        }
                    },
                    "required": ["phone_number"]
                }
            }
        }
        
        # Add dynamic functions from database to fnc_ctx
        for func in functions:
            func_name = func.get('name', '').strip().replace(' ', '_').lower()
            if not func_name or func_name in ['end_call', 'call_transfer']:
                continue
            
            func_desc = func.get('description', '')
            schema = func.get('parameters_schema', {})
            
            # Convert schema to fnc_ctx format
            fnc_ctx[func_name] = {
                'description': func_desc,
                'parameters': schema if schema else {'type': 'object', 'properties': {}}
            }
            logger.info(f"Added function {func_name} to fnc_ctx")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/home/ubuntu/livekit-agent/agent.py', 'w') as f:
        f.write(content)
    print('Done! Fixed fnc_ctx to include dynamic functions')
else:
    print('Could not find the code to replace. Checking file...')
    # Try to find the pattern
    if 'fnc_ctx = None' in content:
        print('Found fnc_ctx = None')
    if 'end_call' in content:
        print('Found end_call')
