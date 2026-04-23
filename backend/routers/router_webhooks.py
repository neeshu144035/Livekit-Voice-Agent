from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from backend.models import get_database, CallModel, WebhookLogModel, PhoneNumberModel

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/twilio-status/{call_id}")
async def twilio_status(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    status = payload.get("CallStatus")
    if status:
        call.status = status
        if status in ["completed", "failed"]:
            call.ended_at = datetime.utcnow()
    db.commit()
    return {"received": True}

@router.post("/livekit-webhook")
async def livekit_webhook(request: Request, db: Session = Depends(get_database)):
    data = await request.json()
    room_name = data.get("room", {}).get("name")
    if room_name:
        # Update call status based on LiveKit room events
        pass
    return {"received": True}

@router.post("/outbound-call")
async def webhook_outbound_call(payload: Dict[str, Any], db: Session = Depends(get_database)):
    # Handle outbound call webhook from Twilio
    return {"received": True}