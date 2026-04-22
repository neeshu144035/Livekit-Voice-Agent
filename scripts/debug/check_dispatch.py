#!/usr/bin/env python3
import requests
import json
import time
import hmac
import hashlib
import base64

api_key = 'devkey'
api_secret = 'secret12345678'
now = int(time.time())
exp = now + 3600

# Create JWT token
header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip('=')
claims = base64.urlsafe_b64encode(json.dumps({'iss': api_key, 'sub': 'admin', 'exp': exp, 'admin': True, 'sip': True}).encode()).decode().rstrip('=')
signature = base64.urlsafe_b64encode(hmac.new(api_secret.encode(), f'{header}.{claims}'.encode(), hashlib.sha256).digest()).decode().rstrip('=')
token = f'{header}.{claims}.{signature}'

url = 'http://localhost:7880/twirp/livekit.SIP/ListSIPDispatchRule'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

resp = requests.post(url, headers=headers, data='{}')
print('Status:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    for item in data.get('items', []):
        print(f"ID: {item.get('sipDispatchRuleId')}, Name: {item.get('name', 'none')}, Trunks: {item.get('trunkIds', [])}")
        rc = item.get('roomConfig', {})
        agents = rc.get('agents', [])
        if agents:
            print(f"  Agents: {[a.get('agentName') for a in agents]}")
        else:
            print("  Agents: NONE")
else:
    print(resp.text)
