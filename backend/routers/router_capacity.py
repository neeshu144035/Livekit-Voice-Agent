from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from backend.logging_config import get_logger
from backend.models import get_database, SystemCapacity

logger = get_logger("router_capacity")
router = APIRouter(prefix="/api/capacity", tags=["capacity"])

@router.get("/")
async def get_capacity(db: Session = Depends(get_database)):
    capacity = db.query(SystemCapacity).first()
    if not capacity:
        capacity = SystemCapacity()
        db.add(capacity)
        db.commit()
        db.refresh(capacity)
    
    utilization = (capacity.current_concurrent_calls / capacity.max_concurrent_calls * 100) if capacity.max_concurrent_calls > 0 else 0
    
    return {
        "max_concurrent_calls": capacity.max_concurrent_calls,
        "current_concurrent_calls": capacity.current_concurrent_calls,
        "available_slots": max(0, capacity.max_concurrent_calls - capacity.current_concurrent_calls),
        "utilization_percent": round(utilization, 2),
        "queue_enabled": capacity.queue_enabled,
        "max_queue_size": capacity.max_queue_size,
        "current_queue_size": capacity.current_queue_size,
        "avg_call_duration_seconds": capacity.avg_call_duration_seconds,
        "auto_scale_enabled": capacity.auto_scale_enabled,
        "status": "healthy" if utilization < 80 else "warning" if utilization < 95 else "critical",
    }

@router.post("/configure")
async def configure_capacity(config: Dict[str, Any], db: Session = Depends(get_database)):
    capacity = db.query(SystemCapacity).first()
    if not capacity:
        capacity = SystemCapacity()
        db.add(capacity)
    
    if "max_concurrent_calls" in config:
        capacity.max_concurrent_calls = config["max_concurrent_calls"]
    if "queue_enabled" in config:
        capacity.queue_enabled = config["queue_enabled"]
    if "max_queue_size" in config:
        capacity.max_queue_size = config["max_queue_size"]
    if "auto_scale_enabled" in config:
        capacity.auto_scale_enabled = config["auto_scale_enabled"]
    if "scale_up_threshold" in config:
        capacity.scale_up_threshold = config["scale_up_threshold"]
    if "scale_down_threshold" in config:
        capacity.scale_down_threshold = config["scale_down_threshold"]
    
    capacity.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(capacity)
    
    logger.info(f"Capacity configured: max={capacity.max_concurrent_calls}, queue={capacity.queue_enabled}")
    return get_capacity(db)

@router.post("/call/start")
async def start_call(call_data: Dict[str, Any], db: Session = Depends(get_database)):
    capacity = db.query(SystemCapacity).first()
    if not capacity:
        capacity = SystemCapacity()
        db.add(capacity)
        db.commit()
    
    if capacity.current_concurrent_calls >= capacity.max_concurrent_calls:
        if capacity.queue_enabled and capacity.current_queue_size < capacity.max_queue_size:
            capacity.current_queue_size += 1
            db.commit()
            logger.info(f"Call queued, position: {capacity.current_queue_size}")
            return {"status": "queued", "position": capacity.current_queue_size, "message": "All agents busy, you are in queue"}
        else:
            logger.warning("Call rejected - capacity full")
            raise HTTPException(status_code=503, detail="System at maximum capacity")
    
    capacity.current_concurrent_calls += 1
    db.commit()
    
    logger.info(f"Call started, concurrent: {capacity.current_concurrent_calls}/{capacity.max_concurrent_calls}")
    return {"status": "accepted", "concurrent_calls": capacity.current_concurrent_calls}

@router.post("/call/end")
async def end_call(call_data: Dict[str, Any], db: Session = Depends(get_database)):
    capacity = db.query(SystemCapacity).first()
    if not capacity:
        raise HTTPException(status_code=404, detail="Capacity not configured")
    
    if capacity.current_concurrent_calls > 0:
        capacity.current_concurrent_calls -= 1
    
    if capacity.current_queue_size > 0:
        capacity.current_queue_size -= 1
    
    db.commit()
    
    logger.info(f"Call ended, concurrent: {capacity.current_concurrent_calls}/{capacity.max_concurrent_calls}")
    return {"status": "ended", "concurrent_calls": capacity.current_concurrent_calls}

@router.get("/metrics")
async def get_capacity_metrics(db: Session = Depends(get_database)):
    capacity = db.query(SystemCapacity).first()
    if not capacity:
        return {"message": "No capacity data available"}
    
    utilization = (capacity.current_concurrent_calls / capacity.max_concurrent_calls * 100) if capacity.max_concurrent_calls > 0 else 0
    
    return {
        "utilization_percent": round(utilization, 2),
        "status": "healthy" if utilization < 80 else "warning" if utilization < 95 else "critical",
        "calls_accepted": capacity.max_concurrent_calls - capacity.current_concurrent_calls,
        "calls_queued": capacity.current_queue_size,
        "avg_duration_seconds": capacity.avg_call_duration_seconds,
        "estimated_wait_time_seconds": round(capacity.avg_call_duration_seconds * (capacity.current_queue_size + 1) / max(1, capacity.max_concurrent_calls), 1),
    }
