from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models import get_database, ChatAgentModel
from backend.schemas import ChatAgentResponse, ChatAgentCreate, ChatAgentUpdate, ChatMessageRequest
from backend.constants import VALID_LLM_MODELS, VALID_LANGUAGES
from backend.agent_utils import ensure_custom_params
from backend.llm_utils import _resolve_openai_client_for_agent_model

router = APIRouter(prefix="/api/chat-agents", tags=["chat-agents"])

@router.post("/", response_model=ChatAgentResponse, status_code=201)
async def create_chat_agent(agent: ChatAgentCreate, db: Session = Depends(get_database)):
    if agent.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if agent.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    db_agent = ChatAgentModel(
        name=agent.name,
        system_prompt=agent.system_prompt,
        llm_model=agent.llm_model,
        language=agent.language,
        custom_params=ensure_custom_params(agent.custom_params),
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/", response_model=List[ChatAgentResponse])
async def list_chat_agents(db: Session = Depends(get_database)):
    agents = db.query(ChatAgentModel).order_by(ChatAgentModel.created_at.desc()).all()
    return agents

@router.get("/{agent_id}", response_model=ChatAgentResponse)
async def get_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat Agent not found")
    return agent

@router.patch("/{agent_id}", response_model=ChatAgentResponse)
async def update_chat_agent(agent_id: int, agent_update: ChatAgentUpdate, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat Agent not found")

    if agent_update.llm_model is not None and agent_update.llm_model not in VALID_LLM_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid llm_model. Must be one of: {', '.join(VALID_LLM_MODELS)}")
    if agent_update.language is not None and agent_update.language not in VALID_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    if agent_update.custom_params is not None:
        agent.custom_params = ensure_custom_params(agent_update.custom_params)

    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{agent_id}")
async def delete_chat_agent(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat Agent not found")
    db.delete(agent)
    db.commit()
    return {"success": True, "message": "Chat Agent deleted successfully"}

@router.post("/{agent_id}/chat")
async def chat_with_agent(agent_id: int, request: ChatMessageRequest, db: Session = Depends(get_database)):
    agent = db.query(ChatAgentModel).filter(ChatAgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Chat Agent not found")
    
    client = _resolve_openai_client_for_agent_model(agent.llm_model)
    
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": request.message}
    ]
    
    response = client.chat.completions.create(
        model=agent.llm_model,
        messages=messages,
        temperature=agent.custom_params.get("llm_temperature", 0.7) if isinstance(agent.custom_params, dict) else 0.7
    )
    
    return {
        "success": True,
        "reply": response.choices[0].message.content
    }

