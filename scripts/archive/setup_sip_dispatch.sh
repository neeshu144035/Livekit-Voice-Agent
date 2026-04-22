#!/bin/bash
# SIP Dispatch Setup Script
# Run this on your VPS to set up inbound call routing

echo "=== SIP Inbound Call Setup ==="

# Check if LiveKit CLI is installed
if ! command -v lk &> /dev/null; then
    echo "Installing LiveKit CLI..."
    curl -sSfL https://get.livekit.io/lk | sh
fi

# Configure CLI with your credentials
lk server config --api-key devkey --api-secret secret12345678 --url http://localhost:7880

# Create dispatch rule for agent "sarah"
# This tells LiveKit to dispatch agent "sarah" to rooms that match the pattern "call-*"

echo "Creating SIP dispatch rule..."
lk sip dispatch create <<'EOF'
{
  "name": "sarah-inbound",
  "dispatchRule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  },
  "roomConfig": {
    "agents": [
      {
        "agentName": "sarah"
      }
    ]
  }
}
EOF

echo ""
echo "=== Checking existing dispatch rules ==="
lk sip dispatch list

echo ""
echo "=== To associate with your phone number ==="
echo "1. Get your trunk ID from: lk sip trunk list"
echo "2. Update the dispatch rule with trunk ID:"
echo "   lk sip dispatch update --id <dispatch-rule-id> --trunk-id <trunk-id>"
