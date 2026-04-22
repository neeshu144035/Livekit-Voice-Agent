#!/usr/bin/env python3
import jwt
import time
import requests
import json

token = jwt.encode({
    'iss': 'devkey',
    'sub': 'admin', 
    'exp': int(time.time()) + 3600,
    'admin': True,
    'sip': True
}, 'secret12345678', algorithm='HS256')

url = 'http://localhost:7880/twirp/livekit.SIP/ListSIPDispatchRule'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
resp = requests.post(url, headers=headers, data='{}')
print('Status:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    for item in data.get('items', []):
        print(f"ID: {item.get('sipDispatchRuleId')}, Name: {item.get('name')}, Trunks: {item.get('trunkIds', [])}")
        rc = item.get('roomConfig', {})
        agents = rc.get('agents', [])
        if agents:
            print(f"  Agents: {agents}")
        else:
            print("  Agents: NONE")
else:
    print(resp.text)
