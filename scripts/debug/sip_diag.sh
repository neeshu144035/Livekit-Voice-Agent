#!/bin/bash
echo "=== SIP CONTAINER STATUS ==="
sudo docker ps | grep sip

echo ""
echo "=== RECENT SIP INVITE LOGS ==="
sudo docker logs livekit-sip 2>&1 | grep -i "INVITE" | tail -5

echo ""
echo "=== RECENT SIP ERRORS ==="
sudo docker logs livekit-sip 2>&1 | grep -iE '"E"|error|fail|reject|"W"' | tail -10

echo ""
echo "=== SIP DISPATCH RULES ==="
sudo docker logs livekit-sip 2>&1 | grep -i "dispatch" | tail -5

echo ""
echo "=== VOICE AGENT STATUS ==="
sudo docker logs voice-agent 2>&1 | grep -i "registered\|error\|room" | tail -10

echo ""
echo "=== LAST INBOUND CALL ATTEMPT ==="
sudo docker logs livekit-sip 2>&1 | grep -i "incoming\|inbound\|from.*to\|caller" | tail -10

echo ""
echo "=== SIP CONFIG ==="
sudo docker exec livekit-sip cat /sip/config.yaml 2>&1 || echo "No config found"

echo ""
echo "=== LISTENING PORTS ==="
sudo ss -tlnp | grep -E '5060|7880|8000|3000'
