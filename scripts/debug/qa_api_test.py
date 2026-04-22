import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_agent_crud():
    print("\n--- Testing Agent CRUD ---")
    # Create
    payload = {
        "name": "QA Test Agent",
        "system_prompt": "You are a test engineer assistant. Analyze data correctly.",
        "llm_model": "moonshot-v1-8k",
        "voice": "jessica",
        "language": "en-GB"
    }
    resp = requests.post(f"{BASE_URL}/agents/", json=payload)
    if resp.status_code == 200:
        agent = resp.json()
        agent_id = agent["id"]
        print(f"✅ Created Agent ID: {agent_id}")
    else:
        print(f"❌ Failed to create agent: {resp.status_code}")
        return

    # List
    resp = requests.get(f"{BASE_URL}/agents/")
    if resp.status_code == 200:
        agents = resp.json()
        print(f"✅ Listed {len(agents)} agents")
    else:
        print(f"❌ Failed to list agents")

    # Get Token
    resp = requests.get(f"{BASE_URL}/token/{agent_id}")
    if resp.status_code == 200:
        token_data = resp.json()
        print(f"✅ Token generated successfully")
    else:
        print(f"❌ Failed to generate token: {resp.text}")

def test_call_logging():
    print("\n--- Testing Call Logging ---")
    room_name = "agent-test-qa-1"
    payload = {
        "transcript": "User: Hello\nAgent: Hi there!",
        "latency_stats": {"stt_ms": 120, "llm_ms": 250},
        "ended": False
    }
    resp = requests.post(f"{BASE_URL}/calls/{room_name}/log", json=payload)
    if resp.status_code == 200:
        print(f"✅ Log entry created for {room_name}")
    else:
        print(f"❌ Failed to log call: {resp.text}")

    # Verify history
    resp = requests.get(f"{BASE_URL}/calls/1/history")
    if resp.status_code == 200:
        history = resp.json()
        print(f"✅ Retrieved history: {len(history)} entries")
    else:
        print(f"❌ Failed to retrieve history")

if __name__ == "__main__":
    try:
        test_agent_crud()
        test_call_logging()
        print("\n🎉 Backend API test suite completed successfully.")
    except Exception as e:
        print(f"❌ Test suite encountered errors: {e}")
