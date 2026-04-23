from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.constants import (
    DEFAULT_TTS_PROVIDER,
    DEFAULT_AGENT_LLM_TEMPERATURE,
    DEFAULT_AGENT_VOICE_SPEED,
    DEFAULT_CALL_DIRECTION
)

class AgentCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    agent_name: Optional[str] = None # LiveKit agent name for dispatch
    system_prompt: str
    llm_model: str = "moonshot-v1-8k"
    voice: str = "jessica"
    tts_provider: Optional[str] = DEFAULT_TTS_PROVIDER
    tts_model: Optional[str] = None
    language: str = "en"
    twilio_number: Optional[str] = None
    welcome_message_type: Optional[str] = "user_speaks_first"
    welcome_message: Optional[str] = None
    max_call_duration: int = 1800
    enable_recording: bool = True
    webhook_url: Optional[str] = None
    llm_temperature: Optional[float] = DEFAULT_AGENT_LLM_TEMPERATURE
    voice_speed: Optional[float] = DEFAULT_AGENT_VOICE_SPEED
    custom_params: Dict[str, Any] = {}

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    agent_name: Optional[str] = None # LiveKit agent name for dispatch
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    voice: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_model: Optional[str] = None
    language: Optional[str] = None
    twilio_number: Optional[str] = None
    welcome_message_type: Optional[str] = None
    welcome_message: Optional[str] = None
    max_call_duration: Optional[int] = None
    enable_recording: Optional[bool] = None
    webhook_url: Optional[str] = None
    llm_temperature: Optional[float] = None
    voice_speed: Optional[float] = None
    custom_params: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    id: int
    name: str
    display_name: str
    agent_name: Optional[str] # LiveKit agent name for dispatch
    system_prompt: str
    llm_model: str
    voice: str
    tts_provider: str = DEFAULT_TTS_PROVIDER
    tts_model: Optional[str] = None
    language: str
    twilio_number: Optional[str]
    welcome_message_type: Optional[str]
    welcome_message: Optional[str]
    max_call_duration: int
    enable_recording: bool
    webhook_url: Optional[str]
    llm_temperature: float = DEFAULT_AGENT_LLM_TEMPERATURE
    voice_speed: float = DEFAULT_AGENT_VOICE_SPEED
    custom_params: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CallCreate(BaseModel):
    agent_id: int
    call_type: str = "web"
    direction: Optional[str] = DEFAULT_CALL_DIRECTION
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CallResponse(BaseModel):
    id: int
    call_id: str
    agent_id: int
    room_name: Optional[str]
    call_type: str
    direction: str
    status: str
    from_number: Optional[str]
    to_number: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    recording_url: Optional[str]
    cost_usd: float
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class TranscriptEntry(BaseModel):
    role: str
    content: str
    is_final: bool = True
    confidence: Optional[float] = None
    stt_latency_ms: Optional[int] = None
    llm_latency_ms: Optional[int] = None
    tts_latency_ms: Optional[int] = None

class FunctionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    method: str = "POST"
    url: str
    timeout_ms: int = 120000
    headers: Dict[str, str] = {}
    query_params: Dict[str, str] = {}
    parameters_schema: Dict[str, Any] = {}
    variables: Dict[str, str] = {}
    speak_during_execution: bool = False
    speak_after_execution: bool = True

class FunctionResponse(BaseModel):
    id: int
    agent_id: int
    name: str
    description: Optional[str]
    method: str
    url: str
    timeout_ms: int
    headers: Dict[str, str]
    query_params: Dict[str, str]
    parameters_schema: Dict[str, Any]
    variables: Dict[str, str]
    speak_during_execution: bool
    speak_after_execution: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class PhoneNumberCreate(BaseModel):
    phone_number: str # E.164 format: +1234567890
    description: Optional[str] = None
    termination_uri: Optional[str] = None 
    sip_trunk_username: Optional[str] = None 
    sip_trunk_password: Optional[str] = None 
    twilio_account_sid: Optional[str] = None 
    twilio_auth_token: Optional[str] = None 
    twilio_sip_trunk_sid: Optional[str] = None 
    inbound_agent_id: Optional[int] = None 
    outbound_agent_id: Optional[int] = None 
    enable_inbound: bool = True 
    enable_outbound: bool = True 
    enable_krisp_noise_cancellation: bool = True 

class PhoneNumberUpdate(BaseModel):
    description: Optional[str] = None
    termination_uri: Optional[str] = None 
    sip_trunk_username: Optional[str] = None 
    sip_trunk_password: Optional[str] = None 
    twilio_account_sid: Optional[str] = None 
    twilio_auth_token: Optional[str] = None 
    twilio_sip_trunk_sid: Optional[str] = None 
    inbound_agent_id: Optional[int] = None 
    outbound_agent_id: Optional[int] = None 
    enable_inbound: Optional[bool] = None 
    enable_outbound: Optional[bool] = None 
    enable_krisp_noise_cancellation: Optional[bool] = None 
    livekit_dispatch_rule_id: Optional[str] = None 

class PhoneNumberResponse(BaseModel):
    id: int
    phone_number: str
    description: Optional[str]
    termination_uri: Optional[str]
    sip_trunk_username: Optional[str]
    twilio_account_sid: Optional[str]
    twilio_sip_trunk_sid: Optional[str]
    livekit_inbound_trunk_id: Optional[str]
    livekit_outbound_trunk_id: Optional[str]
    livekit_dispatch_rule_id: Optional[str]
    livekit_sip_endpoint: Optional[str]
    inbound_agent_id: Optional[int]
    outbound_agent_id: Optional[int]
    status: str
    error_message: Optional[str]
    enable_inbound: bool
    enable_outbound: bool
    enable_krisp_noise_cancellation: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class OutboundCallRequest(BaseModel):
    to_number: str # E.164 format
    phone_number_id: Optional[int] = None 
    runtime_vars: Dict[str, Any] = Field(default_factory=dict)

class LoginRequest(BaseModel):
    email: str
    password: str

class AgentDuplicateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ChatAgentResponse(BaseModel):
    id: int
    name: str
    system_prompt: str
    llm_model: str
    language: str
    custom_params: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatAgentCreate(BaseModel):
    name: str
    system_prompt: str = ""
    llm_model: str = "moonshot-v1-8k"
    language: str = "en"
    custom_params: dict = {}

class ChatAgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    language: Optional[str] = None
    custom_params: Optional[dict] = None

class ChatMessageRequest(BaseModel):
    message: str

class AgentTestChatRequest(BaseModel):
    message: Optional[str] = ""
    history: List[Dict[str, Any]] = []
    start: bool = False

class CallUsageUpdate(BaseModel):
    usage: Dict[str, Any]

class AgentCallCreate(BaseModel):
    agent_id: int
    to_number: str
    runtime_vars: Dict[str, Any] = Field(default_factory=dict)
