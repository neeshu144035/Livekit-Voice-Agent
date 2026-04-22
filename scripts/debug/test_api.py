#!/usr/bin/env python3
"""
API Test & Latency Measurement Script
Tests all API endpoints and measures latency
"""

import time
import requests
import json
from datetime import datetime

API_URL = "http://13.135.81.172:8000"
LIVEKIT_URL = "wss://oyik.info/livekit"

def print_header(text):
    print("\n" + "=" * 50)
    print(f"  {text}")
    print("=" * 50)

def test_health():
    print_header("Testing Health Endpoint")
    start = time.time()
    resp = requests.get(f"{API_URL}/health")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    print(f"Response: {resp.json()}")
    return resp.status_code == 200, elapsed

def test_create_agent():
    print_header("Testing Create Agent")
    agent_data = {
        "name": f"Test Agent {datetime.now().strftime('%H%M%S')}",
        "description": "Test agent for API validation",
        "system_prompt": "You are a helpful AI assistant.",
        "llm_model": "moonshot-v1-8k",
        "voice_id": "aura-asteria-en",
        "stt_language": "en",
        "welcome_message": "Hello! How can I help you today?"
    }
    start = time.time()
    resp = requests.post(f"{API_URL}/agents", json=agent_data)
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    if resp.status_code == 201:
        agent = resp.json()
        print(f"Created Agent ID: {agent.get('id')}")
        print(f"Agent ID (unique): {agent.get('agent_id')}")
        return True, agent.get('id'), elapsed
    print(f"Error: {resp.text}")
    return False, None, elapsed

def test_list_agents():
    print_header("Testing List Agents")
    start = time.time()
    resp = requests.get(f"{API_URL}/agents")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    print(f"Agents count: {len(resp.json())}")
    return resp.status_code == 200, elapsed

def test_get_token(agent_id):
    print_header("Testing Get Token")
    start = time.time()
    resp = requests.get(f"{API_URL}/token/{agent_id}")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Room Name: {data.get('room_name')}")
        print(f"LiveKit URL: {data.get('livekit_url')}")
        print(f"Token (first 50 chars): {data.get('token', '')[:50]}...")
        return True, elapsed
    print(f"Error: {resp.text}")
    return False, elapsed

def test_list_calls():
    print_header("Testing List Calls")
    start = time.time()
    resp = requests.get(f"{API_URL}/calls")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    print(f"Calls count: {len(resp.json())}")
    return resp.status_code == 200, elapsed

def test_analytics():
    print_header("Testing Analytics")
    start = time.time()
    resp = requests.get(f"{API_URL}/analytics?days=7")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total Calls: {data.get('total_calls')}")
        print(f"Completed: {data.get('completed_calls')}")
        print(f"Success Rate: {data.get('success_rate', 0):.1f}%")
    return resp.status_code == 200, elapsed

def test_phone_numbers():
    print_header("Testing Phone Numbers")
    start = time.time()
    resp = requests.get(f"{API_URL}/phone-numbers")
    elapsed = (time.time() - start) * 1000
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}ms")
    return resp.status_code == 200, elapsed

def main():
    print("\n" + "=" * 50)
    print("  Voice AI Platform - API Test Suite")
    print("=" * 50)
    print(f"\nTesting API at: {API_URL}")
    print(f"Testing LiveKit at: {LIVEKIT_URL}\n")

    results = []

    # Test health
    ok, latency = test_health()
    results.append(("Health Check", ok, latency))

    # Test create agent
    ok, agent_id, latency = test_create_agent()
    results.append(("Create Agent", ok, latency))

    if agent_id:
        # Test get token
        ok, latency = test_get_token(agent_id)
        results.append(("Get Token", ok, latency))

    # Test list agents
    ok, latency = test_list_agents()
    results.append(("List Agents", ok, latency))

    # Test list calls
    ok, latency = test_list_calls()
    results.append(("List Calls", ok, latency))

    # Test analytics
    ok, latency = test_analytics()
    results.append(("Analytics", ok, latency))

    # Test phone numbers
    ok, latency = test_phone_numbers()
    results.append(("Phone Numbers", ok, latency))

    # Summary
    print_header("Test Summary")
    print(f"{'Test':<25} {'Status':<10} {'Latency':<15}")
    print("-" * 50)
    total_latency = 0
    for name, ok, latency in results:
        status = "PASS" if ok else "FAIL"
        print(f"{name:<25} {status:<10} {latency:.2f}ms")
        total_latency += latency

    avg_latency = total_latency / len(results) if results else 0
    print("-" * 50)
    print(f"{'Average Latency':<25} {'':<10} {avg_latency:.2f}ms")
    print(f"\nTotal Tests: {len(results)}")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Passed: {passed}/{len(results)}")

if __name__ == "__main__":
    main()
