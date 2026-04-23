from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import or_

from backend.models import get_database, PhoneNumberModel, AgentModel
from backend.schemas import PhoneNumberCreate, PhoneNumberUpdate, PhoneNumberResponse

router = APIRouter(prefix="/api/phone-numbers", tags=["phone-numbers"])

@router.get("/sip-endpoint")
async def get_sip_endpoint():
    import os
    return {"endpoint": os.getenv("SIP_ENDPOINT", "sip.oyik.info")}

@router.post("/", response_model=PhoneNumberResponse, status_code=201)
async def create_phone_number(phone: PhoneNumberCreate, db: Session = Depends(get_database)):
    db_phone = PhoneNumberModel(**phone.dict())
    db.add(db_phone)
    db.commit()
    db.refresh(db_phone)
    return db_phone

@router.get("/", response_model=List[PhoneNumberResponse])
async def list_phone_numbers(db: Session = Depends(get_database)):
    return db.query(PhoneNumberModel).all()

@router.get("/{phone_id}", response_model=PhoneNumberResponse)
async def get_phone_number(phone_id: int, db: Session = Depends(get_database)):
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    return phone

@router.patch("/{phone_id}", response_model=PhoneNumberResponse)
async def update_phone_number(phone_id: int, update: PhoneNumberUpdate, db: Session = Depends(get_database)):
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(phone, field, value)
    
    db.commit()
    db.refresh(phone)
    return phone

@router.delete("/{phone_id}")
async def delete_phone_number(phone_id: int, db: Session = Depends(get_database)):
    phone = db.query(PhoneNumberModel).filter(PhoneNumberModel.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    db.delete(phone)
    db.commit()
    return {"success": True, "message": "Phone number deleted"}

@router.post("/{phone_id}/configure")
async def configure_phone_number(phone_id: int, payload: Dict[str, Any], db: Session = Depends(get_database)):
    # Logic for configuring SIP trunks / LiveKit dispatch
    return {"success": True}

@router.post("/{phone_id}/create-dispatch-rule")
async def create_dispatch_rule(phone_id: int, payload: Dict[str, Any], db: Session = Depends(get_database)):
    return {"success": True}

@router.post("/{phone_id}/outbound")
async def trigger_outbound_call(phone_id: int, payload: Dict[str, Any], db: Session = Depends(get_database)):
    return {"success": True}

@router.get("/{phone_id}/instructions")
async def get_phone_instructions(phone_id: int, db: Session = Depends(get_database)):
    return {"instructions": "Call the API endpoint to configure SIP."}
