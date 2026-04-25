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
14. [Agent-to-Agent Handoff Optimization (April 25, 2026)](#agent-to-agent-handoff-optimization-april-25-2026)

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
XAI_API_KEY=
XAI_REALTIME_MODEL=grok-voice-think-fast-1.0
XAI_REALTIME_BASE_URL=https://api.x.ai/v1
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

#### Important Constraint
- If the user explicitly selects `eleven_v3`, the backend will honor it, but live latency will still be higher because ElevenLabs v3 uses the slower HTTP/non-WebSocket path.

---

### Future Roadmap
- [ ] Implement Tamil, Telugu, and Kannada regional support.
- [ ] Validate ElevenLabs V3 expressive voices for non-English dialects.
- [ ] Add latency benchmarks for Indian subcontinent API routing.

---

### Agent-to-Agent Handoff Optimization (April 25, 2026)

#### Implementation Summary
- **Seamless Transfer Protocol**: Implemented a Retell-style `agent_transfer` system function that allows a live worker to swap the active agent identity mid-call without disconnecting the room or bridging new PSTN lines.
- **Handoff Context Persistence**: The new subagent automatically receives the full conversational context:
  - Preserved caller identity (name, phone number)
  - Recent transcript summary (from the previous agent)
  - Extracted caller memory (facts gathered during the current call)
  - Runtime variables (dynamic state)
- **Concurrency Crash Prevention**: Resolved a critical session instability where simultaneous `generate_reply()` calls during handoff would crash the xAI/OpenAI Realtime websocket. The handoff now relies on a minimal tool return message (`"Transfer completed successfully."`) to naturally trigger the new agent's greeting.
- **Natural Transfer Hold**: Added a hardcoded **4.5-second ringing pause** in the transfer logic. This simulates a realistic "hold" period before the subagent picks up, preventing the subagent from speaking over the previous agent's closing sentence.
- **Persona Isolation**: Moved the `update_agent()` call to occur *after* the ringing delay. This ensures the subagent's instructions and personality only become active when it is time to speak, preventing "identity bleed" where the subagent might hallucinate the previous agent's persona.

#### Deployment Note
- Re-run the voice-agent rebuild command after any changes to `agent_retell.py` transfer logic:
  ```bash
  ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "cd ~/livekit-agent && docker compose up -d --build voice-agent"
  ```

---

### Suggested Prompt For A New Chat
```text
Continue from the April 25, 2026 LiveKit project state in C:\LiveKit-Project.

Current known state:
- Agent-to-agent transfer (handoff) is fully operational.
- Handoff context (memory, transcript) correctly passed to subagents.
- Concurrency crash fixed by removing redundant generate_reply and using minimal tool return.
- Natural 4.5s ringing delay added to the handoff process.
- Subagent activation moved to AFTER the delay to prevent identity bleed.
- xAI unified realtime models use generate_reply for greetings instead of session.say().

Please verify with commands:
- docker logs --tail 50 voice-agent
- python -m py_compile agent_retell.py
```

---

## Project State Summary (April 25, 2026)

### Chat Summary
- The main goal of the latest work was to fix the agent-to-agent transfer logic to be robust, natural, and free of concurrency crashes.
- The focus areas were:
  - Handoff context serialization and backend retrieval.
  - Resolving 400 Bad Request errors on duplicate handoff attempts.
  - Fixing "rt_session not available" crashes during handoff.
  - Implementing a realistic 4.5s transfer delay.
  - Ensuring subagents introduce themselves according to their specific prompts.
