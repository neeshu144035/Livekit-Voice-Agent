with open('/home/ubuntu/livekit-agent/agent.py', 'r') as f:
    content = f.read()

# Add the report_builtin_action function before the entrypoint function
function_code = '''
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

# Find a good place to insert it (before entrypoint function)
if 'async def entrypoint' in content:
    content = content.replace('async def entrypoint', function_code + 'async def entrypoint')
    with open('/home/ubuntu/livekit-agent/agent.py', 'w') as f:
        f.write(content)
    print('Done! Added report_builtin_action function')
else:
    print('Could not find entrypoint function')
