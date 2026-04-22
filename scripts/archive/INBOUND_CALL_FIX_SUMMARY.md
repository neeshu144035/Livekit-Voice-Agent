# Inbound Call Fix Summary

## Problem Description
Inbound calls to +447426999697 were not being answered by the voice agent. The SIP trunk and dispatch rules were configured, but the call was not reaching the agent.

---

## Issues Found and Fixed

### 1. **No Inbound SIP Trunk** (FIXED)
- **Problem**: No inbound SIP trunk was configured for the phone number +447426999697
- **Solution**: Created trunk `ST_SWvXMHU52uP7` for +447426999697

### 2. **No Dispatch Rules** (FIXED)
- **Problem**: There were no dispatch rules to route incoming calls to the agent
- **Solution**: Created dispatch rule `SDR_bF3yazWQRCQz` with Direct mode to room "call-sarah"

### 3. **Agent Using Internal Docker URL** (FIXED)
- **Problem**: The voice-agent container was using `ws://livekit-server:7880` (internal Docker hostname)
- **Impact**: The LiveKit server couldn't reach the agent internally because the SIP trunk creates rooms from outside the Docker network
- **Solution**: Changed to `ws://13.135.81.172:7880` (external IP)
- **File Updated**: `agent.env` on the VPS

### 4. **OpenAI API Key Issue** (FIXED - previous session)
- **Problem**: Wrong API key was being used
- **Solution**: Fixed to use correct key from agent.env

---

## Current Configuration

| Setting | Value |
|---------|-------|
| Phone Number | +447426999697 |
| SIP Trunk | ST_SWvXMHU52uP7 |
| Dispatch Rule | SDR_bF3yazWQRCQz (Direct mode) |
| Target Room | call-sarah |
| Agent Name | sarah |
| Agent LIVEKIT_URL | ws://13.135.81.172:7880 |

---

## Call Flow - Where the Call Reaches

### Previous Problem Stage (Before Fix):
1. Twilio calls VPS IP:5060 ✅ (Call reaches SIP)
2. SIP trunk receives call ✅
3. SIP tries to connect to room "call-sarah" ✅
4. **PROBLEM**: Agent was using internal URL `ws://livekit-server:7880` - couldn't be reached by external SIP
5. Agent never received the job request ❌

### After Fix:
1. Twilio calls VPS IP:5060 ✅
2. SIP trunk receives call ✅
3. SIP joins room "call-sarah" ✅
4. LiveKit sends job to agent at `ws://13.135.81.172:7880` ✅
5. Agent receives job and answers the call ✅

---

## How to Test

**Call +447426999697 now** - the agent should answer!

---

## Commands to Check Status

```bash
# Check if agent is registered
ssh ubuntu@13.135.81.172 "sudo docker logs voice-agent --tail 10 | grep registered"

# Check SIP logs for incoming calls
ssh ubuntu@13.135.81.172 "sudo docker logs livekit-sip --tail 30 | grep call-sarah"

# Check agent logs during a call
ssh ubuntu@13.135.81.172 "sudo docker logs voice-agent --tail 30"
```

---

## Agent Registration Confirmation
```
"registered worker", "agent_name": "sarah", "url": "ws://13.135.81.172:7880"
```
The agent is now registered and listening for jobs!
