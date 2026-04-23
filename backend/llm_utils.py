import os
import logging
import re
import json
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from backend.constants import VALID_LLM_MODELS
from backend.models import AgentModel, FunctionModel

logger = logging.getLogger("backend-api")

def _resolve_openai_client_for_agent_model(model_name: str):
    import openai
    is_moonshot = any(k in (model_name or "").lower() for k in ["moonshot", "kimi", "moonlight"])
    base_url = "https://api.moonshot.cn/v1" if is_moonshot else None
    raw_key = os.getenv("MOONSHOT_API_KEY") if is_moonshot else os.getenv("OPENAI_API_KEY")
    api_key = (raw_key or "").strip() or (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI/Moonshot API key is not configured")
    return openai.OpenAI(api_key=api_key, base_url=base_url)

def _normalize_tool_speech_flags(speak_during: Any, speak_after: Any, fallback_after: bool = True) -> tuple[bool, bool]:
    def _coerce(v):
        if isinstance(v, bool): return v
        if isinstance(v, str): return v.lower() in {"true", "yes", "1"}
        return None

    sd = _coerce(speak_during)
    sa = _coerce(speak_after)
    
    if sd is None: sd = False
    if sa is None: sa = fallback_after
    
    return sd, sa

def _load_agent_runtime_functions(agent: AgentModel, db) -> List[Dict[str, Any]]:
    rows = db.query(FunctionModel).filter(FunctionModel.agent_id == agent.id).all()
    runtime_functions: List[Dict[str, Any]] = []

    for row in rows:
        speak_during, speak_after = _normalize_tool_speech_flags(
            row.speak_during_execution,
            row.speak_after_execution,
            fallback_after=True,
        )
        runtime_functions.append({
            "name": row.name,
            "description": row.description or "",
            "url": row.url or "",
            "method": (row.method or "POST").upper(),
            "timeout_ms": int(row.timeout_ms or 120000),
            "headers": row.headers or {},
            "parameters_schema": row.parameters_schema or {"type": "object", "properties": {}},
            "speak_during_execution": speak_during,
            "speak_after_execution": speak_after,
        })

    from backend.agent_utils import ensure_custom_params
    custom_params = ensure_custom_params(agent.custom_params)
    builtin_cfg = custom_params.get("builtin_functions", {})

    transfer_cfg = builtin_cfg.get("builtin_transfer_call", {})
    if transfer_cfg.get("enabled"):
        transfer_phone = str((transfer_cfg.get("config") or {}).get("phone_number", "")).strip()
        transfer_speak_during, transfer_speak_after = _normalize_tool_speech_flags(
            transfer_cfg.get("speak_during_execution", True),
            transfer_cfg.get("speak_after_execution", False),
            fallback_after=False,
        )
        if not transfer_speak_during and not transfer_speak_after:
            transfer_speak_during, transfer_speak_after = True, False
        runtime_functions.append({
            "name": "transfer_call",
            "description": "Use ONLY when the user explicitly asks to transfer/escalate/connect to a human agent. Do not call this for regular Q&A.",
            "url": "",
            "method": "POST",
            "timeout_ms": 120000,
            "headers": {},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Target phone number in E.164 format, e.g. +447123456789"},
                },
                "required": ["phone_number"],
            },
            "phone_number": transfer_phone,
            "speak_during_execution": transfer_speak_during,
            "speak_after_execution": transfer_speak_after,
        })

    end_call_cfg = builtin_cfg.get("builtin_end_call", {})
    if end_call_cfg.get("enabled"):
        end_speak_during, end_speak_after = _normalize_tool_speech_flags(
            end_call_cfg.get("speak_during_execution", False),
            end_call_cfg.get("speak_after_execution", True),
            fallback_after=True,
        )
        runtime_functions.append({
            "name": "end_call",
            "description": "Use ONLY when the user explicitly confirms they want to end/stop/hang up the conversation.",
            "url": "",
            "method": "POST",
            "timeout_ms": 120000,
            "headers": {},
            "parameters_schema": {"type": "object", "properties": {}},
            "speak_during_execution": end_speak_during,
            "speak_after_execution": end_speak_after,
        })

    return runtime_functions

def _to_openai_tool_definitions(runtime_functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for func in runtime_functions:
        fn_name = str(func.get("name", "")).strip().replace(" ", "_").lower()
        if not fn_name: continue
        speak_during, speak_after = _normalize_tool_speech_flags(
            func.get("speak_during_execution", False),
            func.get("speak_after_execution", True),
            fallback_after=True,
        )
        schema = func.get("parameters_schema") or {"type": "object", "properties": {}}
        base_description = (func.get("description") or "").strip() or fn_name
        if speak_during:
            behavior_hint = "Before calling this tool, tell the user what you are doing; then summarize the result."
        elif speak_after:
            behavior_hint = "Call this tool first, then speak only after receiving its result."
        else:
            behavior_hint = "Keep tool speech concise."
        description = f"{base_description} {behavior_hint}".strip()
        tools.append({
            "type": "function",
            "function": {
                "name": fn_name,
                "description": description,
                "parameters": schema,
            },
        })
    return tools

def _normalize_tool_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")

def _tool_aliases(tool_name: str) -> List[str]:
    normalized = _normalize_tool_name(tool_name)
    aliases = {tool_name or "", normalized, normalized.replace("_", " ")}
    if normalized == "call_transfer":
        aliases.update({"transfer_call", "transfer call"})
    elif normalized == "transfer_call":
        aliases.update({"call_transfer", "call transfer"})
    return [a for a in aliases if a]

def _tool_alias_pattern(alias: str) -> re.Pattern:
    words = [w for w in re.split(r"[^a-z0-9]+", alias.lower()) if w]
    if not words: return re.compile(r"$^")
    separator = r"[\s_\-\.:`'\"()\[\]{}<>]*"
    token = separator.join(re.escape(w) for w in words)
    return re.compile(rf"(?<![a-z0-9]){token}(?![a-z0-9])", re.IGNORECASE)

def _is_tool_mentioned_in_prompt(tool_name: str, prompt: str) -> bool:
    text = (prompt or "").lower()
    if not text: return False
    for alias in _tool_aliases(tool_name):
        if _tool_alias_pattern(alias).search(text):
            return True
    return False

def _filter_runtime_functions_by_prompt(runtime_functions: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    removed_names: List[str] = []
    for fn in runtime_functions or []:
        tool_name = str(fn.get("name", "")).strip()
        if tool_name and _is_tool_mentioned_in_prompt(tool_name, system_prompt):
            filtered.append(fn)
        else:
            removed_names.append(tool_name or "<unknown>")
    if removed_names:
        logger.info("Prompt tool filter removed tools not referenced in system prompt: %s", removed_names)
    return filtered
