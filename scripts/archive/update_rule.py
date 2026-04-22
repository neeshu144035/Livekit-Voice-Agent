#!/usr/bin/env python3
import json

data = {
    'sipDispatchRuleId': 'SDR_yvkcKvc3YSzx',
    'update': {
        'trunkIds': {'set': ['ST_MmPcirsWDBPp']},
        'rule': {'dispatchRuleIndividual': {'roomPrefix': 'call-'}},
        'roomConfig': {'agents': [{'agentName': 'sarah'}]}
    }
}

with open('/tmp/update.json', 'w') as f:
    json.dump(data, f)

print('Written to /tmp/update.json')
