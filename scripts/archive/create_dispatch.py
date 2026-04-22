import jwt
import requests

# Generate JWT token
token = jwt.encode({'iss': 'devkey'}, 'secret12345678', algorithm='HS256')
print(f"Token: {token}")

# Create dispatch rule via HTTP API
url = "http://localhost:7880/twirp/livekit.SIP/CreateSIPDispatchRule"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# The dispatch rule with agent configuration
data = {
    "dispatchRule": {
        "rule": {
            "dispatchRuleIndividual": {
                "roomPrefix": "call"
            }
        },
        "name": "agent-dispatch",
        "roomConfig": {
            "agents": [
                {"agentName": "sarah"}
            ]
        },
        "mediaEncryption": "SIP_MEDIA_ENCRYPT_DISABLE"
    }
}

response = requests.post(url, headers=headers, json=data)
print(f"Response: {response.status_code}")
print(f"Body: {response.text}")
