"""
Voice Agent - LLM Tools Module
Handles runtime function execution, tool filtering, and tool speech guidance.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("voice_agent")

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
    if not words:
        return re.compile(r"$^")
    separator = r"[\s_\-\.:`'\"()\[\]{}<>]*"
    token = separator.join(re.escape(w) for w in words)
    return re.compile(rf"(?<![a-z0-9]){token}(?![a-z0-9])", re.IGNORECASE)

def _is_tool_mentioned_in_prompt(tool_name: str, prompt: str) -> bool:
    text = (prompt or "").lower()
    if not text:
        return False
    for alias in _tool_aliases(tool_name):
        if _tool_alias_pattern(alias).search(text):
            return True
    return False

def filter_functions_by_prompt(
    functions_config: List[Dict[str, Any]],
    system_prompt: str,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    removed_names: List[str] = []
    for cfg in functions_config or []:
        tool_name = str(cfg.get("name", "")).strip()
        if tool_name and _is_tool_mentioned_in_prompt(tool_name, system_prompt):
            filtered.append(cfg)
        else:
            removed_names.append(tool_name or "<unknown>")
    if removed_names:
        logger.info("Prompt tool filter removed tools not referenced in system prompt: %s", removed_names)
    return filtered

def _normalize_tool_speech_flags(
    speak_during_execution: Any,
    speak_after_execution: Any,
    *,
    fallback_after: bool = True,
) -> tuple[bool, bool]:
    during = bool(speak_during_execution)
    after = bool(speak_after_execution)
    if during ^ after:
        return during, after
    if fallback_after:
        return False, True
    return False, False

def _tool_speech_instruction_line(func_cfg: Dict[str, Any]) -> str:
    tool_name = str(func_cfg.get("name", "")).strip().replace(" ", "_").lower() or "tool"
    during, after = _normalize_tool_speech_flags(
        func_cfg.get("speak_during_execution", False),
        func_cfg.get("speak_after_execution", True),
        fallback_after=True,
    )
    if during:
        return (
            f"- `{tool_name}`: first tell the caller what you are checking/doing, "
            "then call the tool, then give a concise result summary."
        )
    if after:
        return (
            f"- `{tool_name}`: call silently first, then explain only the result after the tool finishes."
        )
    return f"- `{tool_name}`: default to concise post-tool result only."

def build_tool_speech_guidance(functions_config: List[Dict[str, Any]]) -> str:
    if not functions_config:
        return ""
    lines = [_tool_speech_instruction_line(fn) for fn in functions_config if fn.get("name")]
    if not lines:
        return ""
    return "Tool speech behavior (must follow per tool):\n" + "\n".join(lines)
