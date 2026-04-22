#!/usr/bin/env python3
"""
Script to diagnose and fix SIP inbound call issues.
Run this on your VPS to check and create the dispatch rule.
"""

import os
import asyncio
import json
import httpx

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://livekit-server:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")

async def check_sip_trunks():
    """Check existing SIP trunks"""
    print("\n=== Checking SIP Trunks ===")
    lk_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{lk_url}/grpc/livekit.SIP/ListSIPTrunk",
                headers={
                    "Authorization": f"Bearer {generate_token()}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            print(f"SIP Trunks: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error checking trunks: {e}")

def generate_token() -> str:
    """Generate a LiveKit API token"""
    import jwt
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    token = jwt.encode(
        {
            "iss": LIVEKIT_API_KEY,
            "sub": "system",
            "exp": now + timedelta(hours=1),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "nbf": int(now.timestamp()),
        },
        LIVEKIT_API_SECRET,
        algorithm="HS256"
    )
    return token

async def create_dispatch_rule():
    """Create a SIP dispatch rule for the agent"""
    print("\n=== Creating SIP Dispatch Rule ===")
    
    # Dispatch rule config - sends calls to agent named "sarah"
    dispatch_config = {
        "dispatchRule": {
            "dispatchRuleIndividual": {
                "roomPrefix": "call-"
            }
        },
        "name": "sarah-inbound-rule",
        "roomConfig": {
            "agents": [
                {"agentName": "sarah"}
            ]
        }
    }
    
    lk_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{lk_url}/grpc/livekit.SIP/CreateSIPDispatchRule",
                headers={
                    "Authorization": f"Bearer {generate_token()}",
                    "Content-Type": "application/json"
                },
                json=dispatch_config,
                timeout=10.0
            )
            print(f"Create dispatch rule response: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Created dispatch rule: {json.dumps(result, indent=2)}")
                return result
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error creating dispatch rule: {e}")

async def main():
    print("=== SIP Inbound Call Diagnostic Tool ===")
    print(f"LiveKit URL: {LIVEKIT_URL}")
    print(f"API Key: {LIVEKIT_API_KEY}")
    
    # First, try to create the dispatch rule
    await create_dispatch_rule()

if __name__ == "__main__":
    asyncio.run(main())
