from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from sqlalchemy import or_

from backend.logging_config import get_logger
from backend.models import get_database, AgentModel, FunctionModel, CallModel, TranscriptModel, WebhookLogModel, PhoneNumberModel
from backend.schemas import AgentCreate, AgentUpdate, AgentResponse, AgentDuplicateRequest
from backend.constants import (
    VALID_LLM_MODELS, VALID_VOICES, VALID_LANGUAGES, 
    VALID_TTS_PROVIDERS, DEFAULT_AGENT_LLM_TEMPERATURE, 
    DEFAULT_AGENT_VOICE_SPEED, MIN_AGENT_LLM_TEMPERATURE, 
    MAX_AGENT_LLM_TEMPERATURE, MIN_AGENT_VOICE_SPEED, MAX_AGENT_VOICE_SPEED
)
from backend.agent_utils import (
    normalize_tts_provider, resolve_display_name, ensure_custom_params, 
    _coerce_agent_setting_float, extract_agent_tts_settings, 
    resolve_agent_llm_temperature_from_params, resolve_agent_voice_speed_from_params,
    serialize_agent
)


logger = get_logger("router_agents")
router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(agent: AgentCreate, db: Session = Depends(get_database)):
    provider = normalize_tts_provider(agent.tts_provider, agent.voice)
    if agent.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if provider == "deepgram" and agent.voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {', '.join(VALID_VOICES)}")
    if provider not in VALID_TTS_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid tts_provider. Must be one of: {', '.join(VALID_TTS_PROVIDERS)}")
    if provider == "elevenlabs" and not agent.voice:
        raise HTTPException(status_code=400, detail="voice must be a valid ElevenLabs voice ID when tts_provider=elevenlabs")
    if agent.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    resolved_name = resolve_display_name(agent.name, agent.display_name)
    custom_params = ensure_custom_params(agent.custom_params)
    custom_params["tts_provider"] = provider
    
    if provider == "elevenlabs":
        resolved_tts_model = agent.tts_model or custom_params.get("tts_model")
        if not resolved_tts_model:
            raise HTTPException(status_code=400, detail="tts_model must be explicitly selected in the app when tts_provider=elevenlabs")
        custom_params["tts_model"] = resolved_tts_model
    elif agent.tts_model:
        custom_params["tts_model"] = agent.tts_model
    else:
        custom_params.pop("tts_model", None)
    
    custom_params["llm_temperature"] = _coerce_agent_setting_float(
        agent.llm_temperature, 
        default=DEFAULT_AGENT_LLM_TEMPERATURE, 
        min_value=MIN_AGENT_LLM_TEMPERATURE, 
        max_value=MAX_AGENT_LLM_TEMPERATURE
    )
    custom_params["voice_speed"] = _coerce_agent_setting_float(
        agent.voice_speed, 
        default=DEFAULT_AGENT_VOICE_SPEED, 
        min_value=MIN_AGENT_VOICE_SPEED, 
        max_value=MAX_AGENT_VOICE_SPEED
    )

    db_agent = AgentModel(
        name=resolved_name,
        agent_name=agent.agent_name,
        system_prompt=agent.system_prompt,
        llm_model=agent.llm_model,
        voice=agent.voice,
        language=agent.language,
        twilio_number=agent.twilio_number,
        welcome_message_type=agent.welcome_message_type,
        welcome_message=agent.welcome_message,
        max_call_duration=agent.max_call_duration,
        enable_recording=agent.enable_recording,
        webhook_url=agent.webhook_url,
        custom_params=custom_params,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return serialize_agent(db_agent)

@router.get("/list-simple")
async def list_agents_simple(db: Session = Depends(get_database)):
    agents = db.query(AgentModel).order_by(AgentModel.name).all()
    return [{"id": a.id, "name": a.name} for a in agents]

@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: Session = Depends(get_database)):
    agents = db.query(AgentModel).order_by(AgentModel.created_at.desc()).all()
    return [serialize_agent(agent) for agent in agents]

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return serialize_agent(agent)

@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent_update: AgentUpdate, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent_update.llm_model is not None and agent_update.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if agent_update.language is not None and agent_update.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    current_tts = extract_agent_tts_settings(agent)
    new_voice = agent_update.voice if agent_update.voice is not None else agent.voice
    new_provider = normalize_tts_provider(agent_update.tts_provider, new_voice)
    
    if new_provider not in VALID_TTS_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid tts_provider. Must be one of: {', '.join(VALID_TTS_PROVIDERS)}")
    if new_provider == "deepgram" and new_voice and new_voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {', '.join(VALID_VOICES)}")
    if new_provider == "elevenlabs" and not new_voice:
        raise HTTPException(status_code=400, detail="voice must be provided for ElevenLabs")

    update_data = agent_update.dict(exclude_unset=True)
    update_data.pop("tts_provider", None)
    update_data.pop("tts_model", None)
    update_data.pop("llm_temperature", None)
    update_data.pop("voice_speed", None)
    
    incoming_display_name = update_data.pop("display_name", None)
    if incoming_display_name is not None and "name" not in update_data:
        update_data["name"] = resolve_display_name(agent.name, incoming_display_name)
    elif "name" in update_data:
        update_data["name"] = resolve_display_name(update_data.get("name"), incoming_display_name)

    for field, value in update_data.items():
        if value is not None:
            setattr(agent, field, value)

    custom_params = ensure_custom_params(agent.custom_params)
    existing_builtin_functions = custom_params.get("builtin_functions")
    if agent_update.custom_params is not None:
        custom_params = ensure_custom_params(agent_update.custom_params)
        if "builtin_functions" not in custom_params and existing_builtin_functions is not None:
            custom_params["builtin_functions"] = existing_builtin_functions
    
    custom_params["tts_provider"] = new_provider
    
    resolved_tts_model = agent_update.tts_model
    if resolved_tts_model is None and new_provider == "elevenlabs":
        resolved_tts_model = current_tts.get("tts_model") or custom_params.get("tts_model")
    
    if resolved_tts_model:
        custom_params["tts_model"] = resolved_tts_model
    elif new_provider == "elevenlabs":
        raise HTTPException(status_code=400, detail="tts_model must be explicitly selected in the app when tts_provider=elevenlabs")
    elif new_provider == "deepgram":
        custom_params.pop("tts_model", None)

    if agent_update.llm_temperature is not None:
        custom_params["llm_temperature"] = _coerce_agent_setting_float(
            agent_update.llm_temperature, 
            default=DEFAULT_AGENT_LLM_TEMPERATURE, 
            min_value=MIN_AGENT_LLM_TEMPERATURE, 
            max_value=MAX_AGENT_LLM_TEMPERATURE
        )
    else:
        custom_params["llm_temperature"] = resolve_agent_llm_temperature_from_params(custom_params)

    if agent_update.voice_speed is not None:
        custom_params["voice_speed"] = _coerce_agent_setting_float(
            agent_update.voice_speed, 
            default=DEFAULT_AGENT_VOICE_SPEED, 
            min_value=MIN_AGENT_VOICE_SPEED, 
            max_value=MAX_AGENT_VOICE_SPEED
        )
    else:
        custom_params["voice_speed"] = resolve_agent_voice_speed_from_params(custom_params)

    agent.custom_params = custom_params
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return serialize_agent(agent)

@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        call_id_rows = db.query(CallModel.call_id).filter(CallModel.agent_id == agent_id).all()
        call_ids = [row[0] for row in call_id_rows if row and row[0]]

        deleted_transcripts = 0
        deleted_webhook_logs = 0
        if call_ids:
            deleted_transcripts = db.query(TranscriptModel).filter(TranscriptModel.call_id.in_(call_ids)).delete(synchronize_session=False)
            deleted_webhook_logs = db.query(WebhookLogModel).filter(WebhookLogModel.call_id.in_(call_ids)).delete(synchronize_session=False)

        deleted_calls = db.query(CallModel).filter(CallModel.agent_id == agent_id).delete(synchronize_session=False)
        deleted_functions = db.query(FunctionModel).filter(FunctionModel.agent_id == agent_id).delete(synchronize_session=False)

        unlinked_phone_numbers = (
            db.query(PhoneNumberModel)
            .filter(or_(PhoneNumberModel.inbound_agent_id == agent_id, PhoneNumberModel.outbound_agent_id == agent_id))
            .update({PhoneNumberModel.inbound_agent_id: None, PhoneNumberModel.outbound_agent_id: None}, synchronize_session=False)
        )

        db.delete(agent)
        db.commit()

        return {
            "message": "Agent deleted successfully",
            "cleanup": {
                "functions_deleted": deleted_functions,
                "calls_deleted": deleted_calls,
                "transcripts_deleted": deleted_transcripts,
                "webhook_logs_deleted": deleted_webhook_logs,
                "phone_numbers_unlinked": unlinked_phone_numbers,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

@router.post("/{agent_id}/duplicate", response_model=AgentResponse, status_code=201)
async def duplicate_agent(agent_id: int, request: AgentDuplicateRequest, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_agent = AgentModel(
        name=request.name,
        agent_name=agent.agent_name,
        system_prompt=agent.system_prompt,
        llm_model=agent.llm_model,
        voice=agent.voice,
        language=agent.language,
        twilio_number=agent.twilio_number,
        welcome_message_type=agent.welcome_message_type,
        welcome_message=agent.welcome_message,
        max_call_duration=agent.max_call_duration,
        enable_recording=agent.enable_recording,
        webhook_url=agent.webhook_url,
        custom_params=agent.custom_params if isinstance(agent.custom_params, dict) else {},
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    original_functions = db.query(FunctionModel).filter(FunctionModel.agent_id == agent_id).all()
    for func in original_functions:
        new_function = FunctionModel(
            agent_id=new_agent.id,
            name=func.name,
            description=func.description,
            method=func.method,
            url=func.url,
            timeout_ms=func.timeout_ms,
            headers=func.headers if isinstance(func.headers, dict) else {},
            query_params=func.query_params if isinstance(func.query_params, dict) else {},
            parameters_schema=func.parameters_schema if isinstance(func.parameters_schema, dict) else {},
            variables=func.variables if isinstance(func.variables, dict) else {},
            speak_during_execution=func.speak_during_execution,
            speak_after_execution=func.speak_after_execution,
        )
        db.add(new_function)

    db.commit()
    db.refresh(new_agent)
    return serialize_agent(new_agent)
