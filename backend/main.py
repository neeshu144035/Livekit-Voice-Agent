import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import engine, SessionLocal, Base, get_database
from backend.constants import LIVEKIT_URL
from backend.logging_config import get_logger, LogContext
from backend.routers import (
router_auth,
router_agents,
router_chat_agents,
router_calls,
router_tts,
router_phone_numbers,
router_webhooks,
router_analytics,
router_capacity,
router_transfer,
router_versions,
router_functions,
router_token,
)

logger = get_logger("backend-api")

app = FastAPI(title="Voice AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_auth.router)
app.include_router(router_agents.router)
app.include_router(router_chat_agents.router)
app.include_router(router_calls.router)
app.include_router(router_tts.router)
app.include_router(router_phone_numbers.router)
app.include_router(router_webhooks.router)
app.include_router(router_analytics.router)
app.include_router(router_capacity.router)
app.include_router(router_transfer.router)
app.include_router(router_versions.router)
app.include_router(router_functions.router)
app.include_router(router_token.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Backend API started")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "livekit_url": LIVEKIT_URL,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check_api():
    return await health_check()
