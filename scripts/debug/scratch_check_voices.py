import urllib.request
import json
import os

api_key = os.environ.get("ELEVEN_API_KEY") or os.environ.get("ELEVENLABS_API_KEY", "")
if not api_key:
    print("No ELEVEN_API_KEY found")
    exit(1)

req = urllib.request.Request(
    "https://api.elevenlabs.io/v2/voices?page_size=5",
    headers={"xi-api-key": api_key}
)
r = urllib.request.urlopen(req)
raw = json.loads(r.read().decode())
raw_voices = raw.get("voices", [])
for v in raw_voices[:5]:
    print("Voice:", v.get("name"), "| ID:", v.get("voice_id"))
    print("  high_quality_base_model_ids:", v.get("high_quality_base_model_ids"))
    print("  category:", v.get("category"))
    print()
