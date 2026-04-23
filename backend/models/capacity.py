from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from backend.models import Base

class SystemCapacity(Base):
    __tablename__ = "system_capacity"
    
    id = Column(Integer, primary_key=True)
    max_concurrent_calls = Column(Integer, default=10, nullable=False)
    current_concurrent_calls = Column(Integer, default=0, nullable=False)
    queue_enabled = Column(Boolean, default=True)
    max_queue_size = Column(Integer, default=50)
    current_queue_size = Column(Integer, default=0)
    avg_call_duration_seconds = Column(Float, default=120.0)
    peak_hours_start = Column(Integer, default=9)
    peak_hours_end = Column(Integer, default=18)
    auto_scale_enabled = Column(Boolean, default=False)
    scale_up_threshold = Column(Float, default=0.8)
    scale_down_threshold = Column(Float, default=0.3)
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())
