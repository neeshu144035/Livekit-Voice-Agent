from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from backend.logging_config import get_logger
from backend.models import get_database, CallModel, AgentModel, WebhookLogModel


logger = get_logger("router_analytics")
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/")
async def get_analytics(db: Session = Depends(get_database)):
    total_calls = db.query(CallModel).count()
    active_calls = db.query(CallModel).filter(CallModel.status.in_(["in-progress", "pending", "initiating"])).count()
    total_agents = db.query(AgentModel).count()
    
    return {
        "total_calls": total_calls,
        "active_calls": active_calls,
        "total_agents": total_agents,
        "calls_today": db.query(CallModel).filter(CallModel.created_at >= datetime.utcnow().date()).count(),
        "avg_duration": 0.0,  # compute if needed
    }

@router.get("/debug/calls-count")
async def debug_calls_count(db: Session = Depends(get_database)):
    counts = {
        "total": db.query(CallModel).count(),
        "pending": db.query(CallModel).filter(CallModel.status == "pending").count(),
        "in-progress": db.query(CallModel).filter(CallModel.status == "in-progress").count(),
        "ended": db.query(CallModel).filter(CallModel.status == "ended").count(),
        "failed": db.query(CallModel).filter(CallModel.status == "failed").count(),
    }
    return counts

@router.get("/webhooks/logs")
async def get_webhook_logs(db: Session = Depends(get_database)):
    logs = db.query(WebhookLogModel).order_by(WebhookLogModel.created_at.desc()).limit(100).all()
    return logs

@router.get("/call-history")
async def get_call_history(db: Session = Depends(get_database)):
    calls = db.query(CallModel).order_by(CallModel.created_at.desc()).limit(50).all()
    return calls

@router.get("/call-history/{call_id}/details")
async def get_call_details(call_id: str, db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    transcripts = db.query(TranscriptModel).filter(TranscriptModel.call_id == call_id).order_by(TranscriptModel.id).all()
    webhook_logs = db.query(WebhookLogModel).filter(WebhookLogModel.call_id == call_id).order_by(WebhookLogModel.created_at).all()
    
    return {
        "call": call,
        "transcripts": [{"role": t.role, "content": t.content, "is_final": t.is_final} for t in transcripts],
        "webhook_logs": [{"event_type": w.event_type, "response_status": w.response_status} for w in webhook_logs],
    }

@router.post("/calls/create-from-agent")
async def create_call_from_agent(payload: Dict[str, Any], db: Session = Depends(get_database)):
    # Logic for creating a call directly from agent settings
    return {"success": True}

@router.delete("/admin/calls/clear")
async def admin_clear_calls(db: Session = Depends(get_database)):
    # Danger: clears all calls, transcripts, webhook logs
    # Implementation omitted for safety
    raise HTTPException(status_code=403, detail="Admin endpoint requires authorization")

@router.get("/system/llm-status")
async def get_llm_status():
    import os
    openai_key = os.getenv("OPENAI_API_KEY")
    moonshot_key = os.getenv("MOONSHOT_API_KEY")
    return {
        "openai_configured": bool(openai_key),
        "moonshot_configured": bool(moonshot_key),
        "available_models": ["openai", "moonshot"] if openai_key or moonshot_key else [],
    }