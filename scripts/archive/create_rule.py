#!/usr/bin/env python3
import json

# Try different JSON format for creating dispatch rule with agents
data = {
    'name': 'sarah-inbound-new',
    'trunkIds': ['ST_MmPcirsWDBPp'],
    'dispatchRule': {
        'dispatchRuleIndividual': {
            'roomPrefix': 'call-'
        }
    },
    'roomConfig': {
        'agents': [
            {'agentName': 'sarah'}
        ]
    }
}

with open('/tmp/create_rule.json', 'w') as f:
    json.dump(data, f)

print('Written to /tmp/create_rule.json')
print(json.dumps(data, indent=2))
