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
# List and find 'saas-dispatch-rule' or 'dummy'
out = run_command("lk sip dispatch list --url http://localhost:7880 --api-key devkey --api-secret secret12345678")
for line in out.splitlines():
    if "saas-dispatch-rule" in line or "dummy" in line:
        match = re.search(r"(SDR_[a-zA-Z0-9]+)", line)
        if match:
            lid = match.group(1)
            print(f"Deleting {lid}")
            subprocess.run(f"lk sip dispatch delete {lid} --url http://localhost:7880 --api-key devkey --api-secret secret12345678", shell=True)

print("Generating token...")
# Generate curl command to steal token. 
# We use a dummy name to avoid conflict IF we failed to delete? No, we deleted.
cmd = "lk sip dispatch create --name 'temp-token-gen' --individual 'call-' --trunks 'ST_A5GekMmjH7n4' --curl --url http://localhost:7880 --api-key devkey --api-secret secret12345678"
curl_out = run_command(cmd)

match = re.search(r"Bearer ([a-zA-Z0-9\-\._]+)", curl_out)
if not match:
    print("Failed to extract token")
    sys.exit(1)
token = match.group(1)

print("Constructing request...")
url = "http://localhost:7880/twirp/livekit.SIP/CreateSIPDispatchRule"
# Correct JSON structure with metadata
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

import subprocess
print("Executing CreateSIPDispatchRule...")
# Use curl via subprocess
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
