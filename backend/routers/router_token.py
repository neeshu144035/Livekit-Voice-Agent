from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import json
import os

from backend.logging_config import get_logger
from backend.models import get_database, AgentModel, CallModel

logger = get_logger("router_token")
router = APIRouter(prefix="/api/token", tags=["token"])

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://13.135.81.172:7880")


def generate_livekit_token(room_name: str, identity: str, name: str = None) -> str:
    from livekit.api import AccessToken, VideoGrants
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity)
    token.with_name(name or identity)
    token.with_ttl(timedelta(hours=1))

    grant = VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token.with_grants(grant)

    return token.to_jwt()


@router.get("/{agent_id}")
async def get_token(agent_id: int, db: Session = Depends(get_database)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    room_name = "call_{}_{}".format(agent.id, uuid.uuid4().hex[:8])
    user_identity = "user_{}".format(uuid.uuid4().hex[:8])

    token = generate_livekit_token(room_name, user_identity, "User-{}".format(agent.id))

    call_id = "call_{}_{}".format(agent.id, uuid.uuid4().hex[:16])
    db_call = CallModel(
        call_id=call_id,
        agent_id=agent.id,
        room_name=room_name,
        call_type="web",
        direction="outbound",
        status="pending"
    )
    db.add(db_call)
    db.commit()

    try:
        http_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
        from livekit.api import LiveKitAPI, CreateRoomRequest, CreateAgentDispatchRequest
        lk_api = LiveKitAPI(url=http_url, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)

        room = await lk_api.room.create_room(
            CreateRoomRequest(name=room_name, empty_timeout=300, max_participants=2)
        )

        if agent.agent_name:
            dispatch = await lk_api.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(
                    agent_name=agent.agent_name,
                    room=room_name,
                    metadata=json.dumps({"call_id": call_id, "call_type": "web", "user_identity": user_identity})
                )
            )
            logger.info("Dispatched agent {} to room {}".format(agent.agent_name, room_name))

        await lk_api.aclose()
    except Exception as e:
        logger.error("Failed to dispatch agent: {}".format(e))

    return {
        "token": token,
        "room_name": room_name,
        "call_id": call_id,
        "user_identity": user_identity,
        "livekit_url": os.getenv("LIVEKIT_WS_URL", "wss://13.135.81.172:7880"),
        "agent": {"id": agent.id, "name": agent.name, "voice_id": agent.voice, "welcome_message": agent.welcome_message}
    }