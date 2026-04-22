#!/bin/bash
lk sip dispatch delete SDR_mP9KA84EfDjQ --url http://localhost:7880 --api-key devkey --api-secret secret12345678
lk sip dispatch create \
  --name "saas-dispatch-rule" \
  --trunks "ST_A5GekMmjH7n4" \
  --type "individual" \
  --room-prefix "call-" \
  --metadata '{"called_number": "{{called_number}}"}' \
  --url http://localhost:7880 \
  --api-key devkey \
  --api-secret secret12345678
lk sip dispatch list --url http://localhost:7880 --api-key devkey --api-secret secret12345678
