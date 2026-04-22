#!/usr/bin/env python3
import requests
import json
import sys

# Use the same JWT that the CLI uses
# Let's get it from the CLI
import subprocess

result = subprocess.run([
    'lk', 'token', 'create',
    '--create', '--list',
    '--egress', '--ingress',
    '--valid-for', '1h'
], capture_output=True, text=True, env={
    'LIVEKIT_URL': 'http://127.0.0.1:7880',
    'LIVEKIT_API_KEY': 'devkey',
    'LIVEKIT_API_SECRET': 'secret12345678'
})

# Extract token from output
lines = result.stdout.strip().split('\n')
token = None
for line in lines:
    if line.startswith('eyJ'):
        token = line.strip()
        break

if not token:
    print("Failed to get token")
    print(result.stdout)
    print(result.stderr)
    sys.exit(1)

print(f"Got token: {token[:50]}...")

# Now try to update the dispatch rule
url = "http://127.0.0.1:7880/twirp/livekit.SIP/UpdateSIPDispatchRule"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Try with snake_case keys (as the SDK would generate)
data = {
    "sip_dispatch_rule_id": "SDR_yvkcKvc3YSzx",
    "name": "sarah-inbound",
    "trunk_ids": ["ST_MmPcirsWDBPp"],
    "rule": {
        "dispatch_rule_individual": {
            "room_prefix": "call-"
        }
    },
    "room_config": {
        "agents": [
            {"agent_name": "sarah"}
        ]
    }
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
