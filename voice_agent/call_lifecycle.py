"""
Voice Agent - Call Lifecycle Module
Handles call record creation, usage tracking, and transcript management.
"""

import os
import json
import time
import logging
import atexit
import urllib.request
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from voice_agent.config import DASHBOARD_API_URL, DEFAULT_TTS_PROVIDER, DEEPGRAM_STT_PHONE_MODEL

logger = logging.getLogger("voice_agent")

class UsageTracker:
    """Tracks usage metrics for a call session."""
    
    def __init__(self, call_id: str = ""):
        self.call_id = call_id
        self.llm_tokens_in = 0
        self.llm_tokens_out = 0
        self.llm_model = ""
        self.stt_duration_ms = 0
        self.stt_model = DEEPGRAM_STT_PHONE_MODEL
        self.tts_characters = 0
        self.tts_provider = DEFAULT_TTS_PROVIDER
        self.tts_model = ""
        self.tts_voice_id = ""
        self.llm_temperature = 0.2
        self.voice_speed = 1.0
        self.language = ""
        self.call_start_unix_ms = int(time.time() * 1000)
        self.transcript_entries: List[Dict[str, str]] = []
        self.assistant_texts: List[str] = []
        self.call_start_time = time.time()
        self.usage_sent = False
    
    def add_llm_usage(self, tokens_in: int = 0, tokens_out: int = 0, model: str = ""):
        self.llm_tokens_in += tokens_in
        self.llm_tokens_out += tokens_out
        if model:
            self.llm_model = model
    
    def add_stt_duration(self, duration_ms: int):
        self.stt_duration_ms += duration_ms
    
    def add_tts_characters(self, chars: int):
        self.tts_characters += chars
    
    def add_transcript(self, role: str, content: str):
        if self.transcript_entries:
            last_entry = self.transcript_entries[-1]
            if last_entry.get("role") == role and last_entry.get("content") == content:
                return
        self.transcript_entries.append({"role": role, "content": content})
        if role == "agent":
            self.assistant_texts.append(content)
    
    def get_transcript_summary(self) -> str:
        if not self.transcript_entries:
            return ""
        lines = []
        for entry in self.transcript_entries[-10:]:
            prefix = "Agent" if entry["role"] == "agent" else "User"
            lines.append(f"{prefix}: {entry['content'][:100]}")
        return "\n".join(lines)
    
    def get_call_duration(self) -> int:
        return int(time.time() - self.call_start_time)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "llm_tokens_in": self.llm_tokens_in,
            "llm_tokens_out": self.llm_tokens_out,
            "actual_llm_tokens_in": self.llm_tokens_in,
            "actual_llm_tokens_out": self.llm_tokens_out,
            "llm_model_used": self.llm_model,
            "stt_duration_ms": self.stt_duration_ms,
            "actual_stt_minutes": round((self.stt_duration_ms or 0) / 60000.0, 6),
            "stt_model_used": self.stt_model,
            "tts_characters": self.tts_characters,
            "actual_tts_characters": self.tts_characters,
            "tts_provider": self.tts_provider,
            "tts_model_used": self.tts_model,
            "tts_voice_id_used": self.tts_voice_id,
            "llm_temperature": self.llm_temperature,
            "voice_speed": self.voice_speed,
            "language": self.language,
            "transcript_summary": self.get_transcript_summary(),
            "actual_duration_seconds": self.get_call_duration(),
        }

_active_call_id: Optional[str] = None
_active_usage: Optional[UsageTracker] = None

def _send_usage_sync(call_id: str, tracker: UsageTracker):
    """Synchronous usage sender for atexit handler"""
    if not call_id or tracker.usage_sent:
        return
    
    payload = tracker.to_payload()
    
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if getattr(resp, "status", 200) >= 400:
                raise RuntimeError(f"HTTP {resp.status}")
            tracker.usage_sent = True
            logger.info(f"[atexit] Sent usage for {call_id}")
    except Exception as e:
        logger.error(f"[atexit] Failed to send usage: {e}")
    
    # Also end the call
    try:
        req2 = urllib.request.Request(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/end",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req2, timeout=5)
    except:
        pass

def _atexit_handler():
    global _active_call_id, _active_usage
    if _active_call_id and _active_usage:
        logger.info(f"[atexit] Sending final usage for {_active_call_id}")
        _send_usage_sync(_active_call_id, _active_usage)

atexit.register(_atexit_handler)

async def send_transcript_to_api(call_id: str, role: str, content: str):
    """Send transcript entry to dashboard API."""
    if not call_id:
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/transcript",
                json={"role": role, "content": content, "is_final": True},
            )
    except Exception as e:
        logger.error(f"Error sending transcript: {e}")

async def send_usage_to_api(call_id: str, tracker: UsageTracker):
    """Send usage metrics to dashboard API."""
    if not call_id or tracker.usage_sent:
        return
    
    payload = tracker.to_payload()
    
    sent = False
    for attempt in range(1, 4):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
                    json=payload,
                )
                resp.raise_for_status()
                sent = True
                tracker.usage_sent = True
                logger.info(f"Sent usage for {call_id} on attempt {attempt}")
                break
        except Exception as e:
            logger.error(f"Error sending usage for {call_id} (attempt {attempt}/3): {e}")
            await asyncio.sleep(0.6 * attempt)
    
    if not sent:
        logger.error(f"Usage delivery failed after retries for {call_id}")

async def create_call_record(
    room_name: str,
    agent_id: int,
    direction: str = "outbound",
    from_number: Optional[str] = None,
    to_number: Optional[str] = None,
) -> Tuple[Optional[str], Optional[int], Dict[str, Any]]:
    """Create a call record in the dashboard."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/create-from-agent",
                json={
                    "room_name": room_name,
                    "agent_id": agent_id,
                    "direction": direction,
                    "call_type": "phone" if direction == "inbound" or from_number or to_number else "web",
                    "from_number": from_number,
                    "to_number": to_number,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            resolved_agent_id = data.get("agent_id")
            try:
                resolved_agent_id = int(resolved_agent_id) if resolved_agent_id is not None else None
            except Exception:
                resolved_agent_id = None
            metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            return data.get("call_id", ""), resolved_agent_id, metadata
    except Exception as e:
        logger.error(f"Error creating call record: {e}")
        return "", None, {}

async def end_call_record(call_id: str):
    """Mark a call as ended in the dashboard."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{DASHBOARD_API_URL}/api/calls/{call_id}/end")
    except Exception as e:
        logger.error(f"Error ending call: {e}")
