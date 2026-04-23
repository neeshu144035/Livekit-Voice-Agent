from fastapi import APIRouter, HTTPException, Depends, WebSocket
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from backend.logging_config import get_logger
from backend.models import get_database, CallModel, TranscriptModel
from backend.schemas import CallResponse

logger = get_logger("router_transfer")
router = APIRouter(prefix="/api/transfers", tags=["transfers"])

_active_transfers: Dict[str, Dict[str, Any]] = {}

@router.post("/{call_id}/initiate")
async def initiate_transfer(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    transfer_to = payload.get("transfer_to")
    transfer_type = payload.get("transfer_type", "warm")
    
    if not transfer_to:
        raise HTTPException(status_code=400, detail="transfer_to phone number required")
    
    logger.info(f"Transfer initiated for call {call_id} to {transfer_to} (type: {transfer_type})")
    
    _active_transfers[call_id] = {
        "status": "initiated",
        "transfer_to": transfer_to,
        "transfer_type": transfer_type,
        "initiated_at": datetime.utcnow().isoformat(),
        "confirmed": False,
        "connected": False,
    }
    
    return {
        "call_id": call_id,
        "status": "initiated",
        "transfer_to": transfer_to,
        "transfer_type": transfer_type,
        "message": f"Transfer to {transfer_to} initiated. Waiting for confirmation...",
    }

@router.post("/{call_id}/confirm")
async def confirm_transfer(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    if call_id not in _active_transfers:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer = _active_transfers[call_id]
    transfer["status"] = "confirmed"
    transfer["confirmed"] = True
    transfer["confirmed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"Transfer confirmed for call {call_id} to {transfer['transfer_to']}")
    
    return {
        "call_id": call_id,
        "status": "confirmed",
        "transfer_to": transfer["transfer_to"],
        "message": "Transfer confirmed. Connecting...",
    }

@router.post("/{call_id}/connect")
async def connect_transfer(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    if call_id not in _active_transfers:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer = _active_transfers[call_id]
    transfer["status"] = "connecting"
    
    logger.info(f"Transfer connecting for call {call_id} to {transfer['transfer_to']}")
    
    return {
        "call_id": call_id,
        "status": "connecting",
        "transfer_to": transfer["transfer_to"],
        "message": "Connecting to transfer target...",
    }

@router.post("/{call_id}/connected")
async def transfer_connected(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    if call_id not in _active_transfers:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer = _active_transfers[call_id]
    transfer["status"] = "connected"
    transfer["connected"] = True
    transfer["connected_at"] = datetime.utcnow().isoformat()
    
    call = db.query(CallModel).filter(CallModel.call_id == call_id).first()
    if call:
        call.status = "transferred"
        db.commit()
    
    logger.info(f"Transfer connected for call {call_id} to {transfer['transfer_to']}")
    
    return {
        "call_id": call_id,
        "status": "connected",
        "transfer_to": transfer["transfer_to"],
        "message": "Transfer successful. Handing off call...",
    }

@router.post("/{call_id}/cancel")
async def cancel_transfer(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    if call_id not in _active_transfers:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer = _active_transfers.pop(call_id)
    
    logger.info(f"Transfer cancelled for call {call_id}")
    
    return {
        "call_id": call_id,
        "status": "cancelled",
        "message": "Transfer cancelled",
    }

@router.post("/{call_id}/failed")
async def transfer_failed(call_id: str, payload: Dict[str, Any], db: Session = Depends(get_database)):
    if call_id not in _active_transfers:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer = _active_transfers.pop(call_id)
    transfer["status"] = "failed"
    transfer["failed_at"] = datetime.utcnow().isoformat()
    transfer["failure_reason"] = payload.get("reason", "Unknown")
    
    logger.error(f"Transfer failed for call {call_id}: {transfer['failure_reason']}")
    
    return {
        "call_id": call_id,
        "status": "failed",
        "reason": transfer["failure_reason"],
        "message": f"Transfer failed: {transfer['failure_reason']}",
    }

@router.get("/{call_id}/status")
async def get_transfer_status(call_id: str):
    if call_id not in _active_transfers:
        return {"status": "not_found", "message": "No active transfer for this call"}
    
    transfer = _active_transfers[call_id]
    return {
        "call_id": call_id,
        "status": transfer["status"],
        "transfer_to": transfer.get("transfer_to"),
        "transfer_type": transfer.get("transfer_type", "warm"),
        "initiated_at": transfer.get("initiated_at"),
        "confirmed_at": transfer.get("confirmed_at"),
        "connected_at": transfer.get("connected_at"),
        "failed_at": transfer.get("failed_at"),
        "failure_reason": transfer.get("failure_reason"),
    }

@router.get("/active")
async def get_active_transfers():
    return {
        "active_transfers": len(_active_transfers),
        "transfers": [
            {
                "call_id": call_id,
                "status": data["status"],
                "transfer_to": data.get("transfer_to"),
            }
            for call_id, data in _active_transfers.items()
        ],
    }

@router.websocket("/ws/{call_id}")
async def transfer_websocket(websocket: WebSocket, call_id: str):
    await websocket.accept()
    logger.info(f"Transfer WebSocket connected for call {call_id}")
    
    try:
        while call_id in _active_transfers:
            transfer = _active_transfers[call_id]
            await websocket.send_json({
                "call_id": call_id,
                "status": transfer["status"],
                "transfer_to": transfer.get("transfer_to"),
                "message": f"Transfer {transfer['status']}...",
            })
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Transfer WebSocket error for {call_id}: {e}")
    finally:
        await websocket.close()
