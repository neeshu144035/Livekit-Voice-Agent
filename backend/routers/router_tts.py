from backend.logging_config import get_logger
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
import httpx
import logging
from backend.constants import (
    DEFAULT_TTS_PROVIDER, 
    DEEPGRAM_VOICE_OPTIONS, 
    DEEPGRAM_VOICE_ALIASES
)

logger = logging.getLogger("backend-api")

logger = get_logger("router_tts")
router = APIRouter(prefix="/api/tts", tags=["tts"])

def get_elevenlabs_api_key():
    import os
    return os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY")

def is_elevenlabs_v3_model(model_id: str) -> bool:
    return model_id and "v3" in model_id.lower()

def normalize_tts_provider(provider: Optional[str], voice: Optional[str]) -> str:
    if not provider:
        return DEFAULT_TTS_PROVIDER
    provider = provider.lower().strip()
    if provider in {"deepgram", "dg"}:
        return "deepgram"
    if provider in {"elevenlabs", "eleven", "el"}:
        return "elevenlabs"
    return DEFAULT_TTS_PROVIDER

@router.get("/providers")
async def get_tts_providers():
    eleven_api_key = get_elevenlabs_api_key()
    return {
        "providers": [
            {"id": "deepgram", "name": "Deepgram", "available": True},
            {"id": "elevenlabs", "name": "ElevenLabs", "available": bool(eleven_api_key), "missing_env": [] if eleven_api_key else ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"]},
        ]
    }

@router.get("/models")
async def get_tts_models(provider: str = DEFAULT_TTS_PROVIDER):
    provider = normalize_tts_provider(provider, None)
    if provider == "deepgram":
        return {"provider": "deepgram", "default_model": None, "models": []}

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {"provider": "elevenlabs", "available": False, "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"], "default_model": None, "models": []}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get("https://api.elevenlabs.io/v1/models", headers={"xi-api-key": eleven_api_key})
            resp.raise_for_status()
            rows = resp.json() or []
    except Exception as e:
        logger.error(f"Failed to fetch ElevenLabs models: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch ElevenLabs models")

    models = []
    for row in rows:
        if not row.get("can_do_text_to_speech"):
            continue
        langs = row.get("languages") or []
        model_id = row.get("model_id")
        language_ids = [lang.get("language_id") for lang in langs if isinstance(lang, dict) and lang.get("language_id")]
        is_v3 = is_elevenlabs_v3_model(model_id)
        models.append({
            "id": model_id,
            "name": row.get("name") or model_id,
            "description": row.get("description"),
            "character_cost_multiplier": (row.get("model_rates") or {}).get("character_cost_multiplier"),
            "languages": language_ids,
            "languages_count": len(language_ids),
            "is_v3": is_v3,
            "supports_multilingual": is_v3 or len(language_ids) > 1,
            "streaming_type": "http" if is_v3 else "ws",
        })

    models = [m for m in models if m.get("id")]
    models.sort(key=lambda m: (0 if m.get("is_v3") else 1, m["name"].lower()))
    return {"provider": "elevenlabs", "available": True, "missing_env": [], "default_model": None, "models": models}

@router.get("/voices")
async def get_tts_voices(provider: str = DEFAULT_TTS_PROVIDER, model: Optional[str] = None):
    provider = normalize_tts_provider(provider, None)
    if provider == "deepgram":
        options = []
        for alias, mapped_model in DEEPGRAM_VOICE_ALIASES.items():
            model_meta = next((v for v in DEEPGRAM_VOICE_OPTIONS if v["id"] == mapped_model), None)
            options.append({
                "id": alias,
                "name": alias.title(),
                "label": f"{alias.title()} ({model_meta['name'] if model_meta else mapped_model})",
                "accent": model_meta["accent"] if model_meta else None,
                "gender": model_meta["gender"] if model_meta else None,
                "provider": "deepgram",
                "deepgram_model": mapped_model,
            })
        for option in DEEPGRAM_VOICE_OPTIONS:
            options.append({
                "id": option["id"],
                "name": option["name"],
                "label": option["label"],
                "accent": option["accent"],
                "gender": option["gender"],
                "provider": "deepgram",
                "deepgram_model": option["id"],
            })
        return {"provider": "deepgram", "voices": options}

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {"provider": "elevenlabs", "available": False, "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"], "voices": []}

    voices: List[Dict[str, Any]] = []
    page_token = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(5):
                params = {"page_size": 100}
                if page_token:
                    params["next_page_token"] = page_token
                resp = await client.get("https://api.elevenlabs.io/v2/voices", params=params, headers={"xi-api-key": eleven_api_key})
                resp.raise_for_status()
                payload = resp.json() or {}
                voices.extend(payload.get("voices") or [])
                page_token = payload.get("next_page_token")
                if not page_token:
                    break
    except Exception as e:
        logger.error(f"Failed to fetch ElevenLabs voices: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch ElevenLabs voices")

    model_lower = (model or "").strip().lower()
    is_v3_model = "v3" in model_lower if model_lower else False
    normalized = []
    for voice in voices:
        voice_id = voice.get("voice_id")
        if not voice_id:
            continue
        labels = voice.get("labels") or {}
        supported_models = voice.get("high_quality_base_model_ids") or []
        if model_lower and not is_v3_model and supported_models:
            if model_lower not in [m.lower() for m in supported_models]:
                continue
        normalized.append({
            "id": voice_id,
            "name": voice.get("name") or voice_id,
            "label": voice.get("name") or voice_id,
            "accent": labels.get("accent") or labels.get("language") or None,
            "gender": labels.get("gender") or None,
            "category": voice.get("category"),
            "provider": "elevenlabs",
            "supported_models": supported_models,
        })
    normalized.sort(key=lambda item: item["label"].lower())
    return {
        "provider": "elevenlabs",
        "available": True,
        "missing_env": [],
        "voices": normalized,
        "model_filter": model or None,
        "is_v3_universal": is_v3_model,
    }

@router.get("/voices/lookup")
async def lookup_tts_voice(provider: str = DEFAULT_TTS_PROVIDER, voice_id: str = ""):
    provider = normalize_tts_provider(provider, None)
    if provider != "elevenlabs":
        raise HTTPException(status_code=400, detail="Voice lookup is currently supported only for elevenlabs")
    
    voice_id = (voice_id or "").strip()
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id is required")

    eleven_api_key = get_elevenlabs_api_key()
    if not eleven_api_key:
        return {"provider": "elevenlabs", "available": False, "missing_env": ["ELEVEN_API_KEY or ELEVENLABS_API_KEY"], "voice": None}

    voices: List[Dict[str, Any]] = []
    page_token = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(10):
                params = {"page_size": 100}
                if page_token:
                    params["next_page_token"] = page_token
                resp = await client.get("https://api.elevenlabs.io/v2/voices", params=params, headers={"xi-api-key": eleven_api_key})
                resp.raise_for_status()
                payload = resp.json() or {}
                page_voices = payload.get("voices") or []
                voices.extend(page_voices)
                match = next((v for v in page_voices if v.get("voice_id") == voice_id), None)
                if match:
                    labels = match.get("labels") or {}
                    normalized_voice = {
                        "id": match.get("voice_id") or voice_id,
                        "name": match.get("name") or (match.get("voice_id") or voice_id),
                        "label": match.get("name") or (match.get("voice_id") or voice_id),
                        "accent": labels.get("accent") or labels.get("language") or None,
                        "gender": labels.get("gender") or None,
                        "category": match.get("category"),
                        "provider": "elevenlabs",
                    }
                    return {"provider": "elevenlabs", "available": True, "missing_env": [], "voice": normalized_voice}
                page_token = payload.get("next_page_token")
                if not page_token:
                    break
    except Exception as e:
        logger.error(f"Failed to lookup ElevenLabs voice {voice_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to lookup ElevenLabs voices from provider")

    raise HTTPException(status_code=404, detail="Voice ID not found in this ElevenLabs account")
