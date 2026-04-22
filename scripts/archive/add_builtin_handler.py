with open('/home/ubuntu/livekit-agent/agent_retell.py', 'r') as f:
    lines = f.readlines()

# Find line 329 (the "break" line after the if url: block)
# and insert the else clause before it
insert_lines = '''                else:
                    # Handle builtin functions
                    if "{func_name}" == "transfer_call":
                        phone_number = func_cfg.get("phone_number", "")
                        logger.info(f"Executing builtin transfer_call to {{phone_number}}")
                        
                        # Report to API
                        if hasattr(self, 'call_id') and self.call_id:
                            try:
                                await report_builtin_action(self.call_id, "transfer_call", {{"phone_number": phone_number}})
                            except Exception as e:
                                logger.error(f"Error reporting transfer: {{e}}")
                        
                        # Dial via SIP
                        try:
                            if hasattr(self, 'room') and self.room and phone_number:
                                room_name = self.room.name
                                logger.info(f"Initiating SIP transfer to {{phone_number}} from room {{room_name}}")
                                
                                # Use LiveKit SIP to dial
                                import httpx as httpx2
                                async with httpx2.AsyncClient() as client2:
                                    # First get available trunks
                                    trunks_resp = await client2.post(
                                        "http://livekit-server:7880/twirp/livekit.SIP/ListSIPTrunk",
                                        json={{}},
                                        timeout=10.0
                                    )
                                    
                                    if trunks_resp.status_code == 200:
                                        trunks_data = trunks_resp.json()
                                        trunk_id = None
                                        
                                        for trunk in trunks_data.get("items", []):
                                            if trunk.get("outbound"):
                                                trunk_id = trunk.get("sipTrunkId")
                                                break
                                        
                                        if trunk_id:
                                            dial_payload = {{
                                                "sipTrunkId": trunk_id,
                                                "roomName": room_name,
                                                "participantIdentity": f"transfer_{{phone_number}}",
                                                "sipCallTo": phone_number
                                            }}
                                            
                                            dial_resp = await client2.post(
                                                "http://livekit-server:7880/twirp/livekit.SIP/CreateSIPParticipant",
                                                json=dial_payload,
                                                timeout=30.0
                                            )
                                            
                                            if dial_resp.status_code == 200:
                                                logger.info(f"Successfully initiated transfer to {{phone_number}}")
                                                result = {{"success": True, "action": "transfer_call", "phone_number": phone_number, "status": "dialing"}}
                                            else:
                                                error_text = dial_resp.text
                                                logger.error(f"Failed to dial {{phone_number}}: {{error_text}}")
                                                result = {{"success": False, "error": f"Dial failed: {{error_text}}"}}
                                        else:
                                            logger.error("No outbound SIP trunk found")
                                            result = {{"success": False, "error": "No outbound trunk"}}
                                    else:
                                        logger.error(f"Failed to list SIP trunks: {{trunks_resp.text}}")
                                        result = {{"success": False, "error": "Failed to get trunks"}}
                            else:
                                logger.warning("No room or phone number for transfer")
                                result = {{"success": True, "action": "transfer_call", "phone_number": phone_number, "status": "reported_only"}}
                        except Exception as e:
                            logger.error(f"Error during SIP transfer: {{e}}")
                            result = {{"success": False, "error": str(e)}}
                    
                    elif "{func_name}" == "end_call":
                        logger.info(f"Executing builtin end_call")
                        if hasattr(self, 'call_id') and self.call_id:
                            try:
                                await report_builtin_action(self.call_id, "end_call", {{}})
                            except Exception as e:
                                logger.error(f"Error reporting end_call: {{e}}")
                        result = {{"success": True, "action": "end_call"}}
'''

# Find the line with "break" after the if url: block
for i, line in enumerate(lines):
    if i > 320 and 'break' in line and '                break' == line.rstrip():
        # Insert before this line
        lines.insert(i, insert_lines)
        break

with open('/home/ubuntu/livekit-agent/agent_retell.py', 'w') as f:
    f.writelines(lines)

print('Done!')
