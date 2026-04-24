from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import os

from backend.logging_config import get_logger
from backend.models import get_database, AgentModel, FunctionModel, CallModel
from backend.schemas import FunctionCreate, FunctionResponse

logger = get_logger("router_functions")
router = APIRouter(prefix="/api/agents", tags=["agent-functions"])

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://13.135.81.172:7880")


def generate_livekit_token(room_name: str, identity: str, name: str = None) -> str:
    """Generate a LiveKit access token for a participant."""
    import livekit
    token = livekit.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity)
    token.with_name(name or identity)
    token.with_timestamp(int(datetime.utcnow().timestamp()))
    token.with_ttl(3600)
    
    grant = livekit.VideoGrants(
        room_join=True,
        room_admin=False,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token.with_grants(grant)
    
    return token.to_jwt()


@router.get("/{agent_id}/functions", response_model=List[FunctionResponse])
async def list_functions(agent_id: int, db: Session = Depends(get_database)):
    """List all custom functions for an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    functions = db.query(FunctionModel).filter(
        FunctionModel.agent_id == agent_id
    ).order_by(FunctionModel.created_at.desc()).all()
    
    return functions


@router.post("/{agent_id}/functions", response_model=FunctionResponse, status_code=201)
async def create_function(agent_id: int, function: FunctionCreate, db: Session = Depends(get_database)):
    """Create a new custom function for an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if function.method.upper() not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Invalid method. Must be one of: {', '.join(valid_methods)}")
    
    db_function = FunctionModel(
        agent_id=agent_id,
        name=function.name,
        description=function.description,
        method=function.method.upper(),
        url=function.url,
        timeout_ms=function.timeout_ms,
        headers=function.headers,
        query_params=function.query_params,
        parameters_schema=function.parameters_schema,
        variables=function.variables,
        speak_during_execution=function.speak_during_execution,
        speak_after_execution=function.speak_after_execution,
    )
    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    
    logger.info(f"Created function {function.name} for agent {agent_id}")
    return db_function


@router.get("/{agent_id}/functions/{function_id}", response_model=FunctionResponse)
async def get_function(agent_id: int, function_id: int, db: Session = Depends(get_database)):
    """Get a specific function by ID."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    return function


@router.patch("/{agent_id}/functions/{function_id}", response_model=FunctionResponse)
async def update_function(agent_id: int, function_id: int, function_update: FunctionCreate, db: Session = Depends(get_database)):
    """Update a custom function."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if function_update.method and function_update.method.upper() not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Invalid method. Must be one of: {', '.join(valid_methods)}")
    
    for field, value in function_update.dict(exclude_unset=True).items():
        if value is not None:
            if field == "method":
                value = value.upper()
            setattr(function, field, value)
    
    function.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(function)
    
    logger.info(f"Updated function {function_id} for agent {agent_id}")
    return function


@router.delete("/{agent_id}/functions/{function_id}")
async def delete_function(agent_id: int, function_id: int, db: Session = Depends(get_database)):
    """Delete a custom function."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    function = db.query(FunctionModel).filter(
        FunctionModel.id == function_id,
        FunctionModel.agent_id == agent_id
    ).first()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    db.delete(function)
    db.commit()
    
    logger.info(f"Deleted function {function_id} from agent {agent_id}")
    return {"message": "Function deleted successfully"}


@router.get("/{agent_id}/builtin-functions")
async def get_builtin_functions(agent_id: int, db: Session = Depends(get_database)):
    """Get built-in system functions for an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return [
        {
            "id": "builtin_end_call",
            "agent_id": agent_id,
            "name": "end_call",
            "description": "End the current call immediately. Use this when the user wants to hang up or when the conversation is complete.",
            "method": "SYSTEM",
            "url": "builtin://end_call",
            "timeout_ms": 5000,
            "headers": {},
            "query_params": {},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for ending the call (e.g., 'user_request', 'completed', 'error')"
                    }
                },
                "required": []
            },
            "variables": {},
            "speak_during_execution": False,
            "speak_after_execution": False,
            "is_builtin": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "builtin_transfer_call",
            "agent_id": agent_id,
            "name": "call_transfer",
            "description": "Transfer the current call to another phone number. Use this when the user needs to speak to a different department or person.",
            "method": "SYSTEM",
            "url": "builtin://transfer_call",
            "timeout_ms": 10000,
            "headers": {},
            "query_params": {},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "The phone number to transfer the call to (E.164 format, e.g., +1234567890)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to speak before transferring"
                    }
                },
                "required": ["phone_number"]
            },
            "variables": {},
            "speak_during_execution": True,
            "speak_after_execution": False,
            "is_builtin": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]


@router.post("/{agent_id}/builtin-functions")
async def save_builtin_functions(agent_id: int, config: Dict[str, Any], db: Session = Depends(get_database)):
    """Save builtin functions configuration for an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    current_params = agent.custom_params or {}
    new_params = dict(current_params)
    new_params['builtin_functions'] = config
    agent.custom_params = new_params
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    logger.info(f"Saved builtin functions for agent {agent_id}")
    return {"success": True, "message": "Builtin functions saved"}


@router.get("/{agent_id}/builtin-functions/config")
async def get_builtin_functions_config(agent_id: int, db: Session = Depends(get_database)):
    """Get builtin functions configuration for an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    custom_params = agent.custom_params or {}
    return custom_params.get('builtin_functions', {})