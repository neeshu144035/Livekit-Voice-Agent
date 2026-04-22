import os
import json
import asyncio
import logging
import time
import atexit
import signal
import re
import uuid
from dotenv import load_dotenv
from typing import Annotated, Optional, Dict, Any, List

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import deepgram, openai, silero, elevenlabs
import livekit.agents.llm as llm_module
import httpx

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-retell")

DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://host.docker.internal:8000").rstrip("/")
MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "1800"))
DEFAULT_TTS_PROVIDER = "deepgram"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"
TRANSFER_HANDOFF_DELAY_SEC = float(os.getenv("TRANSFER_HANDOFF_DELAY_SEC", "2.5"))

DEEPGRAM_VOICE_MAP = {
    "jessica": "aura-asteria-en",
    "mark": "aura-orion-en",
    "sarah": "aura-luna-en",
    "michael": "aura-perseus-en",
    "emma": "aura-hera-en",
    "james": "aura-zeus-en",
}


def get_elevenlabs_api_key() -> str:
    return (os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY") or "").strip()


def normalize_tts_provider(config: Dict[str, Any]) -> str:
    custom_params = config.get("custom_params") or {}
    provider = (
        config.get("tts_provider")
        or custom_params.get("tts_provider")
        or DEFAULT_TTS_PROVIDER
    )
    provider = str(provider).strip().lower()
    if provider not in ("deepgram", "elevenlabs"):
        provider = DEFAULT_TTS_PROVIDER
    return provider


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def sum_usage_series(usage_payload: Dict[str, Any], key: Optional[str] = None) -> float:
    usage_map = usage_payload.get("usage") or {}
    if not usage_map:
        return 0.0

    if key and key in usage_map:
        series = usage_map.get(key) or []
        return float(series[-1]) if series else 0.0

    if "All" in usage_map:
        series = usage_map.get("All") or []
        return float(series[-1]) if series else 0.0

    total = 0.0
    for series in usage_map.values():
        if series:
            total += float(series[-1])
    return total


async def fetch_elevenlabs_character_stats(
    api_key: str,
    start_unix_ms: int,
    end_unix_ms: int,
    metric: str,
    breakdown_type: str,
) -> Dict[str, Any]:
    params = {
        "start_unix": start_unix_ms,
        "end_unix": end_unix_ms,
        "aggregation_interval": "cumulative",
        "metric": metric,
        "breakdown_type": breakdown_type,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/usage/character-stats",
            params=params,
            headers={"xi-api-key": api_key},
        )
        resp.raise_for_status()
        return resp.json() or {}


async def fetch_elevenlabs_history_items(
    api_key: str,
    start_unix_ms: int,
    end_unix_ms: int,
    voice_id: Optional[str],
    model_id: Optional[str],
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "page_size": 1000,
        "date_after_unix": int(start_unix_ms / 1000) - 2,
        "date_before_unix": int(end_unix_ms / 1000) + 2,
        "sort_direction": "asc",
        "source": "TTS",
    }
    if voice_id:
        params["voice_id"] = voice_id
    if model_id:
        params["model_id"] = model_id

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/history",
            params=params,
            headers={"xi-api-key": api_key},
        )
        resp.raise_for_status()
        payload = resp.json() or {}

    # ElevenLabs may return "history" or "items" depending on API generation.
    rows = payload.get("history")
    if rows is None:
        rows = payload.get("items")
    return rows or []


def estimate_call_characters_from_history(
    history_items: List[Dict[str, Any]],
    assistant_texts: List[str],
) -> Dict[str, int]:
    normalized_texts = [normalize_text(text) for text in assistant_texts if normalize_text(text)]
    total_chars = 0
    matched_chars = 0

    for row in history_items:
        start_count = row.get("character_count_change_from") or 0
        end_count = row.get("character_count_change_to") or 0
        char_count = max(int(end_count) - int(start_count), 0)
        if char_count <= 0:
            continue

        total_chars += char_count
        history_text = normalize_text(row.get("text") or "")
        if not history_text:
            continue

        if any(
            history_text == text
            or history_text in text
            or text in history_text
            for text in normalized_texts
        ):
            matched_chars += char_count

    if matched_chars <= 0 and total_chars > 0:
        matched_chars = total_chars

    return {
        "matched_chars": matched_chars,
        "total_chars": total_chars,
    }


# ==================== Usage Tracking (Global for atexit) ====================
_active_call_id = None
_active_usage = None

class UsageTracker:
    def __init__(self):
        self.llm_tokens_in = 0
        self.llm_tokens_out = 0
        self.llm_model = ""
        self.stt_duration_ms = 0
        self.tts_characters = 0
        self.tts_provider = DEFAULT_TTS_PROVIDER
        self.tts_model = ""
        self.tts_voice_id = ""
        self.call_start_unix_ms = int(time.time() * 1000)
        self.transcript_entries = []
        self.assistant_texts = []
        self.call_start_time = time.time()
        self.usage_sent = False

    def add_llm_usage(self, tokens_in=0, tokens_out=0, model=""):
        self.llm_tokens_in += tokens_in
        self.llm_tokens_out += tokens_out
        if model:
            self.llm_model = model

    def add_stt_duration(self, duration_ms):
        self.stt_duration_ms += duration_ms

    def add_tts_characters(self, chars):
        self.tts_characters += chars

    def add_transcript(self, role, content):
        self.transcript_entries.append({"role": role, "content": content})
        if role == "agent":
            self.assistant_texts.append(content)

    def get_transcript_summary(self):
        if not self.transcript_entries:
            return ""
        lines = []
        for entry in self.transcript_entries[-10:]:
            prefix = "Agent" if entry["role"] == "agent" else "User"
            lines.append(f"{prefix}: {entry['content'][:100]}")
        return "\n".join(lines)

    def get_call_duration(self):
        return int(time.time() - self.call_start_time)


def _send_usage_sync(call_id, tracker):
    """Synchronous usage sender for atexit handler"""
    if tracker.usage_sent:
        return
    tracker.usage_sent = True
    import urllib.request
    try:
        data = json.dumps({
            "llm_tokens_in": tracker.llm_tokens_in,
            "llm_tokens_out": tracker.llm_tokens_out,
            "llm_model_used": tracker.llm_model,
            "stt_duration_ms": tracker.stt_duration_ms,
            "tts_characters": tracker.tts_characters,
            "tts_provider": tracker.tts_provider,
            "tts_model_used": tracker.tts_model,
            "transcript_summary": tracker.get_transcript_summary(),
            "actual_duration_seconds": tracker.get_call_duration(),
        }).encode()
        req = urllib.request.Request(
            f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
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


# ==================== API Helpers ====================

async def send_transcript_to_api(call_id, role, content):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/transcript",
                json={"role": role, "content": content, "is_final": True}
            )
    except Exception as e:
        logger.error(f"Error sending transcript: {e}")


async def send_usage_to_api(call_id, tracker):
    if tracker.usage_sent:
        return
    tracker.usage_sent = True

    payload: Dict[str, Any] = {
        "llm_tokens_in": tracker.llm_tokens_in,
        "llm_tokens_out": tracker.llm_tokens_out,
        "llm_model_used": tracker.llm_model,
        "stt_duration_ms": tracker.stt_duration_ms,
        "tts_characters": tracker.tts_characters,
        "tts_provider": tracker.tts_provider,
        "tts_model_used": tracker.tts_model,
        "transcript_summary": tracker.get_transcript_summary(),
        "actual_duration_seconds": tracker.get_call_duration(),
    }

    if tracker.tts_provider == "elevenlabs":
        eleven_api_key = get_elevenlabs_api_key()
        if not eleven_api_key:
            logger.warning("ElevenLabs provider selected but ELEVEN_API_KEY is missing")
        else:
            end_unix_ms = int(time.time() * 1000)
            try:
                history_items = await fetch_elevenlabs_history_items(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    voice_id=tracker.tts_voice_id or None,
                    model_id=tracker.tts_model or None,
                )
                history_char_usage = estimate_call_characters_from_history(
                    history_items=history_items,
                    assistant_texts=tracker.assistant_texts,
                )
                matched_call_chars = history_char_usage["matched_chars"] or tracker.tts_characters
                payload["actual_tts_characters"] = matched_call_chars
                payload["tts_characters"] = matched_call_chars

                model_key = tracker.tts_model or DEFAULT_ELEVENLABS_MODEL
                chars_metric = await fetch_elevenlabs_character_stats(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    metric="tts_characters",
                    breakdown_type="model",
                )
                fiat_metric = await fetch_elevenlabs_character_stats(
                    api_key=eleven_api_key,
                    start_unix_ms=tracker.call_start_unix_ms,
                    end_unix_ms=end_unix_ms,
                    metric="fiat_units_spent",
                    breakdown_type="model",
                )
                total_model_chars = sum_usage_series(chars_metric, model_key)
                total_model_cost = sum_usage_series(fiat_metric, model_key)
                if total_model_chars <= 0:
                    total_model_chars = sum_usage_series(chars_metric)
                if total_model_cost <= 0:
                    total_model_cost = sum_usage_series(fiat_metric)

                if total_model_chars > 0 and total_model_cost >= 0:
                    usage_ratio = min(matched_call_chars / total_model_chars, 1.0)
                    payload["actual_tts_cost_usd"] = round(total_model_cost * usage_ratio, 8)
                    payload["tts_cost_source"] = "elevenlabs_usage_character_stats"
                logger.info(
                    "ElevenLabs usage captured: call_chars=%s window_chars=%s window_cost=%s",
                    matched_call_chars,
                    total_model_chars,
                    total_model_cost,
                )
            except Exception as e:
                logger.error(f"Failed to fetch ElevenLabs usage metrics: {e}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/usage",
                json=payload,
            )
            logger.info(f"Sent usage for {call_id}: tokens={tracker.llm_tokens_in}/{tracker.llm_tokens_out}")
    except Exception as e:
        logger.error(f"Error sending usage: {e}")


async def create_call_record(room_name, agent_id, direction="outbound",
                              from_number=None, to_number=None):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/create-from-agent",
                json={
                    "room_name": room_name,
                    "agent_id": agent_id,
                    "direction": direction,
                    "call_type": "phone" if from_number or to_number else "web",
                    "from_number": from_number,
                    "to_number": to_number,
                }
            )
            data = resp.json()
            return data.get("call_id", "")
    except Exception as e:
        logger.error(f"Error creating call record: {e}")
        return ""


async def end_call_record(call_id):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{DASHBOARD_API_URL}/api/calls/{call_id}/end")
    except Exception as e:
        logger.error(f"Error ending call: {e}")


# ==================== Agent Config ====================

def prewarm(proc: JobProcess):
    # Load VAD with more aggressive settings for faster response
    vad = silero.VAD.load()
    proc.userdata["vad"] = vad


async def fetch_agent_config(agent_id):
    url = f"{DASHBOARD_API_URL}/api/agents/{agent_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
        return {
            "name": "Sarah",
            "system_prompt": "You are Sarah, a helpful voice assistant.",
            "llm_model": "gpt-4o-mini",
            "voice": "sarah",
            "language": "en-GB"
        }


async def fetch_agent_by_phone(phone_number):
    url = f"{DASHBOARD_API_URL}/api/agents/by-phone/{phone_number}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Error fetching agent by phone: {e}")
    return None


async def fetch_agent_functions(agent_id):
    url = f"{DASHBOARD_API_URL}/api/agents/{agent_id}/functions"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Error fetching functions: {e}")
        return []


async def report_builtin_action(call_id: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Report built-in tool action execution back to dashboard API."""
    if not call_id:
        return {"success": False, "error": "Missing call_id"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{DASHBOARD_API_URL}/api/calls/{call_id}/builtin-action",
                json={"action": action, "parameters": parameters},
            )
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return {"success": True, "status_code": resp.status_code}
        return {"success": False, "status_code": resp.status_code, "detail": resp.text}
    except Exception as e:
        logger.error(f"Error reporting builtin action {action}: {e}")
        return {"success": False, "error": str(e)}


def _normalize_phone(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value).strip())


def _validate_transfer_phone(phone_number: str) -> tuple[bool, str]:
    """Basic E.164 validation plus guardrails for common formatting mistakes."""
    normalized = _normalize_phone(phone_number)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        return False, "Transfer number must be valid E.164 format (example: +447123456789)"

    # Common invalid pattern we observed in production: India numbers with 11 local digits.
    # India mobile format is +91 followed by 10 digits.
    if normalized.startswith("+91") and len(normalized) != 13:
        return False, "India transfer numbers must be +91 followed by exactly 10 digits"

    return True, ""


def _room_has_participant_identity(room: Any, participant_identity: str) -> bool:
    if not room or not participant_identity:
        return False
    try:
        for participant in room.remote_participants.values():
            if (getattr(participant, "identity", "") or "") == participant_identity:
                return True
    except Exception:
        return False
    return False


async def resolve_transfer_outbound_trunk_id(
    call_id: Optional[str],
    default_trunk_id: str,
) -> tuple[str, str]:
    """
    Resolve outbound trunk for transfer by matching active call's from_number
    to configured phone number records; fallback to provided default trunk.
    """
    if not call_id:
        return default_trunk_id, "default:first_trunk"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            details_resp = await client.get(f"{DASHBOARD_API_URL}/api/call-history/{call_id}/details")
            if details_resp.status_code != 200:
                return default_trunk_id, f"fallback:call_details_http_{details_resp.status_code}"
            details = details_resp.json() or {}
            from_number = _normalize_phone((details.get("call") or {}).get("from_number"))
            if not from_number:
                return default_trunk_id, "fallback:no_from_number"

            phones_resp = await client.get(f"{DASHBOARD_API_URL}/api/phone-numbers/")
            if phones_resp.status_code != 200:
                # Compatibility fallback if proxy/app rewrites trailing slash.
                phones_resp = await client.get(f"{DASHBOARD_API_URL}/api/phone-numbers")
            if phones_resp.status_code != 200:
                return default_trunk_id, f"fallback:phone_numbers_http_{phones_resp.status_code}"

            phone_rows = phones_resp.json() or []
            for row in phone_rows:
                row_num = _normalize_phone(row.get("phone_number"))
                trunk_id = str(row.get("livekit_outbound_trunk_id") or "").strip()
                if row_num == from_number and trunk_id:
                    return trunk_id, f"matched_phone:{from_number}"

            return default_trunk_id, f"fallback:no_phone_match:{from_number}"
    except Exception as e:
        logger.warning(f"Failed to resolve transfer trunk from call context: {e}")
        return default_trunk_id, "fallback:exception"


async def start_sip_transfer(
    room_name: str,
    phone_number: str,
    call_id: Optional[str] = None,
    room: Any = None,
) -> Dict[str, Any]:
    """Dial transfer target into the current room via LiveKit SIP outbound trunk."""
    try:
        from livekit import api as livekit_api

        phone_number = _normalize_phone(phone_number)
        is_valid, validation_error = _validate_transfer_phone(phone_number)
        if not is_valid:
            return {"success": False, "error": validation_error}

        lk_url = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880").replace("wss://", "https://").replace("ws://", "http://")
        lk_api = livekit_api.LiveKitAPI(
            url=lk_url,
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678"),
        )

        try:
            trunks_resp = await lk_api.sip.list_sip_outbound_trunk(livekit_api.ListSIPOutboundTrunkRequest())
            if not trunks_resp.items:
                return {"success": False, "error": "No outbound trunk configured"}

            default_trunk_id = trunks_resp.items[0].sip_trunk_id
            trunk_id, trunk_source = await resolve_transfer_outbound_trunk_id(call_id, default_trunk_id)
            logger.info(
                f"Transfer dialing request: room={room_name}, to={phone_number}, trunk_id={trunk_id}, source={trunk_source}"
            )
            participant_identity = f"transfer_{uuid.uuid4().hex[:8]}"
            await lk_api.sip.create_sip_participant(
                livekit_api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=phone_number,
                    room_name=room_name,
                    participant_identity=participant_identity,
                    play_ringtone=True,
                )
            )

            if room:
                joined = False
                for _ in range(25):
                    if _room_has_participant_identity(room, participant_identity):
                        joined = True
                        break
                    await asyncio.sleep(0.1)

                if not joined:
                    return {
                        "success": False,
                        "action": "transfer_call",
                        "phone_number": phone_number,
                        "status": "failed",
                        "error": "Transfer participant did not join room; check target number/trunk settings",
                        "trunk_id": trunk_id,
                        "trunk_source": trunk_source,
                        "participant_identity": participant_identity,
                    }

                await asyncio.sleep(1.0)
                if not _room_has_participant_identity(room, participant_identity):
                    return {
                        "success": False,
                        "action": "transfer_call",
                        "phone_number": phone_number,
                        "status": "failed",
                        "error": "Transfer dial leg dropped immediately; verify destination number format and trunk dialing permissions",
                        "trunk_id": trunk_id,
                        "trunk_source": trunk_source,
                        "participant_identity": participant_identity,
                    }

            return {
                "success": True,
                "action": "transfer_call",
                "phone_number": phone_number,
                "status": "dialing",
                "trunk_id": trunk_id,
                "trunk_source": trunk_source,
                "participant_identity": participant_identity,
            }
        finally:
            await lk_api.aclose()
    except Exception as e:
        logger.error(f"SIP transfer failed: {e}")
        return {"success": False, "error": str(e)}


async def remove_room_participant(room_name: str, participant_identity: str) -> Dict[str, Any]:
    """Force-remove participant from room using RoomService API."""
    if not room_name or not participant_identity:
        return {"success": False, "error": "Missing room_name or participant_identity"}

    try:
        from livekit import api as livekit_api

        lk_url = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880").replace("wss://", "https://").replace("ws://", "http://")
        lk_api = livekit_api.LiveKitAPI(
            url=lk_url,
            api_key=os.getenv("LIVEKIT_API_KEY", "devkey"),
            api_secret=os.getenv("LIVEKIT_API_SECRET", "secret12345678"),
        )
        try:
            await lk_api.room.remove_participant(
                livekit_api.RoomParticipantIdentity(room=room_name, identity=participant_identity)
            )
            return {"success": True}
        finally:
            await lk_api.aclose()
    except Exception as e:
        logger.error(f"Failed to remove participant {participant_identity} from {room_name}: {e}")
        return {"success": False, "error": str(e)}


async def run_transfer_handoff(
    room: Any,
    call_id: Optional[str],
    target_phone: str,
    delay_sec: float = TRANSFER_HANDOFF_DELAY_SEC,
) -> Dict[str, Any]:
    """Delay handoff slightly so assistant can announce transfer, then disconnect assistant."""
    if delay_sec > 0:
        await asyncio.sleep(delay_sec)

    transfer_result = await start_sip_transfer(room.name, target_phone, call_id, room)
    if not transfer_result.get("success"):
        return transfer_result

    agent_identity = ""
    try:
        agent_identity = (getattr(room.local_participant, "identity", "") or "").strip()
    except Exception:
        agent_identity = ""

    if not agent_identity:
        transfer_result["agent_removed"] = {"success": False, "error": "Unable to resolve local agent identity"}
        return transfer_result

    transfer_result["agent_removed"] = await remove_room_participant(room.name, agent_identity)
    return transfer_result


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
        super().__init__(instructions=instructions)
"""

    for func in functions_config:
        func_name = func.get("name", "").strip().replace(" ", "_").lower()
        if not func_name:
            continue

        desc = func.get("description", "").replace('"', "'").replace('\n', ' ')

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
                    json.dumps({{"type": "tool_call", "tool_name": "{func_name}", "args": payload}}),
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


def get_sip_phone_numbers(participant):
    from_number = None
    to_number = None
    if hasattr(participant, 'attributes') and participant.attributes:
        attrs = participant.attributes
        from_number = attrs.get("sip.callerNumber") or attrs.get("sip.from", "")
        to_number = attrs.get("sip.calledNumber") or attrs.get("sip.to", "")
    return from_number, to_number


# ==================== Transcript Collector ====================

class TranscriptCollector:
    """Collects transcripts by monitoring chat context changes"""
    def __init__(self, call_id, usage, llm_model):
        self.call_id = call_id
        self.usage = usage
        self.llm_model = llm_model
        self.last_user_msg_count = 0
        self.last_agent_msg_count = 0
        self._running = True
        self._session = None

    def set_session(self, session):
        self._session = session

    def stop(self):
        self._running = False

    async def monitor_chat_context(self, session):
        """Periodically check chat context for new messages"""
        self._session = session
        seen_messages = set()
        
        while self._running:
            try:
                await asyncio.sleep(1)
                if not self._session:
                    continue
                    
                # Access chat context correctly - session.agent.chat_ctx
                ctx = None
                try:
                    if hasattr(self._session, 'agent') and self._session.agent:
                        agent = self._session.agent
                        if hasattr(agent, 'chat_ctx'):
                            ctx = agent.chat_ctx
                        else:
                            logger.debug(f"No chat_ctx on agent: {dir(agent)[:50]}")
                    else:
                        logger.debug(f"No agent on session or session.agent is None")
                except Exception as e:
                    logger.debug(f"Error getting chat_ctx: {e}")
                
                if not ctx:
                    continue
                
                logger.debug(f"Got chat_ctx: {type(ctx)}, items: {hasattr(ctx, 'items')}")
                
                messages = []
                if hasattr(ctx, 'items'):
                    messages = ctx.items
                elif hasattr(ctx, 'messages'):
                    messages = ctx.messages
                
                for msg in messages:
                    role = getattr(msg, 'role', '')
                    content = ''
                    if hasattr(msg, 'content'):
                        if isinstance(msg.content, str):
                            content = msg.content
                        elif isinstance(msg.content, list):
                            content = ' '.join(str(c) for c in msg.content if c)
                    elif hasattr(msg, 'text'):
                        content = msg.text
                    
                    if not content or role == 'system':
                        continue
                    
                    msg_key = f"{role}:{content[:50]}"
                    if msg_key in seen_messages:
                        continue
                    seen_messages.add(msg_key)
                    
                    if role == 'user':
                        word_count = len(content.split())
                        est_duration = int((word_count / 150.0) * 60 * 1000)
                        self.usage.add_stt_duration(est_duration)
                        self.usage.add_llm_usage(tokens_in=len(content) // 4, model=self.llm_model)
                        self.usage.add_transcript("user", content)
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "user", content))
                        logger.info(f"[transcript] User: {content[:60]}...")
                    elif role == 'assistant':
                        self.usage.add_tts_characters(len(content))
                        self.usage.add_llm_usage(tokens_out=len(content) // 4, model=self.llm_model)
                        self.usage.add_transcript("agent", content)
                        asyncio.ensure_future(send_transcript_to_api(self.call_id, "agent", content))
                        logger.info(f"[transcript] Agent: {content[:60]}...")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Monitor error: {e}")
                await asyncio.sleep(2)


# ==================== Main Entrypoint ====================

async def entrypoint(ctx: JobContext):
    global _active_call_id, _active_usage

    logger.info(f"Starting session for room: {ctx.room.name}")

    usage = UsageTracker()
    call_id = None
    agent_id = 5
    direction = "outbound"
    from_number = None
    to_number = None

    try:
        room_name = ctx.room.name
        logger.info(f"Extracting agent_id from room: {room_name}")

        if room_name.startswith("call_"):
            parts = room_name.split("_")
            if len(parts) >= 3 and parts[1].isdigit():
                try:
                    agent_id = int(parts[1])
                    direction = "outbound"
                    logger.info(f"Web/outbound call for agent_id: {agent_id}")
                except:
                    agent_id = 5
            else:
                # Room like "call_sarah" from dispatch rule - treat as inbound
                direction = "inbound"
                logger.info(f"Inbound call (dispatch room): {room_name}")
        elif room_name.startswith("call-") or room_name.startswith("sip-"):
            direction = "inbound"
            logger.info(f"Inbound call detected: {room_name}")
        else:
            parts = room_name.split("_")
            if len(parts) > 1:
                try:
                    agent_id = int(parts[1])
                except:
                    agent_id = 5
    except Exception as e:
        logger.error(f"Error parsing room name: {e}")

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    if direction == "inbound":
        await asyncio.sleep(1)
        sip_participant = detect_sip_participant(ctx.room)
        if sip_participant:
            from_number, to_number = get_sip_phone_numbers(sip_participant)
            logger.info(f"Inbound from: {from_number} to: {to_number}")
            if to_number:
                phone_agent = await fetch_agent_by_phone(to_number)
                if phone_agent:
                    agent_id = phone_agent.get("agent_id", agent_id)

    # Create call record
    call_id = await create_call_record(
        room_name=ctx.room.name,
        agent_id=agent_id,
        direction=direction,
        from_number=from_number,
        to_number=to_number,
    )
    logger.info(f"Call record created: {call_id}")

    # Register for atexit cleanup
    _active_call_id = call_id
    _active_usage = usage

    # Fetch config
    config = await fetch_agent_config(agent_id)
    functions = await fetch_agent_functions(agent_id)
    
    # Add builtin functions from custom_params
    custom_params = config.get('custom_params', {})
    builtin_funcs = custom_params.get('builtin_functions', {})
    
    if builtin_funcs.get('builtin_transfer_call', {}).get('enabled'):
        transfer_cfg = builtin_funcs['builtin_transfer_call'].get('config', {})
        phone_number = transfer_cfg.get('phone_number', '')
        functions.append({
            'name': 'transfer_call',
            'description': 'Transfer the call to a human. Use this when caller wants to buy.',
            'url': '',
            'method': 'POST',
            'parameters_schema': {
                'type': 'object',
                'properties': {
                    'phone_number': {'type': 'string', 'description': 'The phone number to transfer to'}
                },
                'required': ['phone_number']
            },
            'phone_number': phone_number
        })
        logger.info(f"Added builtin transfer_call function with phone: {phone_number}")
    
    if builtin_funcs.get('builtin_end_call', {}).get('enabled'):
        functions.append({
            'name': 'end_call',
            'description': 'End the call politely.',
            'url': '',
            'method': 'POST',
            'parameters_schema': {'type': 'object', 'properties': {}}
        })
        logger.info(f"Added builtin end_call function")
    
    logger.info(f"Agent: {config.get('name')}, Functions: {len(functions)}")

    # Voice / TTS provider config
    selected_voice = config.get("voice", "jessica")
    tts_provider = normalize_tts_provider(config)
    selected_tts_model = (
        config.get("tts_model")
        or (config.get("custom_params") or {}).get("tts_model")
    )

    tts_engine = None
    resolved_voice_id = selected_voice
    if tts_provider == "elevenlabs":
        eleven_key = get_elevenlabs_api_key()
        selected_tts_model = selected_tts_model or DEFAULT_ELEVENLABS_MODEL
        if not eleven_key:
            raise RuntimeError("ElevenLabs selected but ELEVEN_API_KEY / ELEVENLABS_API_KEY is not set")

        tts_engine = elevenlabs.TTS(
            voice_id=selected_voice,
            model=selected_tts_model,
            api_key=eleven_key,
            enable_logging=True,
        )
        resolved_voice_id = selected_voice

    if tts_provider == "deepgram":
        mapped_voice = DEEPGRAM_VOICE_MAP.get(str(selected_voice).lower(), selected_voice)
        tts_engine = deepgram.TTS(model=mapped_voice)
        resolved_voice_id = mapped_voice
        selected_tts_model = None

    llm_model = config.get("llm_model", "gpt-4o-mini")
    is_moonshot = "moonshot" in llm_model.lower() or "kimi" in llm_model.lower() or "moonlight" in llm_model.lower()

    base_url = "https://api.moonshot.cn/v1" if is_moonshot else None
    raw_key = os.getenv("MOONSHOT_API_KEY") if is_moonshot else os.getenv("OPENAI_API_KEY")
    api_key = raw_key.strip() if raw_key else ""
    if not api_key:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()

    logger.info(
        "Using tts_provider=%s, voice=%s, tts_model=%s, llm_model=%s, base_url=%s",
        tts_provider,
        resolved_voice_id,
        selected_tts_model,
        llm_model,
        base_url,
    )
    usage.llm_model = llm_model
    usage.tts_provider = tts_provider
    usage.tts_model = selected_tts_model or ""
    usage.tts_voice_id = selected_voice if tts_provider == "elevenlabs" else resolved_voice_id

    llm = openai.LLM(api_key=api_key, base_url=base_url, model=llm_model)

    # Build system prompt - DO NOT MODIFY based on welcome settings
    welcome_type = config.get("welcome_message_type", "user_speaks_first")
    welcome_msg = config.get("welcome_message", "")
    logger.info(f"Welcome type: {welcome_type}, Welcome msg: {welcome_msg}, Direction: {direction}")
    sys_prompt = config.get("system_prompt", "You are a helpful voice assistant.")
    
    # Note: We do NOT modify system prompt for welcome messages
    # The welcome behavior is controlled solely by generate_reply() call below

    agent = create_dynamic_agent_class(
        functions_config=functions,
        base_instructions=sys_prompt,
        current_room=ctx.room,
        call_id=call_id
    )

    # Use nova-2-phonecall for better phone call performance
    stt_model = "nova-2-phonecall" if (from_number or to_number) else "nova-2-general"
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(language=config.get("language", "en-GB"), model=stt_model),
        llm=llm,
        tts=tts_engine,
    )

    # Track transcripts using session events
    transcript_tracker = TranscriptCollector(call_id, usage, llm_model)

    @session.on("metrics_collected")
    def on_metrics_collected(event):
        try:
            for metric in event.metrics:
                if hasattr(metric, 'type') and 'llm' in str(metric.type).lower():
                    if hasattr(metric, 'tokens'):
                        usage.llm_tokens_in = getattr(metric, 'tokens_input', 0) or 0
                        usage.llm_tokens_out = getattr(metric, 'tokens_output', 0) or 0
                        logger.info(f"[metrics] LLM tokens: {usage.llm_tokens_in}/{usage.llm_tokens_out}")
                if hasattr(metric, 'type') and 'tts' in str(metric.type).lower():
                    if hasattr(metric, 'characters'):
                        usage.tts_characters = getattr(metric, 'characters', 0) or 0
                        logger.info(f"[metrics] TTS chars: {usage.tts_characters}")
                if hasattr(metric, 'type') and 'stt' in str(metric.type).lower():
                    if hasattr(metric, 'duration'):
                        usage.stt_duration_ms = int((getattr(metric, 'duration', 0) or 0) * 1000)
                        logger.info(f"[metrics] STT duration: {usage.stt_duration_ms}ms")
        except Exception as e:
            logger.debug(f"Error in metrics_collected: {e}")

    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        try:
            item = event.item
            if not item:
                return
            role = getattr(item, 'role', '')
            content = ''
            if hasattr(item, 'content'):
                if isinstance(item.content, str):
                    content = item.content
                elif isinstance(item.content, list):
                    content = ' '.join(str(c) for c in item.content if c)
            elif hasattr(item, 'text'):
                content = item.text
            if not content or role == 'system':
                return
            if role == 'user':
                word_count = len(content.split())
                est_duration = int((word_count / 150.0) * 60 * 1000)
                usage.add_stt_duration(est_duration)
                usage.add_llm_usage(tokens_in=len(content) // 4, model=llm_model)
                usage.add_transcript("user", content)
                asyncio.ensure_future(send_transcript_to_api(call_id, "user", content))
                logger.info(f"[transcript] User: {content[:60]}...")
            elif role == 'assistant':
                usage.add_tts_characters(len(content))
                usage.add_llm_usage(tokens_out=len(content) // 4, model=llm_model)
                usage.add_transcript("agent", content)
                asyncio.ensure_future(send_transcript_to_api(call_id, "agent", content))
                logger.info(f"[transcript] Agent: {content[:60]}...")
        except Exception as e:
            logger.error(f"Error in conversation_item_added: {e}")

    @session.on("function_calls_collected")
    def on_function_calls_collected(event):
        try:
            for fc in event.function_calls:
                tool_name = fc.function.name
                args_str = str(fc.function.arguments)
                msg = f"[Calling tool: {tool_name}] {args_str}"
                usage.add_transcript("tool_call", msg)
                asyncio.ensure_future(send_transcript_to_api(call_id, "tool_call", msg))
                logger.info(f"[transcript] Tool call: {tool_name}")
        except Exception as e:
            logger.error(f"Error in function_calls_collected: {e}")

    @session.on("function_calls_finished")
    def on_function_calls_finished(event):
        try:
            for fc in event.function_calls:
                tool_name = fc.function.name
                output = fc.output if fc.output else str(fc.exception) if fc.exception else "no output"
                msg = f"[Tool response: {tool_name}] {output}"
                usage.add_transcript("tool_response", msg)
                asyncio.ensure_future(send_transcript_to_api(call_id, "tool_response", msg))
                logger.info(f"[transcript] Tool response: {tool_name}")
        except Exception as e:
            logger.error(f"Error in function_calls_finished: {e}")

    @ctx.room.on("data_received")
    def on_data_received(payload, participant, topic):
        try:
            if topic == "room":
                data = json.loads(payload)
                if data.get("type") == "tool_call":
                    tool_name = data.get("tool_name", "unknown")
                    args = data.get("args", {})
                    msg = f"[Tool invoked: {tool_name}] {json.dumps(args)}"
                    usage.add_transcript("tool_invocation", msg)
                    asyncio.ensure_future(send_transcript_to_api(call_id, "tool_invocation", msg))
                    logger.info(f"[transcript] Tool invoked: {tool_name}")
                elif data.get("type") == "tool_response":
                    tool_name = data.get("tool_name", "unknown")
                    response = data.get("response", {})
                    msg = f"[Tool result: {tool_name}] {json.dumps(response)}"
                    usage.add_transcript("tool_result", msg)
                    asyncio.ensure_future(send_transcript_to_api(call_id, "tool_result", msg))
                    logger.info(f"[transcript] Tool result: {tool_name}")
        except Exception as e:
            logger.debug(f"Error processing room data: {e}")

    # Event setup BEFORE session start
    shutdown = asyncio.Event()
    
    @ctx.room.on("disconnected")
    def on_disconnected():
        logger.info("Room disconnected")
        shutdown.set()
    
    @ctx.room.on("participant_disconnected")
    def on_participant_left(participant):
        logger.info(f"Participant left: {participant.identity}")
        shutdown.set()
    
    try:
        await session.start(agent=agent, room=ctx.room)
        logger.info("Session started successfully")
        
        # Immediately send greeting if agent should speak first
        # This matches the official LiveKit pattern - call right after session.start()
        if welcome_type == "agent_greets":
            greeting_text = welcome_msg.strip() if welcome_msg.strip() else "Hello! How can I help you today?"
            logger.info(f"Sending greeting immediately: {greeting_text}")
            try:
                await session.generate_reply(instructions=greeting_text)
                logger.info("Greeting sent successfully")
            except Exception as e:
                logger.error(f"Failed to send greeting: {e}")
                import traceback
                traceback.print_exc()

        # Wait for shutdown signal from SDK
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=MAX_CALL_DURATION)
        except asyncio.TimeoutError:
            logger.warning(f"Call timed out after {MAX_CALL_DURATION}s")

    except Exception as e:
        logger.error(f"Session error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Wait briefly to ensure all metrics are collected
        await asyncio.sleep(1)
        # ALWAYS send usage, even on crash/disconnect
        logger.info(f"Sending final usage for {call_id}: LLM={usage.llm_tokens_in}/{usage.llm_tokens_out}, STT={usage.stt_duration_ms}ms, TTS={usage.tts_characters}chars")
        if call_id:
            await send_usage_to_api(call_id, usage)
            await end_call_record(call_id)
        _active_call_id = None
        _active_usage = None

    logger.info(f"Session ended - Duration: {usage.get_call_duration()}s")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        agent_name="sarah"
    ))
