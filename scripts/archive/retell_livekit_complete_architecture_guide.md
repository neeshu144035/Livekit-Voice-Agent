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

---

## Architecture Overview

### The Multi-Agent Voice AI Architecture

Retell AI and similar platforms (Vapi, Bland) use a **distributed multi-agent architecture** powered by LiveKit as the real-time media layer. This architecture separates concerns into distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE (API + Orchestrator)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Agent Mgmt  │  │  Registry   │  │  Scheduler  │  │  Session Lifecycle  │ │
│  │   (REST)    │  │  (Redis/    │  │   (Celery)  │  │      Manager        │ │
│  │             │  │  Postgres)  │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────┼────────────────────┼────────────┘
          │                │                │                    │
          ▼                ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT WORKERS (Runtime Processes)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Agent Worker  │  │   Agent Worker  │  │   Agent Worker  │   ...        │
│  │    (Process 1)  │  │    (Process 2)  │  │    (Process N)  │              │
│  │                 │  │                 │  │                 │              │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │              │
│  │ │  STT → LLM  │ │  │ │  STT → LLM  │ │  │ │  STT → LLM  │ │              │
│  │ │  → TTS Loop │ │  │ │  → TTS Loop │ │  │ │  → TTS Loop │ │              │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │              │
│  │       ▲         │  │       ▲         │  │       ▲         │              │
│  └───────┼─────────┘  └───────┼─────────┘  └───────┼─────────┘              │
└──────────┼────────────────────┼────────────────────┼────────────────────────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────────────┐
│                               ▼                                             │
│                      LIVEKIT CLOUD (Real-Time Media Layer)                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         SFU (Selective Forwarding Unit)              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │   Room 1     │  │   Room 2     │  │   Room N     │               │    │
│  │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │               │    │
│  │  │ │ Agent    │ │  │ │ Agent    │ │  │ │ Agent    │ │               │    │
│  │  │ │ Participant│ │  │ │ Participant│ │  │ │ Participant│ │               │    │
│  │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │               │    │
│  │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │               │    │
│  │  │ │ User     │ │  │ │ User     │ │  │ │ User     │ │               │    │
│  │  │ │ Participant│ │  │ │ Participant│ │  │ │ Participant│ │               │    │
│  │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Separation of Concerns**: 
   - Control Plane handles agent lifecycle, configuration, and orchestration
   - LiveKit handles real-time audio streaming (WebRTC)
   - Agent Workers handle AI logic (STT → LLM → TTS)

2. **Process Isolation**: Each agent runs as an isolated process for fault tolerance
3. **Stateful Sessions**: Voice agents are stateful, long-running WebRTC participants
4. **Horizontal Scalability**: Add more worker nodes to handle more concurrent calls

---

## Backend Setup with LiveKit

### 1. LiveKit Cloud Project Setup

First, create a LiveKit Cloud account and project:

```bash
# Install LiveKit CLI
brew install livekit-cli

# Link your LiveKit Cloud project
lk cloud auth

# Get your API credentials from the dashboard
# Set environment variables
export LIVEKIT_URL=wss://your-project.livekit.cloud
export LIVEKIT_API_KEY=your_api_key
export LIVEKIT_API_SECRET=your_api_secret
```

### 2. Agent Worker Implementation

Each agent worker is a Python/Node.js process that connects to LiveKit:

```python
# Python Agent Worker (main.py)
import asyncio
import os
from livekit.agents import (
    cli, 
    WorkerOptions, 
    JobContext, 
    JobRequest,
    AutoSubscribe
)
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import openai, deepgram, cartesia, silero, turn_detector

# Prewarm function - load models before accepting jobs
def prewarm(proc):
    """Load ML models before accepting jobs to avoid cold start latency"""
    proc.load(silero.VAD.load)
    proc.load(turn_detector.MultilingualModel.load)

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for each voice session.
    Called when a job is assigned to this worker.
    """
    # Get job metadata (passed during dispatch)
    job_id = ctx.job.id
    room_name = ctx.job.room.name
    agent_config = ctx.job.metadata  # Custom agent configuration
    
    print(f"Agent starting - Job: {job_id}, Room: {room_name}")
    
    # Connect to the LiveKit room
    # AutoSubscribe.AUDIO_ONLY = subscribe only to audio tracks
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Create the AI agent session with the pipeline
    session = AgentSession(
        # Speech-to-Text: Convert user audio to text
        stt=deepgram.STT(
            model="nova-2",
            language="en-US",
            interim_results=True  # Get partial transcripts for low latency
        ),
        
        # Large Language Model: Generate responses
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7
        ),
        
        # Text-to-Speech: Convert AI responses to audio
        tts=cartesia.TTS(
            voice_id="79a125e8-cd45-4c13-8a67-188112f4c226",  # Choose voice
            speed=1.0
        ),
        
        # Voice Activity Detection: Detect when user starts/stops speaking
        vad=silero.VAD.load(),
        
        # Turn Detection: Know when it's appropriate to respond
        turn_detection=turn_detector.MultilingualModel(),
    )
    
    # Get agent configuration from metadata or database
    agent_instructions = agent_config.get("instructions", "You are a helpful voice assistant.")
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=Agent(instructions=agent_instructions),
        room_input_options={
            "noise_cancellation": True  # Enable Krisp noise cancellation
        }
    )
    
    # Keep the agent running until the call ends
    await session.wait_for_completion()
    print(f"Agent session completed - Job: {job_id}")

# Configure worker options
worker_options = WorkerOptions(
    entrypoint_fnc=entrypoint,
    prewarm_fnc=prewarm,
    # Agent name - used for explicit dispatch (recommended for telephony)
    agent_name="voice-assistant",
    # Load reporting for horizontal scaling
    load_fnc=lambda: 0.0,  # Return 0.0-1.0 based on current load
)

if __name__ == "__main__":
    cli.run_app(worker_options)
```

### 3. Node.js Agent Worker Alternative

```typescript
// Node.js Agent Worker (agent.ts)
import { cli, JobContext, WorkerOptions } from '@livekit/agents';
import { AgentSession, Agent } from '@livekit/agents/voice';
import { OpenAI } from '@livekit/agents-plugin-openai';
import { Deepgram } from '@livekit/agents-plugin-deepgram';
import { Cartesia } from '@livekit/agents-plugin-cartesia';

async function entrypoint(ctx: JobContext) {
  const jobId = ctx.job.id;
  const roomName = ctx.job.room?.name;
  
  console.log(`Agent starting - Job: ${jobId}, Room: ${roomName}`);
  
  // Connect to room
  await ctx.connect({ autoSubscribe: true });
  
  // Create agent session
  const session = new AgentSession({
    stt: new Deepgram.STT({
      model: 'nova-2',
      language: 'en-US',
    }),
    llm: new OpenAI.LLM({
      model: 'gpt-4o-mini',
    }),
    tts: new Cartesia.TTS({
      voiceId: '79a125e8-cd45-4c13-8a67-188112f4c226',
    }),
  });
  
  // Start session
  await session.start({
    room: ctx.room,
    agent: new Agent({
      instructions: 'You are a helpful voice assistant.',
    }),
  });
  
  // Wait for completion
  await session.waitForCompletion();
}

// Run worker
cli.runApp(
  new WorkerOptions({
    entrypointFnc: entrypoint,
    agentName: 'voice-assistant',
  })
);
```

---

## Concurrent Call Handling

### 1. LiveKit SFU Architecture for Massive Concurrency

LiveKit uses a **Selective Forwarding Unit (SFU)** architecture that can handle millions of concurrent calls:

```
┌─────────────────────────────────────────────────────────────────┐
│                     LIVEKIT SFU ARCHITECTURE                     │
│                                                                  │
│   ┌─────────────┐                                               │
│   │  Publisher  │ (User speaking - sends 1 uplink stream)       │
│   │  (User)     │────┐                                          │
│   └─────────────┘    │                                          │
│                      ▼                                          │
│   ┌─────────────────────────────────────┐                       │
│   │         LIVEKIT SFU SERVER          │                       │
│   │                                     │                       │
│   │  ┌─────────┐  ┌─────────┐          │                       │
│   │  │  Room   │  │  Room   │  ...     │                       │
│   │  │ Router  │  │ Router  │          │                       │
│   │  └────┬────┘  └────┬────┘          │                       │
│   │       │            │               │                       │
│   │  ┌────┴────────────┴────┐          │                       │
│   │  │   Media Router       │          │                       │
│   │  │   (No transcoding)   │          │                       │
│   │  └────┬────────────┬────┘          │                       │
│   └───────┼────────────┼───────────────┘                       │
│           │            │                                        │
│           ▼            ▼                                        │
│   ┌─────────────┐  ┌─────────────┐                              │
│   │ Subscriber  │  │ Subscriber  │                              │
│   │  (Agent)    │  │  (Agent)    │                              │
│   └─────────────┘  └─────────────┘                              │
│                                                                  │
│   KEY BENEFITS:                                                  │
│   - Each publisher sends only 1 stream                          │
│   - SFU forwards without transcoding (low CPU)                  │
│   - Subscribers receive only what they need                     │
│   - Horizontal scaling via multiple SFU nodes                   │
└─────────────────────────────────────────────────────────────────┘
```

**Why SFU scales better than MCU:**
- **MCU (Multipoint Control Unit)**: Mixes all streams → High CPU, adds latency
- **SFU (Selective Forwarding Unit)**: Just routes streams → Low CPU, minimal latency

### 2. Worker Pool and Load Balancing

```python
# worker_pool_manager.py
import redis
import asyncio
from typing import Dict, List
import subprocess
import psutil

class WorkerPoolManager:
    """
    Manages a pool of agent worker processes for handling concurrent calls.
    Each worker can handle multiple calls based on capacity.
    """
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.workers: Dict[str, dict] = {}
        self.max_calls_per_worker = 10  # Each worker handles max 10 calls
        
    async def register_worker(self, worker_id: str, capacity: int = 10):
        """Register a new worker in the pool"""
        worker_info = {
            "worker_id": worker_id,
            "capacity": capacity,
            "current_calls": 0,
            "status": "available",
            "last_heartbeat": time.time()
        }
        self.redis.hset(f"worker:{worker_id}", mapping=worker_info)
        
    async def get_available_worker(self) -> str:
        """Find a worker with available capacity"""
        # Scan all workers
        for key in self.redis.scan_iter(match="worker:*"):
            worker_data = self.redis.hgetall(key)
            current = int(worker_data.get(b"current_calls", 0))
            capacity = int(worker_data.get(b"capacity", 10))
            
            if current < capacity:
                worker_id = key.decode().split(":")[1]
                # Increment call count atomically
                self.redis.hincrby(key, "current_calls", 1)
                return worker_id
        
        # No available workers - spawn new one
        return await self.spawn_new_worker()
    
    async def spawn_new_worker(self) -> str:
        """Spawn a new worker process"""
        worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        
        # Start new worker process
        process = subprocess.Popen([
            "python", "agent_worker.py",
            "--worker-id", worker_id,
            "--livekit-url", os.getenv("LIVEKIT_URL"),
            "--api-key", os.getenv("LIVEKIT_API_KEY"),
            "--api-secret", os.getenv("LIVEKIT_API_SECRET")
        ])
        
        # Register in Redis
        await self.register_worker(worker_id)
        return worker_id
    
    async def release_worker_slot(self, worker_id: str):
        """Release a call slot when call ends"""
        self.redis.hincrby(f"worker:{worker_id}", "current_calls", -1)
        
    async def monitor_workers(self):
        """Health check and cleanup dead workers"""
        while True:
            for key in self.redis.scan_iter(match="worker:*"):
                worker_data = self.redis.hgetall(key)
                last_heartbeat = float(worker_data.get(b"last_heartbeat", 0))
                
                # Check if worker is stale (no heartbeat for 30s)
                if time.time() - last_heartbeat > 30:
                    worker_id = key.decode().split(":")[1]
                    await self.remove_worker(worker_id)
                    
            await asyncio.sleep(10)
```

### 3. Horizontal Scaling with Kubernetes

```yaml
# k8s-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-agent-workers
spec:
  replicas: 3  # Start with 3 worker pods
  selector:
    matchLabels:
      app: voice-agent
  template:
    metadata:
      labels:
        app: voice-agent
    spec:
      containers:
      - name: agent-worker
        image: your-registry/voice-agent:latest
        env:
        - name: LIVEKIT_URL
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: url
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-key
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: voice-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: voice-agent-workers
  minReplicas: 3
  maxReplicas: 100  # Scale up to 100 pods for high concurrency
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 4. Concurrency Limits and Rate Limiting

```python
# concurrency_manager.py
from asyncio import Semaphore
import asyncio

class ConcurrencyManager:
    """
    Manages concurrent call limits per agent/organization.
    Retell's model: Free tier = 20 concurrent calls
    Enterprise = unlimited (elastic scaling)
    """
    
    def __init__(self):
        # Track concurrent calls per agent
        self.agent_semaphores: Dict[str, Semaphore] = {}
        self.org_limits: Dict[str, int] = {}
        
    async def initialize_agent_limit(self, agent_id: str, max_concurrent: int):
        """Set concurrency limit for an agent"""
        self.agent_semaphores[agent_id] = Semaphore(max_concurrent)
        
    async def acquire_call_slot(self, agent_id: str, org_id: str) -> bool:
        """
        Try to acquire a slot for a new call.
        Returns True if slot acquired, False if at limit.
        """
        # Check org limit first
        org_current = await self.get_org_concurrent_calls(org_id)
        org_limit = self.org_limits.get(org_id, 100)  # Default 100
        
        if org_current >= org_limit:
            return False
        
        # Check agent limit
        semaphore = self.agent_semaphores.get(agent_id)
        if semaphore:
            acquired = semaphore.acquire(blocking=False)
            if not acquired:
                return False
        
        # Increment counters
        await self.increment_call_counters(agent_id, org_id)
        return True
    
    async def release_call_slot(self, agent_id: str, org_id: str):
        """Release slot when call ends"""
        semaphore = self.agent_semaphores.get(agent_id)
        if semaphore:
            semaphore.release()
        await self.decrement_call_counters(agent_id, org_id)
```

---

## User-Agent Integration

### 1. Agent Configuration and Persona Management

```python
# agent_configuration.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

@dataclass
class AgentConfig:
    """
    Complete agent configuration matching Retell's model.
    Each agent has its own persona, voice, and behavior settings.
    """
    agent_id: str
    agent_name: str
    
    # LLM Configuration
    llm_provider: str  # "openai", "anthropic", "azure"
    llm_model: str     # "gpt-4o", "claude-3-sonnet", etc.
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 150
    
    # Voice Configuration
    voice_provider: str  # "elevenlabs", "cartesia", "openai"
    voice_id: str
    voice_speed: float = 1.0
    
    # STT Configuration
    stt_provider: str = "deepgram"
    stt_model: str = "nova-2"
    stt_language: str = "en-US"
    
    # Behavior Settings
    enable_backchannel: bool = True  # "mm-hmm", "I see"
    enable_interruptions: bool = True
    silence_timeout_ms: int = 1500   # Wait for user to finish
    max_call_duration_min: int = 60
    
    # Function calling (tools)
    available_tools: List[Dict[str, Any]] = None
    
    # Knowledge base (RAG)
    knowledge_base_ids: List[str] = None

class AgentRegistry:
    """
    Central registry for managing all agent configurations.
    Maps users/phone numbers to specific agents.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def create_agent(self, config: AgentConfig) -> str:
        """Create a new agent with configuration"""
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        
        # Store in database
        await self.db.execute("""
            INSERT INTO agents (
                agent_id, agent_name, llm_config, voice_config, 
                behavior_config, tools, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, 
            agent_id,
            config.agent_name,
            json.dumps({
                "provider": config.llm_provider,
                "model": config.llm_model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "system_prompt": config.system_prompt
            }),
            json.dumps({
                "provider": config.voice_provider,
                "voice_id": config.voice_id,
                "speed": config.voice_speed
            }),
            json.dumps({
                "enable_backchannel": config.enable_backchannel,
                "enable_interruptions": config.enable_interruptions,
                "silence_timeout_ms": config.silence_timeout_ms
            }),
            json.dumps(config.available_tools or [])
        )
        
        return agent_id
    
    async def get_agent_for_phone_number(self, phone_number: str) -> Optional[AgentConfig]:
        """Get the agent assigned to a phone number"""
        row = await self.db.fetchrow("""
            SELECT a.* FROM agents a
            JOIN phone_numbers p ON p.agent_id = a.agent_id
            WHERE p.phone_number = $1
        """, phone_number)
        
        if row:
            return self._row_to_config(row)
        return None
    
    async def get_agent_for_user(self, user_id: str, use_case: str) -> Optional[AgentConfig]:
        """Get appropriate agent for a user based on use case"""
        row = await self.db.fetchrow("""
            SELECT a.* FROM agents a
            JOIN user_agent_assignments ua ON ua.agent_id = a.agent_id
            WHERE ua.user_id = $1 AND ua.use_case = $2
        """, user_id, use_case)
        
        if row:
            return self._row_to_config(row)
        return None
```

### 2. Agent Dispatch System

```python
# agent_dispatch.py
from livekit.api import LiveKitAPI
from livekit.protocol.room import CreateRoomRequest
from livekit.protocol.agent import (
    AgentDispatch, 
    CreateAgentDispatchRequest
)

class AgentDispatcher:
    """
    Dispatches agents to rooms based on incoming calls or web requests.
    This is the core orchestration layer.
    """
    
    def __init__(self, livekit_api: LiveKitAPI, agent_registry: AgentRegistry):
        self.api = livekit_api
        self.registry = agent_registry
        
    async def dispatch_for_inbound_call(
        self, 
        phone_number: str,
        caller_number: str,
        call_metadata: dict
    ) -> str:
        """
        Dispatch an agent when a phone call comes in.
        Returns the room name where the agent was dispatched.
        """
        # 1. Find agent for this phone number
        agent_config = await self.registry.get_agent_for_phone_number(phone_number)
        if not agent_config:
            raise ValueError(f"No agent configured for {phone_number}")
        
        # 2. Create a unique room for this call
        room_name = f"call_{phone_number}_{uuid.uuid4().hex[:8]}"
        
        await self.api.room.create_room(
            CreateRoomRequest(
                name=room_name,
                empty_timeout=300,  # Close room after 5 min if empty
                max_participants=2   # Agent + Caller
            )
        )
        
        # 3. Dispatch agent to the room
        dispatch = await self.api.agent.create_agent_dispatch(
            CreateAgentDispatchRequest(
                room_name=room_name,
                agent_name="voice-assistant",  # Matches worker's agent_name
                metadata=json.dumps({
                    "agent_id": agent_config.agent_id,
                    "agent_config": {
                        "llm_provider": agent_config.llm_provider,
                        "llm_model": agent_config.llm_model,
                        "system_prompt": agent_config.system_prompt,
                        "voice_id": agent_config.voice_id,
                        "stt_language": agent_config.stt_language
                    },
                    "call_info": {
                        "phone_number": phone_number,
                        "caller_number": caller_number,
                        "direction": "inbound"
                    }
                })
            )
        )
        
        return room_name
    
    async def dispatch_for_web_call(
        self,
        agent_id: str,
        user_id: str,
        custom_metadata: dict = None
    ) -> dict:
        """
        Dispatch an agent for a web-based call.
        Returns access token and room info for the frontend.
        """
        # 1. Get agent configuration
        agent_config = await self.registry.get_agent(agent_id)
        
        # 2. Create room
        room_name = f"web_{user_id}_{uuid.uuid4().hex[:8]}"
        
        await self.api.room.create_room(
            CreateRoomRequest(
                name=room_name,
                empty_timeout=300,
                max_participants=2
            )
        )
        
        # 3. Generate access token for frontend
        from livekit.api import AccessToken
        
        token = AccessToken(
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET")
        ).with_identity(user_id).with_name("Web User").with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True
            )
        ).to_jwt()
        
        # 4. Dispatch agent
        await self.api.agent.create_agent_dispatch(
            CreateAgentDispatchRequest(
                room_name=room_name,
                agent_name="voice-assistant",
                metadata=json.dumps({
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "agent_config": {
                        "system_prompt": agent_config.system_prompt,
                        "voice_id": agent_config.voice_id,
                    }
                })
            )
        )
        
        return {
            "room_name": room_name,
            "access_token": token,
            "ws_url": os.getenv("LIVEKIT_URL")
        }
```

### 3. Multi-Agent Handoff

```python
# multi_agent_handoff.py
class MultiAgentOrchestrator:
    """
    Handles transferring calls between different agents.
    Example: Sales agent → Support agent → Human agent
    """
    
    async def handoff_to_agent(
        self,
        current_room: str,
        from_agent_id: str,
        to_agent_id: str,
        handoff_context: dict
    ):
        """
        Transfer a call from one agent to another.
        Preserves conversation context.
        """
        # 1. Get conversation transcript
        transcript = await self.get_call_transcript(current_room)
        
        # 2. Create handoff message with context
        handoff_message = f"""
        [AGENT HANDOFF - Previous conversation summary]
        Previous agent handled: {handoff_context.get('topic', 'general inquiry')}
        Customer issue: {handoff_context.get('issue', 'Not specified')}
        Actions taken: {handoff_context.get('actions', 'None')}
        
        Full transcript:
        {transcript}
        """
        
        # 3. Dispatch new agent with context
        await self.api.agent.create_agent_dispatch(
            CreateAgentDispatchRequest(
                room_name=current_room,
                agent_name="voice-assistant",
                metadata=json.dumps({
                    "agent_id": to_agent_id,
                    "is_handoff": True,
                    "handoff_context": handoff_message,
                    "previous_agent": from_agent_id
                })
            )
        )
        
        # 4. Signal old agent to gracefully exit
        await self.signal_agent_exit(current_room, from_agent_id)
```

---

## LiveKit Internals

### 1. Room, Participant, and Track Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     LIVEKIT CORE CONCEPTS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ROOM: Virtual space for communication                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Room: "call_+1234567890_abc123"                         │   │
│  │                                                          │   │
│  │  ┌─────────────────┐        ┌─────────────────┐         │   │
│  │  │  PARTICIPANT    │        │  PARTICIPANT    │         │   │
│  │  │  (Agent)        │        │  (User/Caller)  │         │   │
│  │  │                 │        │                 │         │   │
│  │  │  Identity:      │        │  Identity:      │         │   │
│  │  │  "agent-001"    │        │  "user-123"     │         │   │
│  │  │                 │        │                 │         │   │
│  │  │  Tracks:        │        │  Tracks:        │         │   │
│  │  │  ┌───────────┐  │        │  ┌───────────┐  │         │   │
│  │  │  │ Audio OUT │  │        │  │ Audio OUT │  │         │   │
│  │  │  │ (TTS)     │──┼────────┼──►           │  │         │   │
│  │  │  └───────────┘  │        │  └───────────┘  │         │   │
│  │  │  ┌───────────┐  │        │  ┌───────────┐  │         │   │
│  │  │  │ Audio IN  │◄─┼────────┼──┤ Audio IN  │  │         │   │
│  │  │  │ (STT)     │  │        │  │ (Mic)     │  │         │   │
│  │  │  └───────────┘  │        │  └───────────┘  │         │   │
│  │  └─────────────────┘        └─────────────────┘         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  TRACK PUBLICATION vs TRACK:                                    │
│  - TrackPublication: Metadata about a published track           │
│  - Track: Actual media stream (only when subscribed)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Signaling Flow

```python
# signaling_flow.py
"""
WebRTC Signaling Flow in LiveKit:

1. Client connects to LiveKit server via WebSocket (signaling)
2. Client requests to join a room
3. Server validates token and admits client
4. ICE (Interactive Connectivity Establishment) begins:
   - STUN servers help discover public IP
   - TURN servers relay if direct connection fails
5. WebRTC peer connection established
6. Media flows directly (or via TURN) between participants
"""

async def demonstrate_signaling():
    """Show the complete signaling sequence"""
    
    # Step 1: Create access token (server-side)
    token = AccessToken(
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    ).with_identity("user-123").with_grants(
        VideoGrants(
            room_join=True,
            room="my-room",
            can_publish=True,
            can_subscribe=True
        )
    ).to_jwt()
    
    # Step 2: Client connects with token
    # (This happens in browser/mobile SDK)
    room = Room()
    await room.connect(LIVEKIT_WS_URL, token)
    
    # Step 3: Publish audio track
    audio_track = await room.local_participant.publish_audio_track(
        LocalAudioTrack.create_audio_track("microphone")
    )
    
    # Step 4: Subscribe to other participants' tracks
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == TrackKind.KIND_AUDIO:
            # Play audio
            audio_element = track.attach()
            document.body.appendChild(audio_element)
```

### 3. Media Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUDIO PIPELINE IN LIVEKIT                     │
│                      (STT → LLM → TTS Flow)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER SPEAKS:                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │  Microphone│───►│  WebRTC  │───►│  LiveKit │                  │
│  │  (Browser) │    │  Encode  │    │   SFU    │                  │
│  └──────────┘    └──────────┘    └────┬─────┘                  │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AGENT WORKER (Subscribed Track)             │   │
│  │                                                          │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐            │   │
│  │  │   VAD    │──►│   STT    │──►│   LLM    │            │   │
│  │  │ (Detect  │   │(Deepgram)│   │ (OpenAI) │            │   │
│  │  │  speech) │   │          │   │          │            │   │
│  │  └──────────┘   └──────────┘   └────┬─────┘            │   │
│  │                                      │                  │   │
│  │                                      ▼                  │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐            │   │
│  │  │  Turn    │◄──│  Stream  │◄──│ Response │            │   │
│  │  │ Detection│   │  Tokens  │   │          │            │   │
│  │  └──────────┘   └──────────┘   └──────────┘            │   │
│  │       │                                                │   │
│  │       ▼                                                │   │
│  │  ┌──────────┐   ┌──────────┐                           │   │
│  │  │   TTS    │──►│  WebRTC  │                           │   │
│  │  │(Cartesia)│   │  Encode  │                           │   │
│  │  └──────────┘   └────┬─────┘                           │   │
│  └──────────────────────┼──────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LIVEKIT SFU (Publish Track)                 │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐          │   │
│  │  │  User    │◄───│  WebRTC  │◄───│  Decode  │          │   │
│  │  │  Speaker │    │  Receive │    │          │          │   │
│  │  └──────────┘    └──────────┘    └──────────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  LATENCY TARGETS:                                               │
│  - STT: ~200ms (streaming)                                      │
│  - LLM TTFT: ~300ms (time to first token)                       │
│  - TTS: ~200ms (streaming)                                      │
│  - Network: ~50-100ms                                           │
│  - TOTAL: ~600-800ms end-to-end                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phone Number Integration

### 1. SIP Trunk Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHONE CALL INTEGRATION                        │
│                    (PSTN ←→ SIP ←→ LiveKit)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INBOUND CALL FLOW:                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Caller  │───►│  Twilio/ │───►│  LiveKit │───►│  Agent   │  │
│  │  Phone   │    │  Telnyx  │    │   SIP    │    │  Worker  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │        │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  PSTN Network    SIP Trunk      LiveKit Room      AI Agent     │
│                                                                  │
│  OUTBOUND CALL FLOW:                                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Agent   │───►│  LiveKit │───►│  Twilio/ │───►│  Callee  │  │
│  │  Worker  │    │   SIP    │    │  Telnyx  │    │  Phone   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Setting Up SIP Trunk with Twilio

```python
# sip_trunk_setup.py
"""
Step-by-step SIP trunk configuration for phone number integration.
This connects your phone numbers to LiveKit.
"""

class SIPTrunkManager:
    """Manages SIP trunk configuration for telephony integration"""
    
    def __init__(self, livekit_api: LiveKitAPI):
        self.api = livekit_api
    
    async def setup_inbound_trunk(self, phone_number: str) -> str:
        """
        Configure inbound SIP trunk for receiving calls.
        
        Twilio Configuration:
        1. Create Elastic SIP Trunk in Twilio
        2. Set Origination URI to: sip:YOUR_LIVEKIT_SIP_URI
        3. Assign phone number to trunk
        """
        
        # Create inbound trunk in LiveKit
        trunk_config = {
            "trunk": {
                "name": f"inbound-{phone_number}",
                "numbers": [phone_number],  # E.164 format: +1234567890
                "allowed_addresses": [],  # IP whitelist (optional)
                "auth_username": "",  # Credential auth (optional)
                "auth_password": "",
                # Enable Krisp noise cancellation
                "krisp_enabled": True
            }
        }
        
        # Create via LiveKit CLI or API
        trunk = await self.api.sip.create_sip_inbound_trunk(trunk_config)
        return trunk.sip_trunk_id
    
    async def setup_outbound_trunk(
        self, 
        trunk_name: str,
        sip_provider_address: str,
        username: str,
        password: str,
        phone_numbers: list
    ) -> str:
        """
        Configure outbound SIP trunk for making calls.
        
        Example for Twilio:
        - address: "sip.pstn.twilio.com"
        - username: Your Twilio SIP Domain username
        - password: Your Twilio SIP Domain password
        """
        
        trunk_config = {
            "trunk": {
                "name": trunk_name,
                "address": sip_provider_address,  # e.g., "sip.telnyx.com"
                "numbers": phone_numbers,
                "auth_username": username,
                "auth_password": password,
                "transport": "TCP"  # or "TLS" for encryption
            }
        }
        
        trunk = await self.api.sip.create_sip_outbound_trunk(trunk_config)
        return trunk.sip_trunk_id
    
    async def create_dispatch_rule(
        self, 
        trunk_id: str, 
        agent_id: str
    ) -> str:
        """
        Create dispatch rule: When call comes in, route to agent.
        """
        rule_config = {
            "rule": {
                "trunk_ids": [trunk_id],
                "room_prefix": "call-",  # Room name: call-{random}
                "agent_name": "voice-assistant",
                "metadata": json.dumps({"agent_id": agent_id})
            }
        }
        
        rule = await self.api.sip.create_sip_dispatch_rule(rule_config)
        return rule.sip_dispatch_rule_id

# Twilio Dashboard Configuration Steps:
"""
1. Go to Twilio Console → Elastic SIP Trunking → Create SIP Trunk
2. Configure Origination (Inbound):
   - SIP URI: sip:YOUR_LIVEKIT_SIP_URI
   - Example: sip:abc123.sip.livekit.cloud
3. Configure Termination (Outbound):
   - SIP URI: Your Twilio SIP domain
   - Authentication: Credential-based
4. Add phone numbers to the trunk
5. In LiveKit, create inbound trunk with those numbers
"""
```

### 3. Making Outbound Calls

```python
# outbound_calling.py
class OutboundCallManager:
    """Manages outbound calls from agents"""
    
    def __init__(self, livekit_api: LiveKitAPI):
        self.api = livekit_api
    
    async def make_outbound_call(
        self,
        to_phone_number: str,
        from_phone_number: str,
        agent_id: str,
        outbound_trunk_id: str,
        call_context: dict = None
    ) -> dict:
        """
        Make an outbound call with an AI agent.
        
        Flow:
        1. Create room
        2. Dispatch agent to room
        3. Create SIP participant (dials the number)
        """
        
        # 1. Create a room for this call
        room_name = f"outbound-{uuid.uuid4().hex[:8]}"
        await self.api.room.create_room(
            CreateRoomRequest(
                name=room_name,
                empty_timeout=600,
                max_participants=2
            )
        )
        
        # 2. Dispatch agent first (so it's ready when call connects)
        await self.api.agent.create_agent_dispatch(
            CreateAgentDispatchRequest(
                room_name=room_name,
                agent_name="voice-assistant",
                metadata=json.dumps({
                    "agent_id": agent_id,
                    "call_direction": "outbound",
                    "to_number": to_phone_number,
                    "context": call_context or {}
                })
            )
        )
        
        # 3. Create SIP participant (this dials the number)
        sip_participant = await self.api.sip.create_sip_participant(
            {
                "sip_trunk_id": outbound_trunk_id,
                "sip_call_to": to_phone_number,  # E.164 format
                "room_name": room_name,
                "participant_identity": f"phone-{to_phone_number}",
                "participant_name": to_phone_number,
                "krisp_enabled": True,  # Noise cancellation
                "headers": {
                    "X-From-Number": from_phone_number
                }
            }
        )
        
        return {
            "room_name": room_name,
            "sip_participant_id": sip_participant.participant_identity,
            "status": "dialing"
        }
```

### 4. Retell-Style Phone Number Management

```python
# phone_number_management.py
class PhoneNumberManager:
    """
    Retell-style phone number management.
    Maps phone numbers to agents for inbound/outbound calls.
    """
    
    def __init__(self, db, sip_manager: SIPTrunkManager):
        self.db = db
        self.sip = sip_manager
    
    async def import_phone_number(
        self,
        phone_number: str,
        provider: str,  # "twilio", "telnyx", "vonage"
        sip_trunk_config: dict,
        inbound_agent_id: str = None,
        outbound_agent_id: str = None,
        nickname: str = None
    ) -> dict:
        """
        Import an external phone number and configure it for AI calls.
        """
        
        # 1. Validate phone number format (E.164)
        if not phone_number.startswith("+"):
            raise ValueError("Phone number must be in E.164 format (+1234567890)")
        
        # 2. Create SIP trunk in LiveKit
        trunk_id = await self.sip.setup_inbound_trunk(phone_number)
        
        # 3. Store in database
        await self.db.execute("""
            INSERT INTO phone_numbers (
                phone_number, provider, trunk_id,
                inbound_agent_id, outbound_agent_id,
                nickname, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, 'active', NOW())
        """, 
            phone_number, provider, trunk_id,
            inbound_agent_id, outbound_agent_id, nickname
        )
        
        # 4. Create dispatch rule if inbound agent assigned
        if inbound_agent_id:
            rule_id = await self.sip.create_dispatch_rule(trunk_id, inbound_agent_id)
            await self.db.execute(
                "UPDATE phone_numbers SET dispatch_rule_id = $1 WHERE phone_number = $2",
                rule_id, phone_number
            )
        
        return {
            "phone_number": phone_number,
            "trunk_id": trunk_id,
            "status": "active"
        }
    
    async def assign_agent_to_number(
        self,
        phone_number: str,
        inbound_agent_id: str = None,
        outbound_agent_id: str = None
    ):
        """
        Assign different agents for inbound vs outbound calls.
        """
        updates = []
        params = []
        
        if inbound_agent_id:
            updates.append("inbound_agent_id = $1")
            params.append(inbound_agent_id)
            
            # Update dispatch rule
            number_data = await self.db.fetchrow(
                "SELECT trunk_id FROM phone_numbers WHERE phone_number = $1",
                phone_number
            )
            if number_data:
                await self.sip.create_dispatch_rule(
                    number_data["trunk_id"], 
                    inbound_agent_id
                )
        
        if outbound_agent_id:
            updates.append("outbound_agent_id = ${}".format(len(params) + 1))
            params.append(outbound_agent_id)
        
        if updates:
            query = f"""
                UPDATE phone_numbers 
                SET {', '.join(updates)}
                WHERE phone_number = ${len(params) + 1}
            """
            params.append(phone_number)
            await self.db.execute(query, *params)
    
    async def make_call_with_number(
        self,
        from_number: str,
        to_number: str,
        context: dict = None
    ) -> dict:
        """
        Make an outbound call using a specific phone number.
        Uses the outbound agent assigned to that number.
        """
        # Get number configuration
        number_data = await self.db.fetchrow("""
            SELECT outbound_agent_id, trunk_id 
            FROM phone_numbers 
            WHERE phone_number = $1
        """, from_number)
        
        if not number_data:
            raise ValueError(f"Phone number {from_number} not configured")
        
        if not number_data["outbound_agent_id"]:
            raise ValueError(f"No outbound agent assigned to {from_number}")
        
        # Make the call
        return await self.sip.make_outbound_call(
            to_phone_number=to_number,
            from_phone_number=from_number,
            agent_id=number_data["outbound_agent_id"],
            outbound_trunk_id=number_data["trunk_id"],
            call_context=context
        )
```

---

## Frontend Integration

### 1. Web SDK Integration (React)

```typescript
// RetellWebClient.tsx - Frontend SDK integration
import { RetellWebClient } from 'retell-client-js-sdk';
import { useEffect, useRef, useState } from 'react';

interface RetellCallProps {
  agentId: string;
  userId: string;
  onCallStart?: () => void;
  onCallEnd?: () => void;
  onTranscriptUpdate?: (transcript: TranscriptEntry[]) => void;
}

interface TranscriptEntry {
  role: 'agent' | 'user';
  content: string;
  timestamp: number;
}

export function RetellCallButton({
  agentId,
  userId,
  onCallStart,
  onCallEnd,
  onTranscriptUpdate
}: RetellCallProps) {
  const [isCallActive, setIsCallActive] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const retellClient = useRef<RetellWebClient | null>(null);
  const transcriptRef = useRef<TranscriptEntry[]>([]);

  // Initialize Retell client
  useEffect(() => {
    retellClient.current = new RetellWebClient();
    
    // Listen for call events
    retellClient.current.on('call_started', () => {
      console.log('Call started');
      setIsCallActive(true);
      setIsConnecting(false);
      onCallStart?.();
    });
    
    retellClient.current.on('call_ended', () => {
      console.log('Call ended');
      setIsCallActive(false);
      setIsConnecting(false);
      onCallEnd?.();
    });
    
    retellClient.current.on('error', (error) => {
      console.error('Call error:', error);
      setIsCallActive(false);
      setIsConnecting(false);
    });
    
    // Real-time transcript updates
    retellClient.current.on('transcript_update', (update) => {
      transcriptRef.current = [...transcriptRef.current, {
        role: update.role,
        content: update.content,
        timestamp: Date.now()
      }];
      onTranscriptUpdate?.(transcriptRef.current);
    });
    
    return () => {
      retellClient.current?.stopCall();
    };
  }, []);

  const startCall = async () => {
    if (!retellClient.current) return;
    
    setIsConnecting(true);
    
    try {
      // 1. Get access token from your backend
      const response = await fetch('/api/create-web-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, user_id: userId })
      });
      
      if (!response.ok) {
        throw new Error('Failed to create call');
      }
      
      const { access_token } = await response.json();
      
      // 2. Start the call with Retell SDK
      await retellClient.current.startCall({
        accessToken: access_token,
        sampleRate: 24000,  // Audio quality
        // Optional: specify devices
        // captureDeviceId: 'default',
        // playbackDeviceId: 'default',
        emitRawAudioSamples: false  // Set true for audio visualization
      });
      
    } catch (error) {
      console.error('Failed to start call:', error);
      setIsConnecting(false);
    }
  };

  const endCall = () => {
    retellClient.current?.stopCall();
  };

  return (
    <button
      onClick={isCallActive ? endCall : startCall}
      disabled={isConnecting}
      className={`call-button ${isCallActive ? 'active' : ''}`}
    >
      {isConnecting ? 'Connecting...' : isCallActive ? 'End Call' : 'Start Call'}
    </button>
  );
}
```

### 2. Backend Endpoint for Web Calls

```python
# web_call_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CreateWebCallRequest(BaseModel):
    agent_id: str
    user_id: str
    metadata: dict = None

@app.post("/api/create-web-call")
async def create_web_call(request: CreateWebCallRequest):
    """
    Create a web call and return access token for frontend.
    This matches Retell's create-web-call API.
    """
    
    # 1. Get agent configuration
    agent_config = await agent_registry.get_agent(request.agent_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 2. Create room and dispatch agent
    call_info = await agent_dispatcher.dispatch_for_web_call(
        agent_id=request.agent_id,
        user_id=request.user_id,
        custom_metadata=request.metadata
    )
    
    # 3. Log call start
    call_id = f"call_{uuid.uuid4().hex[:16]}"
    await db.execute("""
        INSERT INTO calls (
            call_id, agent_id, user_id, room_name,
            call_type, status, started_at
        ) VALUES ($1, $2, $3, $4, 'web', 'ongoing', NOW())
    """, call_id, request.agent_id, request.user_id, call_info["room_name"])
    
    return {
        "call_id": call_id,
        "access_token": call_info["access_token"],
        "room_name": call_info["room_name"],
        "ws_url": call_info["ws_url"]
    }
```

### 3. LiveKit Client SDK (Direct WebRTC)

```typescript
// Direct LiveKit SDK integration (alternative to Retell SDK)
import { Room, RoomEvent, Track } from 'livekit-client';

class LiveKitVoiceClient {
  private room: Room | null = null;
  private audioElement: HTMLAudioElement | null = null;

  async connect(token: string, wsUrl: string): Promise<void> {
    // Create room with noise cancellation
    this.room = new Room({
      adaptiveStream: true,
      dynacast: true,
      publishDefaults: {
        simulcast: false,
        audioPreset: {
          maxBitrate: 24000,
        },
      },
    });

    // Set up event listeners
    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio) {
        // Play agent audio
        this.audioElement = track.attach();
        document.body.appendChild(this.audioElement);
      }
    });

    this.room.on(RoomEvent.TrackUnsubscribed, (track) => {
      track.detach();
    });

    // Connect to room
    await this.room.connect(wsUrl, token);

    // Enable microphone
    await this.room.localParticipant.enableMicrophone();
  }

  async disconnect(): Promise<void> {
    if (this.audioElement) {
      this.audioElement.remove();
    }
    await this.room?.disconnect();
  }
}
```

### 4. Real-Time Transcript Display

```tsx
// TranscriptDisplay.tsx
import { useState, useEffect } from 'react';

interface TranscriptEntry {
  role: 'agent' | 'user';
  content: string;
  timestamp: number;
  isFinal: boolean;
}

export function TranscriptDisplay({ 
  entries 
}: { 
  entries: TranscriptEntry[] 
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="transcript-container">
      {entries.map((entry, index) => (
        <div 
          key={index} 
          className={`transcript-entry ${entry.role}`}
        >
          <span className="speaker">
            {entry.role === 'agent' ? '🤖 AI' : '👤 You'}
          </span>
          <span className={`content ${!entry.isFinal ? 'interim' : ''}`}>
            {entry.content}
          </span>
          <span className="timestamp">
            {new Date(entry.timestamp).toLocaleTimeString()}
          </span>
        </div>
      ))}
      <div ref={scrollRef} />
    </div>
  );
}
```

---

## Complete Implementation Example

### Project Structure

```
voice-ai-platform/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── worker.py              # LiveKit agent worker
│   │   └── pipelines.py           # STT/LLM/TTS configurations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── web_calls.py           # Web call endpoints
│   │   ├── phone_calls.py         # Phone call endpoints
│   │   └── agents.py              # Agent management endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings
│   │   ├── database.py            # Database models
│   │   └── livekit_client.py      # LiveKit API wrapper
│   ├── telephony/
│   │   ├── __init__.py
│   │   ├── sip_manager.py         # SIP trunk management
│   │   └── phone_numbers.py       # Phone number operations
│   ├── deployment/
│   │   ├── Dockerfile
│   │   ├── k8s-deployment.yaml
│   │   └── docker-compose.yml
│   └── main.py                    # FastAPI app entry
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CallButton.tsx
│   │   │   ├── TranscriptDisplay.tsx
│   │   │   └── AudioVisualizer.tsx
│   │   ├── hooks/
│   │   │   └── useRetellCall.ts
│   │   └── services/
│   │       └── api.ts
│   └── package.json
└── README.md
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download ML models (VAD, turn detector)
RUN python -c "from livekit.plugins import silero, turn_detector; silero.VAD.load(); turn_detector.MultilingualModel.load()"

# Copy code
COPY . .

# Expose port
EXPOSE 8080

# Run worker
CMD ["python", "-m", "agents.worker"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  # LiveKit Agent Workers
  agent-worker:
    build: ./backend
    environment:
      - LIVEKIT_URL=wss://your-project.livekit.cloud
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@db:5432/voice_ai
    deploy:
      replicas: 3
    depends_on:
      - redis
      - db

  # API Server
  api:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8080
    ports:
      - "8080:8080"
    environment:
      - LIVEKIT_URL=wss://your-project.livekit.cloud
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - DATABASE_URL=postgresql://postgres:password@db:5432/voice_ai
    depends_on:
      - db

  redis:
    image: redis:7-alpine

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=voice_ai
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Key Takeaways

### Architecture Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Real-time Media** | LiveKit (WebRTC SFU) | Handle audio streaming at scale |
| **Agent Workers** | Python/Node.js processes | Run STT→LLM→TTS pipelines |
| **Orchestration** | Redis + Celery | Manage agent lifecycle |
| **Phone Integration** | SIP Trunking (Twilio/Telnyx) | Connect PSTN calls |
| **Frontend** | Retell SDK / LiveKit SDK | WebRTC client connection |

### Scaling Checklist

- [ ] Use SFU architecture (not MCU) for media routing
- [ ] Run each agent as isolated process for fault tolerance
- [ ] Implement worker pools with load reporting
- [ ] Use Kubernetes HPA for auto-scaling
- [ ] Set concurrency limits per agent/organization
- [ ] Enable Krisp noise cancellation for phone calls
- [ ] Use explicit agent dispatch (not automatic)
- [ ] Implement health checks and automatic failover

### Latency Optimization

| Component | Target Latency | Optimization |
|-----------|---------------|--------------|
| STT | 200ms | Streaming, interim results |
| LLM | 300ms TTFT | GPT-4o-mini, streaming tokens |
| TTS | 200ms | Streaming synthesis |
| Network | 50-100ms | Edge deployment, TURN servers |
| **Total** | **600-800ms** | End-to-end target |

---

## Self-Hosted LiveKit Setup (Production)

### 1. AWS Infrastructure Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS INFRASTRUCTURE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │              AWS Security Group (EC2)                   │ │
│   │  Inbound Rules:                                          │ │
│   │  - SSH (22): Your IP                                     │ │
│   │  - HTTP (80): 0.0.0.0/0                                │ │
│   │  - HTTPS (443): 0.0.0.0/0                              │ │
│   │  - Custom TCP (7880): 0.0.0.0/0  (LiveKit RTC)         │ │
│   │  - Custom TCP (7881): 0.0.0.0/0  (LiveKit RTC)         │ │
│   │  - Custom TCP (5060): 0.0.0.0/0   (SIP)                │ │
│   │  - Custom UDP (5060): 0.0.0.0/0   (SIP)                │ │
│   │  - Custom UDP (10000-20000): 0.0.0.0/0 (RTP Media)     │ │
│   │  - Custom UDP (50000-60000): 0.0.0.0/0 (RTP Media)     │ │
│   │  - Custom TCP (8000): 0.0.0.0/0   (Dashboard API)     │ │
│   │  - Custom TCP (3000): 0.0.0.0/0   (Frontend)           │ │
│   └─────────────────────────────────────────────────────────┘ │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │              EC2 Instance (t3.large recommended)        │ │
│   │  - Ubuntu 22.04 LTS                                    │ │
│   │  - 4+ vCPU, 8GB+ RAM                                   │ │
│   │  - Security Group as above                              │ │
│   └─────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # LiveKit Server
  livekit-server:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit.yaml --dev
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
      - "50000-60000:50000-60000/udp"
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    environment:
      - LIVEKIT_KEYS=${LIVEKIT_KEYS}
    restart: unless-stopped

  # Redis (for SIP and agent state)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  # SIP Service (for phone calls)
  livekit-sip:
    image: livekit/livekit-sip:latest
    ports:
      - "5060:5060/udp"
      - "5060:5060/tcp"
      - "10000-10100:10000-10100/udp"
    environment:
      - LIVEKIT_URL=http://livekit-server:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - SIP_API_KEY=${SIP_API_KEY}
      - SIP_API_SECRET=${SIP_API_SECRET}
    depends_on:
      - livekit-server
      - redis
    restart: unless-stopped

  # Voice Agent Workers
  voice-agent:
    build: ./voice-agent
    environment:
      - LIVEKIT_URL=ws://livekit-server:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
      - DASHBOARD_API_URL=http://host.docker.internal:8000
    volumes:
      - ./agent:/app
    depends_on:
      - livekit-server
    restart: unless-stopped
    deploy:
      replicas: 2

  # Dashboard API
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - LIVEKIT_URL=http://livekit-server:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped
```

### 3. LiveKit Server Config

```yaml
# livekit.yaml
port: 7880
rtc:
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
  tcp_port: 7881
  udp_port: 7882
  # Use your server's public IP
  external_ip: "13.135.81.172"

keys:
  devkey: secret12345678

room:
  auto_create: true
  empty_timeout: 300
  max_participants: 10

logging:
  level: debug
  pion_level: warn

# Redis for state
redis:
  address: redis:6379

# SIP configuration
sip:
  enabled: true
  port: 5060
```

---

## Twilio SIP Trunking Setup

### 1. Twilio Console Configuration

1. **Create Elastic SIP Trunk:**
   - Go to Elastic SIP Trunking → Trunks
   - Create new trunk: `LiveKit-Outbound`
   - Note the SIP Trunk SID (starts with `TK...`)

2. **Configure Origination (for inbound calls):**
   - Add Origination URI: `sip:YOUR_EC2-PUBLIC-IP:5060`
   - Example: `sip:13.135.81.172:5060`

3. **Configure Termination (for outbound calls):**
   - SIP URI: `sip:livekit-outbound-XXXXXXXX.pstn.twilio.com`
   - Add authentication credentials

4. **Add Phone Numbers:**
   - Buy phone numbers in Twilio
   - Assign them to the SIP trunk

### 2. Twilio Phone Numbers Used

| Number | Purpose | Format |
|--------|---------|--------|
| +447426999697 | Inbound/Outbound | UK Number |
| +916238602144 | Testing Outbound | India Number |

---

## SIP Dispatch Rule Configuration

### The Critical Part: Agent Dispatch

The dispatch rule MUST specify which agent to dispatch. Without this, the room is created but no agent joins!

```bash
# Update dispatch rule to include agent dispatch
# Using LiveKit CLI

# Create dispatch rule with roomConfig.agents
lk sip dispatch create --json << 'EOF'
{
  "rule": {
    "dispatchRuleDirect": {
      "roomName": "call_sarah"
    }
  },
  "name": "sarah-direct",
  "trunkIds": ["ST_SWvXMHU52uP7"],
  "roomConfig": {
    "agents": [{
      "agentName": "sarah"
    }]
  }
}
EOF
```

**Key Points:**
- `roomConfig.agents[0].agentName` must match the agent worker's `agent_name`
- Without this, the agent won't be automatically dispatched to the room
- The dispatch rule creates the room, but agent must be explicitly specified

### Verification Commands

```bash
# List dispatch rules
lk sip dispatch list

# Check SIP trunk info
lk sip trunk list

# View LiveKit server logs
docker logs livekit-server -f

# View SIP logs  
docker logs livekit-sip -f
```

---

## Voice Agent Implementation

### Complete Working Agent Code

```python
# agent_retell.py
import os
import json
import asyncio
import logging
import time
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentSession, AutoSubscribe,
    JobContext, JobProcess, WorkerOptions,
    cli, function_tool, RunContext
)
from livekit.plugins import deepgram, openai, silero
import httpx

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-retell")

DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://host.docker.internal:8000").rstrip("/")

def prewarm(proc: JobProcess):
    vad = silero.VAD.load()
    proc.userdata["vad"] = vad

async def entrypoint(ctx: JobContext):
    # Get room name and extract agent info
    room_name = ctx.room.name
    logger.info(f"Starting session for room: {room_name}")
    
    # Parse room name to determine direction and agent
    agent_id = 5  # Default
    direction = "inbound"  # Default
    
    if room_name.startswith("call_"):
        parts = room_name.split("_")
        if len(parts) >= 3 and parts[1].isdigit():
            try:
                agent_id = int(parts[1])
                direction = "outbound"
                logger.info(f"Web/outbound call for agent_id: {agent_id}")
            except:
                agent_id = 5
        else:
            # Room like "call_sarah" from dispatch rule
            direction = "inbound"
            logger.info(f"Inbound call (dispatch room): {room_name}")
    elif room_name.startswith("call-") or room_name.startswith("sip-"):
        direction = "inbound"
        logger.info(f"Inbound call detected: {room_name}")
    
    # Get agent config from API
    config = await get_agent_config(agent_id)
    if not config:
        logger.error(f"No config found for agent_id: {agent_id}")
        return
    
    # Get phone numbers from SIP participant
    from_number = None
    to_number = None
    for p in ctx.room.participants.values():
        if p.identity.startswith("sip_"):
            # Parse SIP identity: sip_+1234567890
            phone = p.identity.replace("sip_", "").replace("phone-", "")
            if phone.startswith("+"):
                from_number = phone
    
    direction = direction or config.get("direction", "inbound")
    logger.info(f"Call direction determined: {direction}")
    
    # Setup LLM
    model = config.get("llm_model", "gpt-4o-mini")
    if "moonshot" in model.lower():
        llm = openai.LLM(
            model="moonshot-v1-8k-chat",
            base_url="https://api.moonshot.cn/v1",
            api_key=os.getenv("MOONSHOT_API_KEY")
        )
    else:
        llm = openai.LLM(model=model)
    
    # Get voice
    voice_id = config.get("voice_id", "sarah")
    tts_voice = voice_id
    
    # Create session with appropriate STT model
    stt_model = "nova-2-phonecall" if (from_number or to_number) else "nova-2-general"
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(language=config.get("language", "en-GB"), model=stt_model),
        llm=llm,
        tts=deepgram.TTS(model=tts_voice),
    )
    
    # Get system prompt
    sys_prompt = config.get("system_prompt", "You are a helpful voice assistant.")
    
    # Welcome message handling
    welcome_type = config.get("welcome_message_type", "user_speaks_first")
    welcome_msg = config.get("welcome_message", "")
    logger.info(f"Welcome type: {welcome_type}, Welcome msg: {welcome_msg}, Direction: {direction}")
    
    # Create agent
    agent = Agent(
        instructions=sys_prompt,
        tools=[...],  # Your tools here
    )
    
    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Start session
    await session.start(agent=agent, room=ctx.room)
    logger.info("Session started successfully")
    
    # Handle welcome message - agent speaks first
    if welcome_type == "agent_greets":
        greeting_text = welcome_msg.strip() if welcome_msg.strip() else "Hello! How can I help you today?"
        logger.info(f"Sending greeting immediately: {greeting_text}")
        try:
            await session.generate_reply(instructions=greeting_text)
            logger.info("Greeting sent successfully")
        except Exception as e:
            logger.error(f"Failed to send greeting: {e}")
    
    # Wait for call to end
    await asyncio.Future()

async def get_agent_config(agent_id: int) -> dict:
    """Fetch agent config from dashboard API"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{DASHBOARD_API_URL}/api/agents/{agent_id}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
    return None

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        agent_name="sarah"  # Must match dispatch rule's agentName
    ))
```

---

## Common Issues & Debugging

### Issue 1: Inbound calls reach server but agent doesn't join

**Symptoms:**
- SIP logs show room created: `room: call_sarah`
- Agent logs show no job request
- Call disconnects with "no response from servers"

**Solution:**
- Check dispatch rule has `roomConfig.agents.agentName` set
- Verify agent_name matches exactly (case-sensitive)
- Check agent worker is registered: `docker logs voice-agent | grep registered`

### Issue 2: Agent doesn't speak welcome message

**Symptoms:**
- Agent joins room but stays silent
- User speaks but no response

**Solution:**
- Check `welcome_message_type` in agent config
- For "agent_greets": ensure `session.generate_reply()` is called after session.start()
- For "user_speaks_first": this is expected behavior - agent waits for user

### Issue 3: SIP trunk not receiving calls

**Symptoms:**
- No logs in livekit-sip
- Calls show "flood" rejection

**Solution:**
- Check AWS Security Group allows port 5060 TCP + UDP
- Verify Twilio Origination URI points to correct IP
- Check firewall: `sudo iptables -L -n | grep 5060`

### Issue 4: Deepgram API error (newline in headers)

**Symptoms:**
- Error: "ValueError: Newline or carriage return detected in headers"
- Agent can't speak

**Solution:**
- Fix .env file line endings: `sed -i 's/\r$//' .env`
- Rebuild and restart container

---

## References

- [LiveKit Documentation](https://docs.livekit.io)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [LiveKit SIP Configuration](https://docs.livekit.io/sip/)
- [Twilio Elastic SIP Trunking](https://www.twilio.com/docs/sip-trunking)
- [Retell AI Documentation](https://docs.retellai.com)
- [WebRTC Internals](https://webrtc.org/getting-started/overview)
- [SIP Protocol RFC 3261](https://tools.ietf.org/html/rfc3261)
