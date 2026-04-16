# LiveKit Voice and Chat AI Dashboard

A production-oriented voice and chat agent platform built with Next.js, FastAPI, LiveKit, Twilio SIP, and Python agent workers.

## What is included

- `app/` and `components/`: active Next.js dashboard UI
- `backend/main.py`: FastAPI control plane for auth, agents, calls, phone numbers, transcripts, and analytics
- `agent_retell.py`: main LiveKit voice agent worker
- `deployment/frontend-single-source/`: frontend deployment script
- `docker-compose*.yml`, `Dockerfile.agent`, `livekit.yaml`, `sip-config.yaml`: local/runtime infrastructure

This repo intentionally excludes local machine state, secrets, logs, backups, and old snapshots.

## Verified status

- `npm run build` passes
- `backend/main.py` compiles
- `agent_retell.py` compiles

## Main features

- Dashboard login/session handling
- Voice agent create/edit/delete/duplicate
- Prompt, model, voice, TTS, and language configuration
- Web test calls through LiveKit
- Phone number and SIP mapping for inbound/outbound calls
- Outbound call webhook flow
- Call history, transcript, latency, and cost tracking
- Chat preview and chatbot dashboard
- Custom functions and built-in tools

## Local development

### Frontend

```bash
npm install
npm run dev
```

### Backend

```bash
pip install -r backend/requirements.txt
python backend/main.py
```

### Voice agent

```bash
pip install -r requirements.txt
python agent_retell.py start
```

## Environment setup

Copy `.env.example` to `.env` and fill in the real credentials for:

- LiveKit
- Postgres / Redis
- OpenAI or Moonshot
- Deepgram
- ElevenLabs

## Important entrypoints

- Frontend app: `app/dashboard/page.tsx`
- Agent editor: `app/agent/[id]/page.tsx`
- Backend API: `backend/main.py`
- Voice worker: `agent_retell.py`
