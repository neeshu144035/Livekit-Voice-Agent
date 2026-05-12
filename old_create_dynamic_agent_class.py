def create_dynamic_agent_class(functions_config, base_instructions, current_room=None, call_id=None):
    if not functions_config:
        return Agent(instructions=base_instructions)

    class_def = f"""
class DynamicPropertyAgent(Agent):
    def __init__(self, instructions, functions_config, room=None, call_id=None):
        self.functions_config = functions_config
        self.room = room
        self.call_id = call_id
        self._transfer_in_progress = False
        self._pending_end_call_after_speech = False
        self._end_call_handoff_started = False
        super().__init__(instructions=instructions)
"""

    for func in functions_config:
        func_name = func.get("name", "").strip().replace(" ", "_").lower()
        if not func_name:
            continue

        speak_during, speak_after = _normalize_tool_speech_flags(
            func.get("speak_during_execution", False),
            func.get("speak_after_execution", True),
            fallback_after=True,
        )
        speech_mode = "during" if speak_during else "after" if speak_after else "default"
        speech_hint = (
            "Before calling this tool, first tell the caller what you are doing; then share a concise result."
            if speak_during
            else "Call this tool first, then explain the result after it finishes."
        )
        desc = f"{func.get('description', '').strip()} {speech_hint}".strip().replace('"', "'").replace('\n', ' ')

        variables = func.get("variables", {})
        if not variables:
            schema = func.get("parameters_schema", {})
            if isinstance(schema, dict) and "properties" in schema:
                variables = schema.get("properties", {})

        args_def = ["self", "ctx: RunContext"]
        args_dict_str = []
        for v_name, v_info in variables.items():
            clean_v_name = v_name.strip().replace(" ", "_").lower()
            v_desc = str(v_info.get("description", "")).replace('"', "'").replace('\n', ' ')
            v_type = v_info.get("type", "string")
            py_type = "str"
            if v_type in ["integer", "number"]:
                py_type = "int"
            elif v_type == "boolean":
                py_type = "bool"

            args_def.append(f'{clean_v_name}: Annotated[{py_type}, "{v_desc}"] = ""')
            args_dict_str.append(f'"{clean_v_name}": {clean_v_name}')

        args_str = ", ".join(args_def)
        payload_body_str = ", ".join(args_dict_str)

        method_def = f"""
    @function_tool(description="{desc}")
    async def {func_name}({args_str}) -> dict:
        payload = {{ {payload_body_str} }}
        normalized_tool_name = "{func_name}"
        speech_mode = "{speech_mode}"
        # For builtin transfer, force payload phone_number from dashboard config.
        # This prevents model-provided numbers from overriding configured transfer target.
        if normalized_tool_name in ("call_transfer", "transfer_call"):
            for _cfg in self.functions_config:
                if _cfg.get("name", "").strip().replace(" ", "_").lower() == normalized_tool_name:
                    _configured_phone = str(_cfg.get("phone_number", "")).strip()
                    if _configured_phone:
                        payload["phone_number"] = _configured_phone
                    break
        logger.info(f"Tool {func_name} called with args: {{payload}}")

        # Send tool call transcript
        if hasattr(self, 'call_id') and self.call_id:
            try:
                import httpx
                msg = f"[Calling tool: {func_name}] {{json.dumps(payload)}}"
                asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_call", msg))
            except:
                pass

        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_call", "tool_name": "{func_name}", "args": payload, "speech_mode": speech_mode}}),
                    topic="room"
                ))
            except Exception as e:
                logger.error(f"Failed to publish tool_call event: {{e}}")

        result = {{"error": "Tool execution failed"}}

        for func_cfg in self.functions_config:
            if func_cfg.get("name", "").strip().replace(" ", "_").lower() == "{func_name}":
                normalized_name = func_cfg.get("name", "").strip().replace(" ", "_").lower()
                url = func_cfg.get("url", "")
                method = func_cfg.get("method", "POST").upper()
                timeout_ms = func_cfg.get("timeout_ms", 120000)
                headers = func_cfg.get("headers", {{}})

                payload, validation_errors = _validate_and_normalize_tool_payload(payload, func_cfg)
                if validation_errors:
                    result = {{
                        "success": False,
                        "error": "Tool parameter validation failed",
                        "details": validation_errors,
                    }}
                    break

                if normalized_name in ("call_transfer", "transfer_call"):
                    configured_phone = str(func_cfg.get("phone_number", "")).strip()
                    requested_phone = str(payload.get("phone_number", "")).strip()
                    target_phone = configured_phone or requested_phone
                    logger.info(
                        f"transfer_call target resolved: configured={{configured_phone or 'NONE'}} requested={{requested_phone or 'NONE'}} final={{target_phone or 'NONE'}}"
                    )
                    if not target_phone:
                        result = {{"success": False, "error": "Transfer phone number is not configured"}}
                    else:
                        is_valid_phone, transfer_phone_error = _validate_transfer_phone(target_phone)
                        if not is_valid_phone:
                            result = {{"success": False, "error": transfer_phone_error}}
                        elif not self.room:
                            result = {{"success": False, "error": "Room not available for transfer"}}
                        elif self._transfer_in_progress:
                            result = {{"success": False, "error": "Transfer is already in progress"}}
                        else:
                            if hasattr(self, "call_id") and self.call_id:
                                await report_builtin_action(self.call_id, "transfer_call", {{"phone_number": target_phone}})
                            self._transfer_in_progress = True

                            async def _do_handoff():
                                try:
                                    handoff_result = await run_transfer_handoff(
                                        self.room,
                                        getattr(self, "call_id", None),
                                        target_phone,
                                    )
                                    logger.info(f"transfer_call handoff result: {{handoff_result}}")
                                except Exception as handoff_exc:
                                    logger.error(f"transfer_call handoff failed: {{handoff_exc}}")
                                finally:
                                    self._transfer_in_progress = False

                            asyncio.create_task(_do_handoff())
                            result = {{
                                "success": True,
                                "action": "transfer_call",
                                "phone_number": target_phone,
                                "status": "handoff_queued",
                                "message": "Handoff queued; announce transfer to caller now.",
                            }}
                elif normalized_name == "end_call":
                    if hasattr(self, "call_id") and self.call_id:
                        result = await report_builtin_action(
                            self.call_id,
                            "end_call",
                            {{"reason": str(payload.get("reason", "")).strip()}},
                        )
                        if result.get("success") and self.room:
                            if speech_mode == "after":
                                self._pending_end_call_after_speech = True
                                self._end_call_handoff_started = False
                                result["status"] = "awaiting_post_speech_handoff"
                                result["message"] = "Acknowledge the call ending, then hang up."
                            else:
                                self._pending_end_call_after_speech = False
                                self._end_call_handoff_started = True
                                async def _do_end_handoff():
                                    try:
                                        end_handoff_result = await run_end_call_handoff(self.room)
                                        logger.info(f"end_call handoff result: {{end_handoff_result}}")
                                    except Exception as end_handoff_exc:
                                        logger.error(f"end_call handoff failed: {{end_handoff_exc}}")
                                asyncio.create_task(_do_end_handoff())
                    else:
                        result = {{"success": False, "error": "Missing call_id"}}
                elif url:
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
                    result = {{"success": False, "error": "Function URL is empty"}}
                break

        # Send tool response transcript
        if hasattr(self, 'call_id') and self.call_id:
            try:
                import httpx
                msg = f"[Tool response: {func_name}] {{json.dumps(result)}}"
                asyncio.ensure_future(send_transcript_to_api(self.call_id, "tool_response", msg))
            except:
                pass

        if self.room:
            try:
                asyncio.ensure_future(self.room.local_participant.publish_data(
                    json.dumps({{"type": "tool_response", "tool_name": "{func_name}", "response": result}}),
                    topic="room"
                ))
            except:
                pass

        return result
"""
        class_def += method_def

    local_vars = {}
    exec(class_def, globals(), local_vars)
    AgentClass = local_vars["DynamicPropertyAgent"]
    return AgentClass(instructions=base_instructions, functions_config=functions_config, room=current_room, call_id=call_id)


# ==================== SIP Detection ====================

def detect_sip_participant(room):
    for participant in room.remote_participants.values():
        identity = participant.identity or ""
        if identity.startswith("sip_") or "sip" in identity.lower():
            return participant
    return None
