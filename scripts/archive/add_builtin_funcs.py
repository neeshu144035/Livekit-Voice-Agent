import re

# Read the file
with open('/home/ubuntu/livekit-agent/agent_retell.py', 'r') as f:
    content = f.read()

# Find the location after fetch_agent_functions and before logger.info
old_pattern = r'(functions = await fetch_agent_functions\(agent_id\)\n)(\s+logger\.info\(f"Agent: )'

new_code = '''functions = await fetch_agent_functions(agent_id)
    
    # Add builtin functions from custom_params
    custom_params = config.get('custom_params', {})
    builtin_funcs = custom_params.get('builtin_functions', {})
    
    if builtin_funcs.get('builtin_transfer_call', {}).get('enabled'):
        transfer_cfg = builtin_funcs['builtin_transfer_call'].get('config', {})
        phone_number = transfer_cfg.get('phone_number', '')
        functions.append({
            'name': 'transfer_call',
            'description': 'Transfer the call to a human agent. Use this when caller wants to buy a property.',
            'method': 'POST',
            'url': '',
            'parameters_schema': {
                'type': 'object',
                'properties': {
                    'phone_number': {'type': 'string', 'description': 'Phone number to transfer to'}
                }
            },
            'phone_number': phone_number
        })
        logger.info(f'Added builtin transfer_call function with phone: {phone_number}')
    
    if builtin_funcs.get('builtin_end_call', {}).get('enabled'):
        functions.append({
            'name': 'end_call',
            'description': 'End the call politely.',
            'method': 'POST',
            'url': '',
            'parameters_schema': {'type': 'object', 'properties': {}}
        })
        logger.info(f'Added builtin end_call function')
    
    logger.info(f'''

# Replace
content = re.sub(old_pattern, new_code + r'\2', content)

# Write back
with open('/home/ubuntu/livekit-agent/agent_retell.py', 'w') as f:
    f.write(content)

print('Done!')
