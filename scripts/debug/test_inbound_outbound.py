#!/usr/bin/env python3
"""
Test script to verify inbound/outbound call functionality.
Run this locally or on the server to test.
"""

import os
import sys
import json
import asyncio
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")

async def test_api_health():
    """Test if API is running"""
    print("\n=== Testing API Health ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/", timeout=5.0)
            print(f"API Status: {resp.status_code}")
            return resp.status_code == 200
    except Exception as e:
        print(f"API Error: {e}")
        return False

async def test_list_agents():
    """Test listing agents"""
    print("\n=== Testing List Agents ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/api/agents/", timeout=5.0)
            if resp.status_code == 200:
                agents = resp.json()
                print(f"Found {len(agents)} agents:")
                for a in agents:
                    print(f"  - ID: {a.get('id')}, Name: {a.get('name')}, agent_name: {a.get('agent_name')}")
                return agents
            else:
                print(f"Error: {resp.text}")
                return []
    except Exception as e:
        print(f"Error: {e}")
        return []

async def test_list_phone_numbers():
    """Test listing phone numbers"""
    print("\n=== Testing List Phone Numbers ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/api/phone-numbers/", timeout=5.0)
            if resp.status_code == 200:
                phones = resp.json()
                print(f"Found {len(phones)} phone numbers:")
                for p in phones:
                    print(f"  - {p.get('phone_number')} | Status: {p.get('status')} | Inbound Agent: {p.get('inbound_agent_name')}")
                return phones
            else:
                print(f"Error: {resp.text}")
                return []
    except Exception as e:
        print(f"Error: {e}")
        return []

async def test_sip_endpoint():
    """Test getting SIP endpoint"""
    print("\n=== Testing SIP Endpoint ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/api/phone-numbers/sip-endpoint", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                print(f"SIP Endpoint: {data.get('sip_endpoint')}")
                print(f"LiveKit URL: {data.get('livekit_url')}")
                return data
            else:
                print(f"Error: {resp.text}")
                return None
    except Exception as e:
        print(f"Error: {e}")
        return None

async def test_update_agent_name(agent_id: int, agent_name: str):
    """Update agent's dispatch name"""
    print(f"\n=== Updating Agent {agent_id} agent_name to '{agent_name}' ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{API_URL}/api/agents/{agent_id}",
                json={"agent_name": agent_name},
                timeout=10.0
            )
            if resp.status_code == 200:
                print(f"Updated successfully: {resp.json()}")
                return True
            else:
                print(f"Error: {resp.text}")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False

async def test_outbound_call(phone_id: int, to_number: str):
    """Test making an outbound call"""
    print(f"\n=== Testing Outbound Call from phone {phone_id} to {to_number} ===")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_URL}/api/phone-numbers/{phone_id}/outbound",
                json={"to_number": to_number},
                timeout=30.0
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"Outbound call initiated:")
                print(f"  - Room: {data.get('room_name')}")
                print(f"  - Call SID: {data.get('twilio_call_sid')}")
                return data
            else:
                print(f"Error: {resp.status_code}: {resp.text}")
                return None
    except Exception as e:
        print(f"Error: {e}")
        return None

async def main():
    print("=" * 60)
    print("VOICE AGENT TEST SUITE")
    print("=" * 60)
    
    # Test 1: API Health
    api_ok = await test_api_health()
    if not api_ok:
        print("\n❌ API is not running. Please start the backend first.")
        return
    
    # Test 2: List Agents
    agents = await test_list_agents()
    if not agents:
        print("\n⚠️ No agents found. Create an agent first.")
        return
    
    # Test 3: Get SIP Endpoint
    sip = await test_sip_endpoint()
    
    # Test 4: List Phone Numbers
    phones = await test_list_phone_numbers()
    
    # Test 5: Update agent with dispatch name
    print("\n=== Setting up agent dispatch names ===")
    for agent in agents:
        agent_id = agent.get('id')
        current_name = agent.get('agent_name')
        
        # Set agent_name based on agent ID for easy dispatch
        dispatch_name = f"agent-{agent_id}"
        if current_name != dispatch_name:
            await test_update_agent_name(agent_id, dispatch_name)
    
    # Print setup instructions
    print("\n" + "=" * 60)
    print("SETUP INSTRUCTIONS")
    print("=" * 60)
    print("""
For inbound calls to work, you need to:

1. Create a SIP Dispatch Rule on LiveKit:
   - Room prefix: call-
   - Agent name: sarah (or your agent's name in agent_retell.py)
   
   Run on your VPS:
   lk sip dispatch create <<'EOF'
   {
     "name": "sarah-inbound",
     "dispatchRule": {
       "dispatchRuleIndividual": {
         "roomPrefix": "call-"
       }
     },
     "roomConfig": {
       "agents": [{"agentName": "sarah"}]
     }
   }
   EOF

2. Update Twilio SIP Trunk Origination:
   - SIP URI: sip:13.135.81.172:5060

3. Rebuild and deploy the agent:
   cd /home/ubuntu/livekit-agent
   sudo docker build -t voice-agent -f Dockerfile.agent .
   sudo docker stop voice-agent && sudo docker rm voice-agent
   sudo docker run -d --name voice-agent ...
""")

if __name__ == "__main__":
    asyncio.run(main())
