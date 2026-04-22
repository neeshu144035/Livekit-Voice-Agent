import re

with open('/home/ubuntu/livekit-agent/agent_retell.py', 'r') as f:
    content = f.read()

# Find the function execution code and add builtin handling
old_code = '''                if url:
                    try:
                        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
                            if method == "GET":
                                response = await client.get(url, headers=headers, params=payload)
                            else:
                                response = await client.post(url, headers=headers, json=payload)

                            try:
                                result = response.json()
                            except:
                                result = {{"response": response.text, "status": response.status_code}}
                    except Exception as e:
                        logger.error(f"Error calling {func_name}: {{e}}")
                        result = {{"error": str(e)}}
                break'''

new_code = '''                if url:
                    try:
                        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
                            if method == "GET":
                                response = await client.get(url, headers=headers, params=payload)
                            else:
                                response = await client.post(url, headers=headers, json=payload)

                            try:
                                result = response.json()
                            except:
                                result = {{"response": response.text, "status": response.status_code}}
                    except Exception as e:
                        logger.error(f"Error calling {func_name}: {{e}}")
                        result = {{"error": str(e)}}
                else:
                    # Handle builtin functions
                    if "{func_name}" == "transfer_call":
                        phone_number = func_cfg.get("phone_number", "")
                        logger.info(f"Executing builtin transfer_call to {{phone_number}}")
                        # Call the API to report the action
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.post(f"{{DASHBOARD_API_URL}}/api/calls/{{self.call_id}}/builtin-action", 
                                    json={{"action": "transfer_call", "phone_number": phone_number}})
                        except Exception as e:
                            logger.error(f"Error reporting transfer: {{e}}")
                        result = {{"success": True, "action": "transfer_call", "phone_number": phone_number}}
                    elif "{func_name}" == "end_call":
                        logger.info(f"Executing builtin end_call")
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.post(f"{{DASHBOARD_API_URL}}/api/calls/{{self.call_id}}/builtin-action",
                                    json={{"action": "end_call"}})
                        except Exception as e:
                            logger.error(f"Error reporting end_call: {{e}}")
                        result = {{"success": True, "action": "end_call"}}
                break'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/home/ubuntu/livekit-agent/agent_retell.py', 'w') as f:
        f.write(content)
    print('Done! Added builtin function execution')
else:
    print('Could not find code to replace')
