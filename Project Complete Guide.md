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
12. [Explicit Runtime Control (April 2026)](#explicit-runtime-control-april-2026)
13. [Project State Summary (April 2026)](#project-state-summary-april-2026)

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

### Deployment Topology Used In This Repo

This repository does **not** use one single deployment method for every component. The current production layout is:

1. **Frontend dashboard (Next.js)**  
   - Built locally with `npm run build`
   - Only the `.next` build artifact is uploaded to the VPS
   - The VPS serves/restarts the frontend with **PM2** (`nextjs` process)

2. **Backend API (FastAPI)**  
   - Source file is synced to the VPS under `~/livekit-dashboard-api/`
   - Process is restarted with **PM2** (`api` process)

3. **Voice agent runtime (`agent_retell.py`)**  
   - Source file is synced to the VPS under `~/livekit-agent/`
   - Container is rebuilt/restarted with **Docker Compose**

4. **LiveKit / SIP / supporting infra**  
   - Containerized with Docker Compose
   - Repo contains both [`docker-compose.yml`](docker-compose.yml) and [`docker-compose.production.yml`](docker-compose.production.yml)

The important point is that production is a **hybrid deployment**: PM2 for frontend/backend app processes, Docker Compose for the voice/media stack.

### Compose Files In The Repo

#### Local / simpler stack: `docker-compose.yml`

[`docker-compose.yml`](docker-compose.yml) is the smaller stack used for local/self-hosted bring-up. It includes:

- `redis`
- `livekit-server`
- `livekit-sip`
- `voice-agent`
- `postgres`

This file is useful for local testing and single-host setup, especially when the backend is reachable from the agent via:

```env
DASHBOARD_API_URL=http://host.docker.internal:8000
```

#### Production-oriented stack: `docker-compose.production.yml`

[`docker-compose.production.yml`](docker-compose.production.yml) is the closer representation of the VPS/container deployment. It adds production-specific details such as:

- health checks
- explicit container names
- `backend-api` service wiring
- multiple voice agent containers (`voice-agent-1`, `voice-agent-2`, `voice-agent-3`)
- `minio` for recordings
- `livekit-server` launched with `--node-ip=13.135.81.172`

This is the better reference when documenting infra topology, but the current day-to-day deploy flow below is still the authoritative operational workflow.

### Current Production Deploy Flow

Before running any of the VPS deploy commands below, make sure the SSH private key file [`livekit-company-key.pem`](livekit-company-key.pem) is available locally. This key is used by `scp` and `ssh` to authenticate to the production server.

#### 1. Frontend Dashboard (Next.js via PM2)

The frontend is built on Windows and only the `.next` artifact is pushed to the VPS.

This deploy requires [`livekit-company-key.pem`](livekit-company-key.pem).

```powershell
# Step 1: Clean and rebuild locally
cd C:\LiveKit-Project
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
npm run build

# Step 2: Copy .next to temp and create tar (using /tmp for Linux path)
Remove-Item -Recurse -Force C:\Temp\next-deploy -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path C:\Temp\next-deploy -Force
Copy-Item -Path .next\* -Destination C:\Temp\next-deploy\ -Recurse -Force

# Step 3: Create tar.gz in /tmp (Linux)
cd /tmp && rm -f next-deploy.tar.gz && tar -czf next-deploy.tar.gz next-deploy

# Step 4: Upload to VPS
scp -i C:\LiveKit-Project\livekit-company-key.pem /tmp/next-deploy.tar.gz ubuntu@13.135.81.172:/tmp/

# Step 5: Extract on VPS (critical: ensure fresh .next folder)
ssh -i C:\LiveKit-Project\livekit-company-key.pem ubuntu@13.135.81.172 "cd /var/www/html && sudo rm -rf .next && sudo mkdir .next && cd .next && sudo tar -xzf /tmp/next-deploy.tar.gz && sudo mv next-deploy/* . && sudo rm -rf next-deploy && sudo chown -R www-data:www-data . && sudo pm2 restart nextjs"

# Step 6: Verify (check BUILD_ID matches local)
ssh -i C:\LiveKit-Project\livekit-company-key.pem ubuntu@13.135.81.172 "cat /var/www/html/.next/BUILD_ID"
```

**Verification:**
- confirm build completed locally
- confirm `.next` exists on VPS under `/var/www/html/.next`
- confirm PM2 restart succeeds for `nextjs`

#### 2. Voice Agent Runtime (`agent_retell.py`)

The production voice agent entrypoint is currently [`agent_retell.py`](agent_retell.py). The deploy flow is file sync + container rebuild:

This deploy requires [`livekit-company-key.pem`](livekit-company-key.pem).

```bash
scp -i livekit-company-key.pem agent_retell.py ubuntu@13.135.81.172:~/livekit-agent/agent_retell.py
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "cd ~/livekit-agent && docker compose up -d --build voice-agent"
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "docker logs --tail 80 voice-agent"
```

**What this does:**
- uploads the latest runtime logic
- rebuilds the `voice-agent` container
- tails recent logs for smoke validation

#### 3. Backend API (`backend/main.py`)

The current operational backend deploy is a targeted sync of [`backend/main.py`](backend/main.py) followed by PM2 restart:

This deploy requires [`livekit-company-key.pem`](livekit-company-key.pem).

```bash
scp -i livekit-company-key.pem backend/main.py ubuntu@13.135.81.172:~/livekit-dashboard-api/main.py
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "sudo pm2 restart api --update-env"
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "curl -s http://127.0.0.1:8000/health"
```

**Verification:**
- PM2 process `api` restarts cleanly
- local VPS health endpoint returns success on `127.0.0.1:8000/health`

### Runtime Environment Notes

The current agent runtime relies on environment tuning like:

```env
STRICT_PROTOOL_FILTER=1
DISCONNECT_GRACE_SEC=20
CHAT_REPLY_TIMEOUT_SEC=40
END_CALL_DISCONNECT_DELAY_SEC=1.0
TRANSFER_HANDOFF_DELAY_SEC=2.5
SILENCE_REPROMPT_SEC=25
STT_ENDPOINTING_PHONE_MS=40
STT_ENDPOINTING_WEB_MS=40
VAD_MIN_SPEECH_DURATION=0.015
VAD_MIN_SILENCE_DURATION=0.05
VAD_PREFIX_PADDING_DURATION=0.12
ELEVENLABS_STREAMING_LATENCY=1
ELEVENLABS_AUTO_MODE=1
OPENAI_REASONING_EFFORT=low
OPENAI_VERBOSITY=low
OPENAI_MAX_COMPLETION_TOKENS=220
```

**Note**: For multilingual (language=multi), the runtime now uses Nova-3 with endpointing_ms=100 for best Hindi/English detection.

These values are particularly relevant to [`agent_retell.py`](agent_retell.py), where latency, silence handling, greeting behavior, and OpenAI/ElevenLabs runtime tuning are applied.

### Recommended Post-Deploy Smoke Checks

After any production deploy, run the checks that match the component you changed:

```bash
# Backend health
curl -s http://127.0.0.1:8000/health

# Voice agent logs
docker logs --tail 80 voice-agent

# PM2 status
pm2 status
```

For frontend deploys, also verify the dashboard loads and key pages render without a blank screen.  
For backend deploys, validate agent list / call history endpoints.  
For voice-agent deploys, place at least one web or phone test call and confirm transcript + cost data continue to populate.

### Practical Notes

- Treat the PM2 + targeted file sync flow as the **authoritative production runbook** right now.
- Treat the compose files as the **infrastructure reference** for service topology and local/containerized environments.
- Do not assume the generic idea of "docker-compose up everything" matches the current VPS rollout, because frontend and backend are not currently deployed that way.

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
# Clean and rebuild locally
cd C:\LiveKit-Project
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
npm run build

# Copy to temp and create tar (Linux path /tmp)
Remove-Item -Recurse -Force C:\Temp\next-deploy -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path C:\Temp\next-deploy -Force
Copy-Item -Path .next\* -Destination C:\Temp\next-deploy\ -Recurse -Force

# Create tar.gz in /tmp
cd /tmp && rm -f next-deploy.tar.gz && tar -czf next-deploy.tar.gz next-deploy

# Upload and deploy
scp -i C:\LiveKit-Project\livekit-company-key.pem /tmp/next-deploy.tar.gz ubuntu@13.135.81.172:/tmp/
ssh -i C:\LiveKit-Project\livekit-company-key.pem ubuntu@13.135.81.172 "cd /var/www/html && sudo rm -rf .next && sudo mkdir .next && cd .next && sudo tar -xzf /tmp/next-deploy.tar.gz && sudo mv next-deploy/* . && sudo rm -rf next-deploy && sudo chown -R www-data:www-data . && sudo pm2 restart nextjs"

# Verify
ssh -i C:\LiveKit-Project\livekit-company-key.pem ubuntu@13.135.81.172 "cat /var/www/html/.next/BUILD_ID"
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


```env
STRICT_PROTOOL_FILTER=1
DISCONNECT_GRACE_SEC=20
CHAT_REPLY_TIMEOUT_SEC=40
END_CALL_DISCONNECT_DELAY_SEC=1.0
TRANSFER_HANDOFF_DELAY_SEC=2.5
SILENCE_REPROMPT_SEC=25
STT_ENDPOINTING_PHONE_MS=40
STT_ENDPOINTING_WEB_MS=40
VAD_MIN_SPEECH_DURATION=0.015
VAD_MIN_SILENCE_DURATION=0.05
VAD_PREFIX_PADDING_DURATION=0.12
ELEVENLABS_STREAMING_LATENCY=1
ELEVENLABS_AUTO_MODE=1
OPENAI_REASONING_EFFORT=low
OPENAI_VERBOSITY=low
OPENAI_MAX_COMPLETION_TOKENS=220
```

**Note**: For multilingual, runtime uses Nova-3 with language=multi.

---

## References

- [LiveKit Documentation](https://docs.livekit.io)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [LiveKit SIP Configuration](https://docs.livekit.io/sip/)
- [Twilio Elastic SIP Trunking](https://www.twilio.com/docs/sip-trunking)
- [Retell AI Documentation](https://docs.retellai.com)
- [WebRTC Internals](https://webrtc.org/getting-started/overview)
- [SIP Protocol RFC 3261](https://tools.ietf.org/html/rfc3261)

---

## 🎙️ Production Updates (April 2026)

### Voice Agent & ElevenLabs v3 Integration
- **Bug Fix**: Fixed a critical `TypeError` in `agent_retell.py` by ensuring `voice_id` and `model` are passed as strings to the `elevenlabs.TTS` constructor, matching the LiveKit plugin v1.4.2 signature.
- **Multilingual Deployment**: Added native support for **Hindi** (`hi`) and **Malayalam** (`ml`) across the entire platform.
    - **Language Enforcement**: Implemented automated system prompt injection in `agent_retell.py` that forces the AI to respond natively in the selected language.
    - **Full-Stack Update**: 
        - Backend schemas (`backend/main.py`) updated to validate `hi`, `hi-IN`, `ml`, and `ml-IN`.
        - Frontend dropdowns (`CreateAgentWizard.tsx` and Agent Detail pages) updated with Hindi/Malayalam options.
- **Automated Deployment Process**:
    - **Backend**: API logic synced to VPS and restarted via `pm2 restart api`.
    - **Frontend**: Dashboard built locally, zipped, and deployed to VPS `/var/www/html/` with `.next` replacement.
    - **Agent**: Docker container rebuilt with updated prompt logic and restarted.

---

### Explicit Runtime Control (April 20, 2026)

#### Backend/Runtime Behavior Changes
- **Agent settings now drive runtime behavior**: The backend and voice agent runtime now follow only what the app saves, eliminating hidden defaults:
  - [`agent_retell.py:279`](agent_retell.py) - `voice_runtime_mode` is resolved from saved config only, no longer forced by env/defaults
  - [`agent_retell.py:287`](agent_retell.py) - `voice_realtime_model` is read from saved config only
  - ElevenLabs models are no longer auto-swapped; the app's explicit selection is honored
  - Greeting path no longer invents a fallback script - uses what's saved

- **Safe latency optimizations retained** (do not rewrite config):
  - [`agent_retell.py:269`](agent_retell.py) - Pooled dashboard HTTP clients for faster API calls
  - [`agent_retell.py:2144`](agent_retell.py) - Parallel config/function fetches at call start

- **Explicit ElevenLabs model required**:
  - [`backend/main.py:1276`](backend/main.py) - Create/update now require an explicit ElevenLabs `tts_model`
  - API no longer advertises a default ElevenLabs model
  - Backend validates: `tts_model must be explicitly selected in the app when tts_provider=elevenlabs`

- **LLM defaults reverted to Moonshot**:
  - [`backend/main.py:87`](backend/main.py) - `llm_model` defaults to `moonshot-v1-8k`
  - [`CreateAgentWizard.tsx:227`](components/CreateAgentWizard.tsx) - Default LLM is `moonshot-v1-8k`
  - [`app/agent/[id]/page.tsx:269`](app/agent/[id]/page.tsx) - Default LLM is `moonshot-v1-8k`

#### Frontend/UI Changes
- **Voice Runtime mode explicitly exposed**:
  - [`CreateAgentModal.tsx:541`](components/CreateAgentModal.tsx) - Voice Runtime dropdown (Pipeline / Realtime text + TTS)
  - [`CreateAgentWizard.tsx:678`](components/CreateAgentWizard.tsx) - Voice Runtime dropdown
  - [`app/agent/[id]/page.tsx:1116`](app/agent/[id]/page.tsx) - Voice Runtime dropdown

- **Explicit ElevenLabs model/voice selection**:
  - Users must explicitly select ElevenLabs TTS model and voice
  - No more auto-switching provider/model behind the user's back
  - Warning displayed when `eleven_v3` is selected (slower HTTP path vs WebSocket)

#### Important Constraint
- If the user explicitly selects `eleven_v3`, the backend will honor it, but live latency will still be higher because ElevenLabs v3 uses the slower HTTP/non-WebSocket path.

#### Current Docs Checked (April 20, 2026)
- LiveKit Realtime plugin
- OpenAI Realtime VAD
- ElevenLabs models
- ElevenLabs WebSockets

---

### Future Roadmap
- [ ] Implement Tamil, Telugu, and Kannada regional support.
- [ ] Validate ElevenLabs V3 expressive voices for non-English dialects.
- [ ] Add latency benchmarks for Indian subcontinent API routing.

---

## Project State Summary (April 20, 2026)

### Chat Summary
- The main goal of the latest work was to make sure the app's selected settings actually control backend/runtime behavior for real-time calls and webcalls, instead of the runtime silently using older defaults.
- The focus areas were:
  - deployment documentation cleanup
  - explicit use of `livekit-company-key.pem` in deploy steps
  - ElevenLabs v3 verification
  - multilingual language support
  - Malayalam support
  - command-based verification without relying on browser testing

### What Was Updated In Code
- [`backend/main.py`](backend/main.py)
  - Call metadata is now populated from the saved agent configuration at call creation time.
  - Webcalls now persist selected values such as `tts_provider`, `tts_model`, `language`, `voice`, `voice_speed`, and `llm_temperature` immediately.
  - Usage updates were extended so later syncs can also store effective `language` and `tts_voice_id_used`.
  - **NEW**: Create/update now require explicit ElevenLabs `tts_model`; no default advertised
  - **NEW**: LLM default reverted to `moonshot-v1-8k`
- [`agent_retell.py`](agent_retell.py)
  - ElevenLabs `eleven_v3` is now the preferred multilingual/expressive TTS path.
  - Added `multi` language support for multilingual mode.
  - Added stronger language enforcement so the assistant answers in the chosen language.
  - Malayalam now falls back through multilingual STT mode rather than staying on a weaker unsupported path.
  - Added runtime protections to prevent speech output from reading unresolved placeholders like `{{name}}` or raw tags like `<break ...>`.
  - Reduced forced low-token phone behavior unless explicitly enabled, which should help speech feel less clipped.
  - **NEW**: `voice_runtime_mode` and `voice_realtime_model` read from saved config only
  - **NEW**: No auto-swapping of ElevenLabs models - app selection is honored
  - **NEW**: Greeting uses saved script, no fallback invention
  - **RETAINED**: Pooled HTTP clients and parallel config/function fetches (latency wins)
- Frontend/editor-side updates were also made in:
  - [`app/agent/[id]/page.tsx`](app/agent/[id]/page.tsx)
  - [`components/CreateAgentWizard.tsx`](components/CreateAgentWizard.tsx)
  - [`components/CreateAgentModal.tsx`](components/CreateAgentModal.tsx)
  - [`components/VoiceCallModal.tsx`](components/VoiceCallModal.tsx)
  - **NEW**: Voice Runtime mode (Pipeline / Realtime text + TTS) explicitly exposed
  - **NEW**: Explicit ElevenLabs model/voice selection required
  - **NEW**: Warning shown for `eleven_v3` (slower HTTP path)
- Language options now include a multilingual selection similar to Retell-style language switching:
  - `Multilingual (Auto)`
  - plus UK English, Hindi, Malayalam, and the other existing locale choices

### Deployment And VPS Update
- The deployment guide was updated to reflect the real hybrid production model:
  - frontend/backend managed on the VPS with PM2
  - voice/media stack managed with Docker Compose
- The deployment section now explicitly mentions the SSH key:
  - [`livekit-company-key.pem`](livekit-company-key.pem)
- Backend and worker code were synced to the VPS and restarted successfully during verification.

### Verification Completed With Commands
- Local verification completed successfully:
  - `python -m py_compile backend/main.py agent_retell.py`
  - `npx tsc --noEmit`
- Remote/VPS verification completed with command-line checks:
  - `curl http://127.0.0.1:8000/api/agents/21`
  - `curl http://127.0.0.1:8000/api/token/21`
  - `curl http://127.0.0.1:8000/api/call-history/<call_id>/details`
  - `docker compose up -d --build voice-agent`

### Last Webcall Verification
- Recent agent `21` webcalls on April 20, 2026 were verified to use ElevenLabs v3, not v2.5:
  - `call_21_733f3ec74135435f`
  - `call_21_a83d9a8012b840ba`
- An earlier call on the same date still showed `deepgram`, which confirms pre-fix mixed behavior:
  - `call_21_275da76623d046ff`
- A fresh token-generated webcall on April 20, 2026 created `call_21_ff7428538e294260`, and its metadata immediately showed:
  - `tts_provider=elevenlabs`
  - `tts_model=eleven_v3`
  - `language=hi`
  - `voice_speed=1.0`
  - `llm_temperature=0.85`

### Current Limitation
- Malayalam TTS is supported with ElevenLabs v3.
- Malayalam live understanding is still limited by the current real-time STT path.
- The runtime now falls back to multilingual STT mode for Malayalam, which is better than the old behavior, but it is not yet equal to strong native Malayalam real-time recognition.

### Best Next Improvements
- Clean saved agent prompts so they use natural spoken punctuation instead of literal tags or placeholder-heavy formatting.
- Improve multilingual STT if Malayalam understanding needs to be production-grade.
- Add per-language prompt and pacing presets for more human-sounding delivery.

### Suggested Prompt For A New Chat
```text
Continue from the April 20, 2026 LiveKit project state in C:\LiveKit-Project.

Current known state after latest deploy:
- backend/main.py and agent_retell.py updated so app-selected settings control runtime (voice_runtime_mode, voice_realtime_model, ElevenLabs model, greeting)
- explicit ElevenLabs tts_model required on create/update; no auto-swapping
- LLM default reverted to moonshot-v1-8k
- frontend (CreateAgentModal, CreateAgentWizard, agent page) exposes Voice Runtime mode explicitly
- safe latency wins retained: pooled HTTP clients, parallel config/function fetches
- Voice agent container rebuilt and restarted
- PM2 frontend/backend restarted
- curl health check passed

Prior verified state:
- agent 21 webcalls use ElevenLabs eleven_v3
- multilingual mode, Hindi, Malayalam, UK English supported
- deployment is hybrid: PM2 for frontend/backend, Docker Compose for voice-agent

Please verify with commands:
- python -m py_compile backend/main.py agent_retell.py
- npx tsc --noEmit
- curl http://127.0.0.1:8000/health
- docker logs --tail 20 voice-agent
```

---

## Multilingual STT Discovery (April 20, 2026 - Evening)

### The Problem
- Nova-2 with `language=multi` was NOT detecting Hindi properly
- STT was returning 0ms processing - no speech detected at all

### The Solution (Nova-3 for Multilingual)
- **Use Nova-3** with `language=multi` instead of Nova-2
- Nova-3 has ~21% better multilingual streaming than Nova-2
- Better code-switching for Hindi-English conversations
- Faster too!

### Key Settings (agent_retell.py)
```python
# Multilingual STT config (line ~2483)
if stt_language == "multi":
    stt_model = "nova-3"  # NOT nova-2!
    stt_kwargs["language"] = "multi"
    stt_kwargs["endpointing_ms"] = 100  # Faster response

# VAD tuning for speech detection
VAD_MIN_SILENCE_DURATION = 0.05  # Was 0.08, lower = faster detection
```

### Verification
```bash
# Check STT config in logs
docker logs voice-agent 2>&1 | grep "STT config"

# Output should show:
# STT config: model=nova-3 language=multi endpointing_ms=100
```

### Summary
- Nova-3 + language=multi = ✅ Working Hindi detection
- Nova-2 + language=multi = ❌ Not working
- Same Deepgram API, different model performance
- Retell AI and others recommend Nova-3 now for multilingual
