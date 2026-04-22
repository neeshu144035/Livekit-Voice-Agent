#!/usr/bin/env python3
import requests
import time
import json

# Generate JWT manually with admin and sip grants
import jwt

payload = {
    'iss': 'devkey',
    'sub': 'admin',
    'exp': int(time.time()) + 3600,
    'admin': True,
    'video': {
        'roomCreate': True,
        'roomList': True,
        'roomAdmin': True,
        'roomJoin': True,
        'canPublish': True,
        'canSubscribe': True
    }
}
token = jwt.encode(payload, 'secret12345678', algorithm='HS256')
print(f"Token generated")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# List trunks first
url_list = "http://localhost:7880/twirp/livekit.SIP/ListSIPInboundTrunk"
resp = requests.post(url_list, headers=headers, json={})
print(f"List trunks response: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text}")
    exit(1)
    
data = resp.json()
print(f"Trunks: {data}")
trunk_id = None
for item in data.get('items', []):
    if '+447426999697' in item.get('numbers', []):
        trunk_id = item['sipTrunkId']
        print(f"Found trunk: {trunk_id}")
        break

if not trunk_id:
    print("No trunk found!")
    exit(1)

# Delete existing dispatch rules for this trunk
url_list_rules = "http://localhost:7880/twirp/livekit.SIP/ListSIPDispatchRule"
resp_rules = requests.post(url_list_rules, headers=headers, json={})
if resp_rules.status_code == 200:
    rules_data = resp_rules.json()
    for rule in rules_data.get('items', []):
        if trunk_id in rule.get('trunkIds', []):
            print(f"Deleting existing dispatch rule: {rule['sipDispatchRuleId']}")
            url_delete = "http://localhost:7880/twirp/livekit.SIP/DeleteSIPDispatchRule"
            requests.post(url_delete, headers=headers, json={
                "sipDispatchRuleId": rule['sipDispatchRuleId']
            })

# Create dispatch rule with agent - using the proper structure
dispatch_data = {
    "name": "sarah-inbound-with-agent",
    "trunkIds": [trunk_id],
    "rule": {
        "dispatchRuleIndividual": {
            "roomPrefix": "call"
        }
    },
    "roomConfig": {
        "agents": [
            {"agentName": "sarah"}
        ]
    }
}

print(f"Creating dispatch rule with data: {json.dumps(dispatch_data, indent=2)}")

url = "http://localhost:7880/twirp/livekit.SIP/CreateSIPDispatchRule"
dispatch_resp = requests.post(url, headers=headers, json=dispatch_data)
print(f"Create dispatch response: {dispatch_resp.status_code} - {dispatch_resp.text}")

if dispatch_resp.status_code == 200:
    print("SUCCESS! Dispatch rule created with agent!")
    
    # List dispatch rules to verify
    resp_verify = requests.post(url_list_rules, headers=headers, json={})
    if resp_verify.status_code == 200:
        verify_data = resp_verify.json()
        print("\nCurrent dispatch rules:")
        for rule in verify_data.get('items', []):
            agents = []
            if rule.get('roomConfig', {}).get('agents'):
                agents = [a.get('agentName', '') for a in rule['roomConfig']['agents']]
            print(f"  - {rule.get('name')}: {rule.get('sipDispatchRuleId')}")
            print(f"    Trunks: {rule.get('trunkIds')}")
            print(f"    Agents: {agents}")
