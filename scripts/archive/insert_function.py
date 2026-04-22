# Read the file
with open('/home/ubuntu/livekit-agent/agent_retell.py', 'r') as f:
    lines = f.readlines()

# Function to insert
function_lines = '''
async def report_builtin_action(call_id: str, action: str, parameters: dict):
    """Report a built-in action to the dashboard API"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/builtin-action",
                json={"action": action, "parameters": parameters}
            )
            if resp.status_code == 200:
                logger.info(f"[{AGENT_WORKER_NAME}] Reported {action}: {resp.json()}")
            else:
                logger.warning(f"[{AGENT_WORKER_NAME}] Failed to report {action}: {resp.status_code}")
    except Exception as e:
        logger.error(f"[{AGENT_WORKER_NAME}] Error reporting {action}: {e}")


'''

# Find the right place to insert (after line 387 which is blank after return)
# Look for "return from_number, to_number" and insert after the following blank line
insert_after = None
for i, line in enumerate(lines):
    if 'return from_number, to_number' in line:
        insert_after = i + 1  # Insert after this line
        break

if insert_after:
    # Insert the function
    lines.insert(insert_after, function_lines)
    
    # Write back
    with open('/home/ubuntu/livekit-agent/agent_retell.py', 'w') as f:
        f.writelines(lines)
    print('Done! Added report_builtin_action function')
else:
    print('Could not find insertion point')
