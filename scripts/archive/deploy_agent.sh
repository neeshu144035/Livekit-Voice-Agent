#!/bin/bash
# Deploy script for voice agent

cd ~/livekit-agent

# Build and run the agent
docker build -t voice-agent .
docker stop voice-agent || true
docker rm voice-agent || true
docker run -d --name voice-agent \
  --network livekit-agent_default \
  -e LIVEKIT_URL=ws://livekit-server:7880 \
  -e LIVEKIT_API_KEY=devkey \
  -e LIVEKIT_API_SECRET=secret12345678 \
  -e DEEPGRAM_API_KEY=$DEEPGRAM_API_KEY \
  -e MOONSHOT_API_KEY=$MOONSHOT_API_KEY \
  -e SYSTEM_PROMPT="You are a helpful and friendly AI voice assistant." \
  -e VOICE=jessica \
  -e LANGUAGE=en-US \
  voice-agent

echo "Agent deployed! Check logs with: docker logs voice-agent -f"
