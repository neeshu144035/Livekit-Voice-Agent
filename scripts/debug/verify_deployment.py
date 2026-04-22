"""Verification script for the deployment of inbound call fixes and call history features."""
import requests
import json
import sys

API = "http://localhost:8000"
PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS: {name}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {name} — {detail}")

print("=" * 60)
print("DEPLOYMENT VERIFICATION")
print("=" * 60)

# --- Test 1: Call History endpoint ---
print("\n📋 Test 1: /api/call-history endpoint")
try:
    r = requests.get(f"{API}/api/call-history", params={"limit": 3}, timeout=5)
    data = r.json()
    test("Returns 200", r.status_code == 200, f"Got {r.status_code}")
    test("Has 'calls' key", "calls" in data)
    test("Has 'total' key", "total" in data)
    test("Has 'total_pages' key", "total_pages" in data)
    test("Total > 0", data.get("total", 0) > 0, f"total={data.get('total')}")
    if data.get("calls"):
        c = data["calls"][0]
        test("Call has call_id", "call_id" in c)
        test("Call has agent_name", "agent_name" in c)
        test("Call has direction", "direction" in c)
        test("Call has status", "status" in c)
        test("Call has cost_usd", "cost_usd" in c)
        test("Call has llm_cost", "llm_cost" in c)
        test("Call has stt_cost", "stt_cost" in c)
        test("Call has tts_cost", "tts_cost" in c)
        test("Call has llm_tokens_in", "llm_tokens_in" in c)
        test("Call has llm_tokens_out", "llm_tokens_out" in c)
        test("Call has stt_duration_ms", "stt_duration_ms" in c)
        test("Call has tts_characters", "tts_characters" in c)
        test("Call has transcript_count", "transcript_count" in c)
        print(f"    → Sample call: id={c['call_id'][:20]}, agent={c.get('agent_name')}, dir={c.get('direction')}, cost=${c.get('cost_usd', 0):.4f}")
except Exception as e:
    test("Endpoint reachable", False, str(e))

# --- Test 2: Call History with filters ---
print("\n🔍 Test 2: /api/call-history with filters")
try:
    r = requests.get(f"{API}/api/call-history", params={"direction": "outbound", "limit": 2}, timeout=5)
    data = r.json()
    test("Outbound filter works", r.status_code == 200)
    if data.get("calls"):
        test("All are outbound", all(c.get("direction") == "outbound" for c in data["calls"]))
except Exception as e:
    test("Filter works", False, str(e))

# --- Test 3: Call Detail endpoint ---
print("\n📖 Test 3: /api/call-history/{call_id}/details")
try:
    # Get a call_id to test with
    r = requests.get(f"{API}/api/call-history", params={"limit": 1}, timeout=5)
    calls = r.json().get("calls", [])
    if calls:
        cid = calls[0]["call_id"]
        r = requests.get(f"{API}/api/call-history/{cid}/details", timeout=5)
        det = r.json()
        test("Returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Has 'call' key", "call" in det)
        test("Has 'costs' key", "costs" in det)
        test("Has 'usage' key", "usage" in det)
        test("Has 'latency' key", "latency" in det)
        test("Has 'transcript' key", "transcript" in det)
        if "costs" in det:
            costs = det["costs"]
            test("Costs has total_usd", "total_usd" in costs)
            test("Costs has llm_cost", "llm_cost" in costs)
            test("Costs has stt_cost", "stt_cost" in costs)
            test("Costs has tts_cost", "tts_cost" in costs)
        if "usage" in det:
            usage = det["usage"]
            test("Usage has llm_tokens_in", "llm_tokens_in" in usage)
            test("Usage has stt_duration_formatted", "stt_duration_formatted" in usage)
        print(f"    → Detail: agent={det['call']['agent_name']}, cost=${det['costs']['total_usd']:.4f}, transcripts={len(det.get('transcript', []))}")
    else:
        test("Has calls to test", False, "No calls found")
except Exception as e:
    test("Detail endpoint", False, str(e))

# --- Test 4: LiveKit Webhook endpoint ---
print("\n🔔 Test 4: /api/livekit-webhook")
try:
    r = requests.post(f"{API}/api/livekit-webhook", json={}, timeout=5)
    test("Returns 200", r.status_code == 200)
    test("Returns ok", r.json().get("status") == "ok")
except Exception as e:
    test("Webhook endpoint", False, str(e))

# --- Test 5: Agent by Phone endpoint ---
print("\n📱 Test 5: /api/agents/by-phone")
try:
    r = requests.get(f"{API}/api/agents/by-phone/+0000000000", timeout=5)
    # 404 is expected for a non-existent number
    test("Returns 404 for unknown number", r.status_code == 404)
except Exception as e:
    test("By-phone endpoint", False, str(e))

# --- Test 6: Call Usage Update endpoint ---
print("\n📊 Test 6: /api/calls/{{call_id}}/usage")
try:
    r = requests.post(f"{API}/api/calls/nonexistent_call/usage", json={
        "llm_tokens_in": 100,
        "llm_tokens_out": 50,
    }, timeout=5)
    test("Returns 404 for unknown call", r.status_code == 404)
except Exception as e:
    test("Usage endpoint", False, str(e))

# --- Test 7: Create Call from Agent endpoint ---
print("\n📞 Test 7: /api/calls/create-from-agent")
try:
    r = requests.post(f"{API}/api/calls/create-from-agent", json={
        "room_name": "test_verification_room",
        "agent_id": 5,
        "direction": "outbound",
        "call_type": "web",
    }, timeout=5)
    test("Returns 200", r.status_code == 200)
    data = r.json()
    test("Returns call_id", "call_id" in data)
    if "call_id" in data:
        print(f"    → Created test call: {data['call_id']}")
        # Now test usage update on this call
        r2 = requests.post(f"{API}/api/calls/{data['call_id']}/usage", json={
            "llm_tokens_in": 500,
            "llm_tokens_out": 200,
            "llm_model_used": "gpt-4o-mini",
            "stt_duration_ms": 15000,
            "tts_characters": 300,
            "transcript_summary": "Test conversation summary",
        }, timeout=5)
        test("Usage update works", r2.status_code == 200)
        if r2.status_code == 200:
            cost = r2.json().get("total_cost", 0)
            print(f"    → Cost calculated: ${cost:.6f}")
            test("Cost > 0", cost > 0, f"cost={cost}")
except Exception as e:
    test("Create call endpoint", False, str(e))

# --- Test 8: Database schema ---
print("\n🗄️ Test 8: Database columns exist")
try:
    r = requests.get(f"{API}/api/call-history", params={"limit": 1}, timeout=5)
    calls = r.json().get("calls", [])
    if calls:
        c = calls[0]
        required_fields = ["llm_cost", "stt_cost", "tts_cost", "llm_tokens_in", "llm_tokens_out", "stt_duration_ms", "tts_characters"]
        for f in required_fields:
            test(f"Field '{f}' present", f in c, f"Missing from response")
    else:
        test("Has data", False)
except Exception as e:
    test("Schema check", False, str(e))

# --- Summary ---
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("🎉 ALL TESTS PASSED!")
else:
    print("⚠️  Some tests failed. Review above.")
print("=" * 60)
sys.exit(1 if FAIL > 0 else 0)
