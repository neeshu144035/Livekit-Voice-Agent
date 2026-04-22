#!/bin/bash
lk sip dispatch delete SDR_CKnL93n4ezd9 --url http://localhost:7880 --api-key devkey --api-secret secret12345678
lk sip dispatch create --name 'saas-dispatch-rule' --individual 'call-' --trunks 'ST_A5GekMmjH7n4' --curl --url http://localhost:7880 --api-key devkey --api-secret secret12345678 > curl_cmd.sh
cat curl_cmd.sh
