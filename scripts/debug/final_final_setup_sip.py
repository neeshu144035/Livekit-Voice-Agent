import subprocess
import json
import re
import sys

def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode()

print("Cleaning up old rules...")
# Parsing list output to find IDs by Name
out = run_command("lk sip dispatch list --url http://localhost:7880 --api-key devkey --api-secret secret12345678")
for line in out.splitlines():
    if "saas-dispatch-rule" in line or "temp-token-gen" in line or "dummy" in line:
        match = re.search(r"(SDR_[a-zA-Z0-9]+)", line)
        if match:
            lid = match.group(1)
            print(f"Deleting {lid} ({line.strip()})")
            subprocess.run(f"lk sip dispatch delete {lid} --url http://localhost:7880 --api-key devkey --api-secret secret12345678", shell=True)

print("Generating token...")
# Using token create command
token_cmd = "lk token create --api-key devkey --api-secret secret12345678 --grant '{\"sip\":{\"admin\":true}}'"
token = run_command(token_cmd).strip()
if not token or "Bearer" in token: # lk output is just the token string usually
    # If it fails, maybe print error
    pass
# Verify token format
if "." not in token:
    print(f"Invalid token: {token}")
    sys.exit(1)

print("Constructing request...")
url = "http://localhost:7880/twirp/livekit.SIP/CreateSIPDispatchRule"
payload = {
    "dispatchRule": {
        "rule": { 
            "dispatchRuleIndividual": { "roomPrefix": "call-" } 
        },
        "trunkIds": ["ST_A5GekMmjH7n4"],
        "name": "saas-dispatch-rule",
        "metadata": "{\"called_number\": \"{{called_number}}\"}"
    }
}

print("Executing CreateSIPDispatchRule...")
curl_cmd = [
    "curl", "-s", "-X", "POST",
    "-H", f"Authorization: Bearer {token}",
    "-H", "Content-Type: application/json",
    "-d", json.dumps(payload),
    url
]
try:
    subprocess.run(curl_cmd, check=True)
    print("\nSuccess!")
except Exception as e:
    print(f"Curl failed: {e}")
