#!/usr/bin/env python3
import asyncio
from livekit import api

async def main():
    lk = api.LiveKitAPI('http://localhost:7880', 'devkey', 'secret12345678')
    rules = await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
    for r in rules.items:
        print(f'ID: {r.sip_dispatch_rule_id}, Name: {r.name}, Trunks: {r.trunk_ids}')
        if r.room_config and r.room_config.agents:
            print(f'  Agents: {[a.agent_name for a in r.room_config.agents]}')
        else:
            print('  Agents: NONE')
    await lk.aclose()

asyncio.run(main())
