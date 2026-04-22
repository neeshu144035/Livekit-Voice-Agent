import jwt
import time
import requests
import json

# Generate admin token for SIP API
token = jwt.encode({
    'iss': 'devkey',
    'sub': 'admin',
    'exp': int(time.time()) + 3600,
    'admin': True,
    'sip': True  # Enable SIP admin
}, 'secret12345678', algorithm='HS256')

# Update the dispatch rule with agent
url = "http://127.0.0.1:7880/twirp/livekit.SIP/UpdateSIPDispatchRule"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

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
