#!/bin/bash
cd /home/ubuntu

# Get token - it appears after "Access token: " on the last line
OUTPUT=$(LIVEKIT_URL=http://127.0.0.1:7880 LIVEKIT_API_KEY=devkey LIVEKIT_API_SECRET=secret12345678 lk token create --create --list 2>&1)

# Extract the token from the output
TOKEN=$(echo "$OUTPUT" | awk '/Access token:/ {print $NF}')

echo "Token: ${TOKEN:0:50}..."

# Make API call
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/update.json \
  http://127.0.0.1:7880/twirp/livekit.SIP/UpdateSIPDispatchRule
