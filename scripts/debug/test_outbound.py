import requests
import json

r = requests.post(
    'http://localhost:8000/api/phone-numbers/4/outbound',
    json={'to_number': '+916238602144', 'phone_number_id': 4}
)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))
