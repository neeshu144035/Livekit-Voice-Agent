from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from backend.logging_config import get_logger
from backend.models import get_database, AgentModel
from backend.schemas import AgentResponse

logger = get_logger("router_versions")
router = APIRouter(prefix="/api/agents/{agent_id}/versions", tags=["agent-versions"])

@router.post("/", status_code=201)
async def create_version(agent_id: int, payload: Dict[str, Any], db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    version_data = {
        "agent_id": agent_id,
        "version_name": payload.get("version_name", f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
        "description": payload.get("description", ""),
        "snapshot": {
            "name": agent.name,
            "agent_name": agent.agent_name,
            "system_prompt": agent.system_prompt,
            "llm_model": agent.llm_model,
            "voice": agent.voice,
            "language": agent.language,
            "twilio_number": agent.twilio_number,
            "welcome_message_type": agent.welcome_message_type,
            "welcome_message": agent.welcome_message,
            "max_call_duration": agent.max_call_duration,
            "enable_recording": agent.enable_recording,
            "webhook_url": agent.webhook_url,
            "custom_params": agent.custom_params,
        },
        "created_at": datetime.utcnow().isoformat(),
    }
    
    version_json = json.dumps(version_data, default=str)
    
    logger.info(f"Created version {version_data['version_name']} for agent {agent_id}")
    
    return {
        "success": True,
        "version": version_data,
        "message": f"Version {version_data['version_name']} created for agent {agent_id}",
    }

@router.get("/")
async def list_versions(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    current_snapshot = {
        "name": agent.name,
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "voice": agent.voice,
        "language": agent.language,
        "custom_params": agent.custom_params,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }

    return {
        "agent_id": agent_id,
        "current_version": current_snapshot,
        "message": "Save versions via POST / to create snapshots for rollback",
        "total": 0,
    }

@router.get("/{version_name}")
async def get_version(agent_id: int, version_name: str, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    version_data = {
        "agent_id": agent_id,
        "version_name": version_name,
        "snapshot": {
            "name": agent.name,
            "agent_name": agent.agent_name,
            "system_prompt": agent.system_prompt,
            "llm_model": agent.llm_model,
            "voice": agent.voice,
            "language": agent.language,
            "custom_params": agent.custom_params,
        },
        "created_at": datetime.utcnow().isoformat(),
    }
    
    return version_data

@router.post("/{version_name}/rollback")
async def rollback_to_version(agent_id: int, version_name: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    snapshot = payload.get("snapshot")
    if not snapshot:
        raise HTTPException(status_code=400, detail="snapshot required")
    
    if "name" in snapshot:
        agent.name = snapshot["name"]
    if "agent_name" in snapshot:
        agent.agent_name = snapshot["agent_name"]
    if "system_prompt" in snapshot:
        agent.system_prompt = snapshot["system_prompt"]
    if "llm_model" in snapshot:
        agent.llm_model = snapshot["llm_model"]
    if "voice" in snapshot:
        agent.voice = snapshot["voice"]
    if "language" in snapshot:
        agent.language = snapshot["language"]
    if "custom_params" in snapshot:
        agent.custom_params = snapshot["custom_params"]
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    
    logger.info(f"Rolled back agent {agent_id} to version {version_name}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} rolled back to version {version_name}",
        "agent": serialize_agent(agent),
    }

@router.post("/compare")
async def compare_versions(agent_id: int, payload: Dict[str, Any], db: Session = Depends(get_database)):
    version1_name = payload.get("version1")
    version2_name = payload.get("version2")
    
    if not version1_name or not version2_name:
        raise HTTPException(status_code=400, detail="Both version1 and version2 required")
    
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    current_snapshot = {
        "name": agent.name,
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "voice": agent.voice,
        "language": agent.language,
        "custom_params": agent.custom_params,
    }
    
    version1_snapshot = payload.get("version1_snapshot", {})
    version2_snapshot = payload.get("version2_snapshot", {})
    
    changes = []
    for key in set(list(version1_snapshot.keys()) + list(version2_snapshot.keys())):
        val1 = version1_snapshot.get(key)
        val2 = version2_snapshot.get(key)
        if val1 != val2:
            changes.append({
                "field": key,
                "old_value": val1,
                "new_value": val2,
            })
    
    return {
        "agent_id": agent_id,
        "version1": version1_name,
        "version2": version2_name,
        "changes": changes,
        "total_changes": len(changes),
    }

def serialize_agent(agent: AgentModel) -> Dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt,
        "llm_model": agent.llm_model,
        "voice": agent.voice,
        "language": agent.language,
        "custom_params": agent.custom_params,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
