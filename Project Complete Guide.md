# Complete Technical Guide: Building a Retell-Style Voice AI Platform with LiveKit

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Backend Setup with LiveKit](#backend-setup-with-livekit)
3. [Concurrent Call Handling](#concurrent-call-handling)
4. [User-Agent Integration](#user-agent-integration)
5. [LiveKit Internals](#livekit-internals)
6. [Phone Number Integration](#phone-number-integration)
7. [Frontend Integration](#frontend-integration)
8. [Complete Implementation Example](#complete-implementation-example)
9. [Deployment Guide](#deployment-guide)
10. [Common Issues & Debugging](#common-issues--debugging)
11. [Latest Production Updates (March 2026)](#latest-production-updates-march-2026)

---

## Architecture Overview

### The Multi-Agent Voice AI Architecture

Retell AI and similar platforms (Vapi, Bland) use a **distributed multi-agent architecture** powered by LiveKit as the real-time media layer. This architecture separates concerns into distinct layers:

```
                                CONTROL PLANE (API + Orchestrator)
    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
    │   Agent Mgmt   │    │    Registry    │    │   Scheduler    │    │ Session Lifecycle│
    │   (REST)       │    │ (Redis/        │    │    (Celery)    │    │    Manager      │
    │                │    │  Postgres)     │    │                │    │                  │
    └───────┬────────┘    └───────┬────────┘    └───────┬────────┘    └────────┬────────┘
            │                    │                    │                    │
            └────────────────────┴────────────────────┴────────────────────┘
                                             │
                                             ▼
                              AGENT WORKERS (Runtime Processes)
    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
    │ Agent Worker   │    │ Agent Worker   │    │ Agent Worker   │
    │  (Process 1)   │    │  (Process 2)   │    │  (Process N)   │
    │                │    │                │    │                │
    │  STT → LLM     │    │  STT → LLM     │    │  STT → LLM     │
    │       ↘ TTS    │    │       ↘ TTS    │    │       ↘ TTS    │
    │        ↘²      │    │        ↘²      │    │        ↘²      │
    └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
            │                    │                    │
            └────────────────────┴────────────────────┘
                                             │
                                             ▼
                              LIVEKIT CLOUD (Real-Time Media Layer)
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                         SFU (Selective Forwarding Unit)                    │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐                                │
    │  │  Room 1  │   │  Room 2  │   │  Room N  │                                │
    │  │ ┌──────┐ │   │ ┌──────┐ │   │ ┌──────┐ │                                │
    │  │ │Agent │ │   │ │Agent │ │   │ │Agent │ │                                │
    │  │ │Part. │ │   │ │Part. │ │   │ │Part. │ │                                │
    │  │ └──────┘ │   │ └──────┘ │   │ └──────┘ │                                │
    │  │ ┌──────┐ │   │ ┌──────┐ │   │ ┌──────┐ │                                │
    │  │ │User  │ │   │ │User  │ │   │ │User  │ │                                │
    │  │ │Part. │ │   │ │Part. │ │   │ │Part. │ │                                │
    │  │ └──────┘ │   │ └──────┘ │   │ └──────┘ │                                │
    │  └──────────┘   └──────────┘   └──────────┘                                │
    └─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Control Plane (Backend API)**
   - FastAPI/Flask REST API for agent management
   - PostgreSQL for persistent storage (agents, calls, users)
   - Redis for caching and pub/sub (agent availability, session state)

2. **LiveKit Server (Media Layer)**
   - Acts as SFU (Selective Forwarding Unit)
   - Handles WebRTC connections for audio/video
   - Manages rooms, participants, and media routing
   - Provides REST and gRPC APIs for room management

3. **Agent Workers (Runtime)**
   - Python processes using LiveKit Agents framework
   - Each worker handles one concurrent call (1:1 mapping)
   - Workers register with LiveKit and await jobs
   - Pipeline: STT → LLM → TTS (all streaming)

### Why This Architecture?

- **Scalability:** Add/remove workers based on call volume
- **Reliability:** Workers are disposable; LiveKit handles reconnection
- **Latency:** Media stays in LiveKit network, only control traffic goes to workers
- **Cost:** Pay for LiveKit capacity + compute for agents

---

## Backend Setup with LiveKit

### Prerequisites

```bash
# Install LiveKit server
brew install livekit-cli  # macOS
# or
sudo apt install livekit  # Linux

# Or use Docker
docker pull livekit/livekit-server:latest
```

### Basic LiveKit Server Config (`livekit.yaml`)

```yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range: 50000-50100
  use_external_ip: true
keys:
  # Generate with: livekit create-keys
  devkey: "secret12345678"
  devkey: "secret12345678"  # Repeat for second key pair

# Room configuration
room:
  auto_create: true
  empty_timeout: 300  # 5 minutes
  max_participants: 10
```

### Running LiveKit Server

```bash
livekit-server --config livekit.yaml
```

Or with Docker:

```bash
docker run -d --name livekit \
  -p 7880:7880 -p 7881:7881 -p 50000-50100:50000-50100/udp \
  -v $(pwd)/livekit.yaml:/etc/livekit.yaml \
  livekit/livekit-server \
  --config /etc/livekit.yaml
```

### Backend API Structure

```python
from fastapi import FastAPI, HTTPException
from livekit import api as livekit_api
import httpx

app = FastAPI()

# LiveKit client setup
lk_api = livekit_api.LiveKitAPI(
    url="http://localhost:7880",
    api_key="devkey",
    api_secret="secret12345678"
)

@app.post("/api/agents")
async def create_agent(agent: AgentCreate):
    # Store agent config in PostgreSQL
    # Return agent_id
    pass

@app.post("/api/calls")
async def initiate_call(call: CallCreate):
    # 1. Create LiveKit room
    room = await lk_api.room.create_room(
        room_name=call.room_name,
        empty_timeout=300,
        max_participants=2
    )
    
    # 2. Generate agent token
    agent_token = lk_api.access_token().grant(
        room_name=call.room_name,
        identity="agent",
        name="Agent",
        can_publish=True,
        can_subscribe=True
    ).to_jwt()
    
    # 3. Return both tokens to frontend
    return {
        "room_name": call.room_name,
        "agent_token": agent_token,
        "user_token": user_token  # Generated for frontend
    }

@app.get("/api/calls/{call_id}")
async def get_call(call_id: str):
    # Fetch from PostgreSQL
    pass
```

---

## Concurrent Call Handling

### The Worker Pool Pattern

Unlike traditional web services where one process handles many requests, voice AI requires **one worker per concurrent call**. This is because:

1. Each call holds a WebSocket connection to LiveKit
2. Audio processing is CPU-intensive
3. Latency requirements are sub-second

### Implementation with LiveKit Agents

```python
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, elevenlabs
import asyncio

# Worker registers with LiveKit and waits for jobs
worker = WorkerOptions(
    entrypoint_fnc=entrypoint,
    prewarm=True  # Pre-spawn workers
)

@server.rtc_session(agent_name="default")
async def entrypoint(ctx: JobContext):
    # Called when a call comes in
    
    # Connect to room
    await ctx.connect()
    
    # Get call config from API
    call_config = await fetch_call_config(ctx.room.name)
    
    # Build pipeline
    agent = VoicePipelineAgent(
        vad=...,
        stt=deepgram.STT(...),
        llm=openai.LLM(...),
        tts=elevenlabs.TTS(...)
    )
    
    # Start session
    session = AgentSession(
        vad=...,
        stt=...,
        llm=...,
        tts=...
    )
    
    await session.start(
        room=ctx.room,
        agent=agent
    )
    
    # Wait for call to end
    await ctx.room.disconnected
```

### Scaling Workers

```bash
# Start 10 workers
for i in {1..10}; do
    docker run -d --name agent-$i \
      -e LIVEKIT_URL=ws://livekit:7880 \
      -e LIVEKIT_API_KEY=devkey \
      -e LIVEKIT_API_SECRET=secret \
      my-agent-image
done
```

Or use Kubernetes HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: voice-agent
  minReplicas: 1
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## User-Agent Integration

### Frontend (Web)

```javascript
import LiveKit from 'livekit-client';

const room = new LiveKit.Room({
  adaptiveStream: true,
  dynacast: true,
});

await room.connect('wss://your-server.com', userToken);

room.on('trackSubscribed', (track, publication, participant) => {
  if (track.kind === 'audio') {
    track.attach().play();
  }
});

// Send audio from microphone
const audioTracks = await room.localParticipant.enableMicrophone();
```

### Frontend (Mobile)

**iOS (Swift):**
```swift
import LiveKit

let room = Room()
try await room.connect(url: "wss://your-server.com", token: token)

// Publish local audio
try await room.localParticipant.enableMicrophone()
```

**Android (Kotlin):**
```kotlin
import io.livekit.android.LiveKit
import io.livekit.android.room

val room = LiveKit.connect(context, url, token)

// Publish local audio
room.localParticipant.enableMicrophone()
```

### SIP Integration (Phone Calls)

```python
from livekit import api as lk

# Create SIP trunk
sip_trunk = await lk.sip.create_trunk(
    name="my-trunk",
    endpoints=[{
        "phone_number": "+1234567890",
        "agent_name": "default"
    }]
)

# Handle inbound call
@server.sip()
async def handle_sip(ctx: SIPContext):
    await ctx.connect()
    # ... rest of agent code
```

---

## LiveKit Internals

### Room Lifecycle

```
Frontend                           LiveKit Server                    Agent Worker
   |                                     |                                |
   |------- Create Room (REST) -------->|                                |
   |<---- Room Created ----------------|                                |
   |                                     |                                |
   |------- Connect (WebRTC) ---------->|                                |
   |                                     |------- Job Request ---------->|
   |                                     |<----- Worker Accepted -------|
   |<---- Connected --------------------|                                |
   |                                     |                                |
   |========= Audio/Video RTP ========>|========= Forwarded ==========>|
   |                                     |                                |
   |------- Disconnect ---------------->|                                |
   |<---- Disconnected -----------------|                                |
```

### Key Concepts

1. **Room:** Virtual space for participants. Has unique name.
2. **Participant:** User or agent in room. Has identity.
3. **Track:** Audio or video stream. Can be published/subscribed.
4. **Publication:** Track being sent from participant.
5. **Subscription:** Track being received by participant.

### Audio Flow

```
User (Mic) → Local Track → Publish → LiveKit SFU → Subscribe → Remote Track → Agent
Agent → Local Track → Publish → LiveKit SFU → Subscribe → Remote Track → User (Speaker)
```

### Data Channels

```python
# Send custom data (e.g., transcript, control messages)
await room.localParticipant.publish_data(
    data=json.dumps({"type": "transcript", "text": "Hello"}),
    topic="transcript"
)

# Receive data
@room.on("data_received")
def on_data(data: DataPacket):
    msg = json.loads(data.text)
```

---

## Phone Number Integration

### Getting Phone Numbers

1. **Twilio:** Buy from Twilio, configure SIP trunk
2. **DID in a Box:** Simple DID provider
3. **Telnyx:** Another DID provider

### Configuring SIP with LiveKit

```yaml
# livekit.yaml (SIP section)
sip:
  enabled: true
  ports:
    - 5060  # SIP UDP
    - 5061 # SIP TLS
  trunk:
    name: "twilio-trunk"
    endpoints:
      - address: "sip.twilio.com:5060"
        transport: "udp"
```

### Outbound Calls

```python
from livekit import api as lk

async def make_call(phone_number: str, agent_id: str):
    # Create room
    room = await lk.room.create_room(
        room_name=f"outbound-{uuid.uuid4()}"
    )
    
    # Create SIP dispatch
    dispatch = await lk.sip.create_dispatch(
        agent_name="default",
        room_name=room.name,
        phone_number=phone_number
    )
    
    return dispatch
```

---

## Frontend Integration

### Agent Configuration UI

```typescript
interface AgentConfig {
  id: string;
  name: string;
  llm_provider: 'openai' | 'anthropic' | 'custom';
  llm_model: string;
  llm_temperature: number;
  tts_provider: 'elevenlabs' | 'deepgram' | 'cartesia';
  tts_voice: string;
  system_prompt: string;
  max_duration: number;  // seconds
  recording_enabled: boolean;
}
```

### Call UI Components

```tsx
function CallPage() {
  const [transcript, setTranscript] = useState([]);
  const [status, setStatus] = useState('idle');

  useEffect(() => {
    const room = connectToRoom();
    
    room.on('trackSubscribed', (track) => {
      if (track.kind === 'audio') track.attach().play();
    });
    
    room.on('dataReceived', (data) => {
      const msg = JSON.parse(data.text);
      if (msg.type === 'transcript') {
        setTranscript(prev => [...prev, msg]);
      }
    });
  }, []);

  return (
    <div>
      <StatusBadge status={status} />
      <TranscriptView messages={transcript} />
      <CallControls onEnd={() => room.disconnect()} />
    </div>
  );
}
```

---

## Complete Implementation Example

### Directory Structure

```
voice-ai-platform/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy models
│   ├── api/                 # API routes
│   │   ├── agents.py
│   │   └── calls.py
│   └── services/
│       ├── livekit.py       # LiveKit client
│       └── llm.py           # LLM clients
├── agent/
│   ├── agent.py             # Main agent code
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Home
│   │   └── call/
│   │       └── [id].tsx     # Call UI
│   └── package.json
└── docker-compose.yml
```

### Backend (`main.py`)

```python
from fastapi import FastAPI, WebSocket
from sqlalchemy import create_engine
from livekit import api as lk

app = FastAPI()
engine = create_engine("postgresql://user:pass@localhost:5432/db")

@app.get("/agents")
async def list_agents():
    return [{"id": "1", "name": "Sales Agent"}]

@app.post("/calls")
async def create_call(call: CallCreate):
    # Create LiveKit room
    room = await lk.room.create_room(
        room_name=call.room_name or f"call-{uuid.uuid4()}"
    )
    
    # Generate tokens
    agent_token = create_token("agent", room.name)
    user_token = create_token("user", room.name)
    
    # Store in DB
    # ...
    
    return {"room": room.name, "agent_token": agent_token, "user_token": user_token}
```

### Agent (`agent.py`)

```python
from livekit.agents import AgentSession, JobContext
from livekit.plugins import deepgram, openai, elevenlabs

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4"),
        tts=elevenlabs.TTS(voice_id="jessica")
    )
    
    agent = Agent(instructions="You are a helpful assistant.")
    await session.start(room=ctx.room, agent=agent)
```

---

## Deployment Guide

### Docker Compose

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: voiceai
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  livekit:
    image: livekit/livekit-server
    ports:
      - "7880:7880"
      - "7881:7881"
      - "50000-50100:50000-50100/udp"
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    command: --config /etc/livekit.yaml

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/voiceai
      - REDIS_URL=redis://redis:6379

  agent:
    build: ./agent
    deploy:
      replicas: 10
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - DATABASE_URL=postgresql://user:pass@postgres:5432/voiceai

volumes:
  pgdata:
```

### Build & Deploy

```bash
# Build all images
docker-compose build

# Start services
docker-compose up -d

# Scale agents
docker-compose up -d --scale agent=20
```

### Frontend Deployment

```bash
# Build Next.js
npm run build

# Deploy to server
scp -r .next user@server:/var/www/html/

# Or use Docker for frontend
docker build -t frontend .
docker run -d -p 3000:3000 -v /var/www/html/.next:/app/.next frontend
```

---

## Common Issues & Debugging

### Agent Not Connecting

**Symptoms:** Agent doesn't join the room

**Debug:**
```bash
# Check agent logs
docker logs agent

# Check LiveKit connection
curl http://localhost:7880/health

# Verify room exists
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:7880/v1/rooms/$ROOM_NAME
```

**Solutions:**
- Check API keys are correct
- Verify network connectivity
- Ensure agent version matches LiveKit server

### Audio Quality Issues

**Symptoms:** Choppy audio, echo, latency

**Debug:**
```bash
# Check WebRTC stats
# In browser console:
room.getStats()

# Check CPU usage
docker stats
```

**Solutions:**
- Reduce agent processing load
- Use dedicated audio processing worker
- Adjust VAD (Voice Activity Detection) settings

### Concurrent Call Limits

**Symptoms:** New calls fail with "no agents available"

**Debug:**
```bash
# Check running agents
docker ps | grep agent

# Check Redis for agent registrations
redis-cli KEYS "agent:*"
```

**Solutions:**
- Scale up agent replicas
- Implement call queuing
- Add load balancer for agents

---

## Latest Production Updates (March 2026)

### Voice Settings & Speed
- Voice speed is applied through ElevenLabs `VoiceSettings` in runtime.
- Voice speed control is effectively for ElevenLabs voices (Deepgram TTS speed override is not used in current runtime path).
- **ElevenLabs v3 & Voice Compatibility**: 
  - ElevenLabs `eleven_v3` is universally compatible with all voices. The dashboard dynamically shows all voices when v3 is selected.
  - V2/v2.5 models dynamically filter voices to only show compatible voices using the ElevenLabs `high_quality_base_model_ids` API data.
  - Runtime code natively uses the standard `elevenlabs.TTS` plugin for all models (including v3), simplifying pipeline initialization.
- GPT-5 family temperature limitation handled:
  - runtime no longer sends custom temperature for `gpt-5*` models (prevents silent-call failures from OpenAI 400 errors).
  - backend chat completion helper retries without temperature when provider rejects it.

### Responsiveness Tuning
- Lower-latency defaults applied in runtime:
  - VAD silence/speech thresholds tuned for faster turn-taking.
  - Deepgram endpointing tuned separately for phone/web calls.
  - OpenAI runtime configured with low-latency defaults (`reasoning_effort`, `verbosity`, completion token cap).

### Call History + Cost
- Latest inbound/outbound cost flow validated with non-zero breakdown:
  - `llm_cost`
  - `stt_cost`
  - `tts_cost`
  - `cost_usd` total
- Usage metadata now also stores applied runtime `voice_speed` and effective LLM temperature behavior for audit/debug.

### Current Deploy Commands (Authoritative)

#### Frontend (`.next` artifact only)
```powershell
cd C:\LiveKit-Project
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force C:\Temp\next-deploy -ErrorAction SilentlyContinue
npm run build
# If Turbopack panics on Windows, fallback:
# npx next build --webpack
Copy-Item -Recurse .next C:\Temp\next-deploy
tar -czf C:\Temp\next-deploy.tar.gz -C C:\Temp next-deploy
scp -i "C:\LiveKit-Project\livekit-company-key.pem" C:\Temp\next-deploy.tar.gz ubuntu@13.135.81.172:/tmp/
ssh -i "C:\LiveKit-Project\livekit-company-key.pem" ubuntu@13.135.81.172 "cd /var/www/html && sudo rm -rf .next && sudo mkdir .next && cd .next && sudo tar -xzf /tmp/next-deploy.tar.gz && sudo mv next-deploy/* . && sudo rm -rf next-deploy && sudo chown -R www-data:www-data . && sudo pm2 restart nextjs"
```

#### Voice Agent (`agent_retell.py`)
```bash
scp -i livekit-company-key.pem agent_retell.py ubuntu@13.135.81.172:~/livekit-agent/agent_retell.py
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "cd ~/livekit-agent && docker compose up -d --build voice-agent"
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "docker logs --tail 80 voice-agent"
```

#### Backend API (`backend/main.py`)
```bash
scp -i livekit-company-key.pem backend/main.py ubuntu@13.135.81.172:~/livekit-dashboard-api/main.py
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "sudo pm2 restart api --update-env"
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "curl -s http://127.0.0.1:8000/health"
```

#### Optional Runtime Flags
```env
STRICT_PROTOOL_FILTER=1
DISCONNECT_GRACE_SEC=20
CHAT_REPLY_TIMEOUT_SEC=40
END_CALL_DISCONNECT_DELAY_SEC=1.0
TRANSFER_HANDOFF_DELAY_SEC=2.5
SILENCE_REPROMPT_SEC=20
STT_ENDPOINTING_PHONE_MS=120
STT_ENDPOINTING_WEB_MS=80
VAD_MIN_SPEECH_DURATION=0.04
VAD_MIN_SILENCE_DURATION=0.30
VAD_PREFIX_PADDING_DURATION=0.35
ELEVENLABS_STREAMING_LATENCY=2
ELEVENLABS_AUTO_MODE=1
OPENAI_REASONING_EFFORT=low
OPENAI_VERBOSITY=low
OPENAI_MAX_COMPLETION_TOKENS=220
```

---

## References

- [LiveKit Documentation](https://docs.livekit.io)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [LiveKit SIP Configuration](https://docs.livekit.io/sip/)
- [Twilio Elastic SIP Trunking](https://www.twilio.com/docs/sip-trunking)
- [Retell AI Documentation](https://docs.retellai.com)
- [WebRTC Internals](https://webrtc.org/getting-started/overview)
- [SIP Protocol RFC 3261](https://tools.ietf.org/html/rfc3261)