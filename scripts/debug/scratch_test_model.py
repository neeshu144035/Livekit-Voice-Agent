import urllib.request
import os
import json

api_key = os.environ.get("ELEVEN_API_KEY", "")
req = urllib.request.Request("https://api.elevenlabs.io/v1/models", headers={"xi-api-key": api_key})
data = json.loads(urllib.request.urlopen(req).read().decode())
for m in data:
    print(m["model_id"], "|", m["name"])
