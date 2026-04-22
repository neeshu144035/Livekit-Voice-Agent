import asyncio
import logging
import os
import time
import json
from livekit import api, rtc
from dotenv import load_dotenv

load_dotenv()

# Configuration
LIVEKIT_URL = "ws://13.135.81.172:7880" 
API_KEY = "devkey"
API_SECRET = "secret12345678"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("latency-tester")

class LatencyTester:
    async def run(self):
        self.room = rtc.Room()
        self.user_speech_done_time = 0
        self.agent_joined = asyncio.Event()
        self.metrics = {}

        token = api.AccessToken(API_KEY, API_SECRET) \
            .with_identity("latency-tester") \
            .with_grants(api.VideoGrants(room_join=True, room="agent-test-1"))
        
        jwt = token.to_jwt()
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant connected: {participant.identity}")
            if "agent" in participant.identity.lower() or participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
                self.agent_joined.set()

        @self.room.on("data_received")
        def on_data(data: rtc.DataPacket):
            try:
                payload = json.loads(data.data.decode())
                if payload.get("type") == "transcript":
                    role = payload.get("role")
                    text = payload.get("text")
                    curr_time = time.time() * 1000
                    
                    if role == "user":
                        self.user_speech_done_time = curr_time
                        logger.info(f"User: {text}")
                    elif role == "agent":
                        if self.user_speech_done_time > 0:
                            latency = curr_time - self.user_speech_done_time
                            logger.info(f"Agent (Latency: {latency:.2f}ms): {text}")
                            self.metrics["e2e_ms"] = latency
                        else:
                            logger.info(f"Agent: {text}")
            except Exception as e:
                pass

        logger.info(f"Connecting to {LIVEKIT_URL}...")
        await self.room.connect(LIVEKIT_URL, jwt)
        logger.info("Connected to room.")

        # Check for already present agent
        for p in self.room.remote_participants.values():
            if "agent" in p.identity.lower():
                self.agent_joined.set()

        logger.info("Waiting for agent to join...")
        try:
            await asyncio.wait_for(self.agent_joined.wait(), timeout=15)
            logger.info("Agent joined!")
        except asyncio.TimeoutError:
            logger.warning("Agent did not join in time.")

        # Send a simulated user transcript via data channel to trigger agent
        # (Since we can't easily stream audio from this script)
        # Note: The agent needs to be programmed to listen to data-channel "user_transcript"
        # but our current agent listens to STT. 
        # So this script is mainly for OBSERVING a real call.
        
        await asyncio.sleep(5)
        await self.room.disconnect()
        print("\n--- Final Metrics ---")
        print(json.dumps(self.metrics, indent=2))

if __name__ == "__main__":
    asyncio.run(LatencyTester().run())
