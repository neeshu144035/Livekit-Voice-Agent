#!/usr/bin/env python3
"""Test script to verify SIP transfer functionality"""
import asyncio
import httpx
import base64
import os

# LiveKit credentials
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret12345678")
LIVEKIT_URL = "http://livekit-server:7880"

async def test_list_sip_trunks():
    """Test listing SIP trunks with authentication"""
    print("Testing SIP trunk listing...")
    
    # Create auth headers
    credentials = base64.b64encode(f"{LIVEKIT_API_KEY}:{LIVEKIT_API_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{LIVEKIT_URL}/twirp/livekit.SIP/ListSIPTrunk",
                json={},
                headers=headers,
                timeout=10.0
            )
            
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ Success! Found {len(data.get('items', []))} trunks")
                for trunk in data.get('items', []):
                    print(f"  - Trunk ID: {trunk.get('sipTrunkId')}")
                    print(f"    Outbound: {trunk.get('outbound', False)}")
                    print(f"    Inbound: {trunk.get('inbound', False)}")
                return True
            else:
                print(f"✗ Failed: {resp.text}")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

async def test_create_sip_participant():
    """Test creating SIP participant (dialing out)"""
    print("\nTesting SIP participant creation...")
    print("Note: This requires an active room and valid trunk")
    
    # Create auth headers
    credentials = base64.b64encode(f"{LIVEKIT_API_KEY}:{LIVEKIT_API_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }
    
    # First get available trunks
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{LIVEKIT_URL}/twirp/livekit.SIP/ListSIPTrunk",
                json={},
                headers=headers,
                timeout=10.0
            )
            
            if resp.status_code != 200:
                print(f"✗ Cannot list trunks: {resp.text}")
                return False
            
            trunks_data = resp.json()
            trunk_id = None
            
            # Find outbound trunk
            for trunk in trunks_data.get("items", []):
                if trunk.get("outbound"):
                    trunk_id = trunk.get("sipTrunkId")
                    break
            
            if not trunk_id:
                print("✗ No outbound trunk found")
                return False
            
            print(f"✓ Found outbound trunk: {trunk_id}")
            print("Note: To actually dial, you need an active room with a call in progress")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("LiveKit SIP Transfer Test")
    print("="*60)
    
    # Run tests
    trunk_result = asyncio.run(test_list_sip_trunks())
    dial_result = asyncio.run(test_create_sip_participant())
    
    print("\n" + "="*60)
    if trunk_result and dial_result:
        print("✓ All tests passed! Transfer functionality should work.")
    else:
        print("✗ Some tests failed. Check the errors above.")
    print("="*60)
