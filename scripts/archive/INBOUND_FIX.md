# Fix Summary - Inbound Calls Not Picking Up

## Issues Found & Fixed:

1. **agent_retell.py**: Fixed room name parsing to handle `call_{agent_id}_{uuid}` format
2. **backend/main.py**: Added `agent_name` field to AgentCreate/AgentUpdate schemas
3. **create_dispatch.json**: Updated dispatch rule format for LiveKit CLI

## What You Need To Do On Your VPS:

### Step 1: Upload and Rebuild the Agent

```powershell
# Upload the fixed agent_retell.py
scp -i livekit-company-key.pem agent_retell.py ubuntu@13.135.81.172:/home/ubuntu/livekit-agent/

# SSH and rebuild/restart the agent
ssh -i livekit-company-key.pem ubuntu@13.135.81.172
cd /home/ubuntu/livekit-agent
sudo docker stop voice-agent && sudo docker rm voice-agent
sudo docker build -t voice-agent -f Dockerfile.agent .
sudo docker run -d --name voice-agent --network livekit-agent_default --add-host=host.docker.internal:host-gateway -e LIVEKIT_URL=ws://livekit-server:7880 -e LIVEKIT_API_KEY=devkey -e LIVEKIT_API_SECRET=secret12345678 -e OPENAI_API_KEY=sk-z9M8if5d04D8H3IU57IGfu4OAsMZPFlHc0CiP3RmsMWg1xwx -e DEEPGRAM_API_KEY=672fd1a3bf1688178e38ac9f5ebb4d703306c22b -e DASHBOARD_API_URL=http://host.docker.internal:8000 voice-agent
```

### Step 2: Create SIP Dispatch Rule (CRITICAL for inbound calls)

```bash
# SSH into your VPS, then run:
ssh -i livekit-company-key.pem ubuntu@13.135.81.172

# Install LiveKit CLI if not installed
curl -sSfL https://get.livekit.io/lk | sh

# Create dispatch rule for agent "sarah"
lk sip dispatch create <<'EOF'
{
  "name": "sarah-inbound",
  "dispatchRule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  },
  "roomConfig": {
    "agents": [
      {
        "agentName": "sarah"
      }
    ]
  }
}
EOF

# List dispatch rules to verify
lk sip dispatch list

# List trunks to get trunk ID
lk sip trunk list

# Associate dispatch rule with trunk (if needed)
lk sip dispatch update --id <dispatch-rule-id> --trunk-id <trunk-id>
```

### Step 3: Verify Twilio Configuration

In Twilio Console:
1. Go to your SIP Trunk → Origination
2. Ensure the SIP URI points to: `sip:13.135.81.172:5060`
3. Make sure the phone number is added to the trunk

### Step 4: Test

```bash
# Check agent logs
ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "sudo docker logs voice-agent -f"

# Now call your Twilio number and watch the logs
```

## Expected Flow:
1. You call +447426999697 (your Twilio number)
2. Twilio sends call to sip:13.135.81.172:5060
3. LiveKit receives call, creates room `call_5_xxx`
4. Dispatch rule triggers, sends job to voice-agent container
5. Agent joins room and answers
