#!/usr/bin/env python3
import asyncio
from livekit import api

async def main():
    lk = api.LiveKitAPI('http://localhost:7880', 'devkey', 'secret12345678')
    
    # List inbound trunks
    print("=== SIP Inbound Trunks ===")
    try:
        trunks = await lk.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())
        if trunks.items:
            for t in trunks.items:
                print(f"ID: {t.sip_trunk_id}")
                print(f"  Name: {t.name}")
                print(f"  Numbers: {t.numbers}")
                print(f"  Allowed Addresses: {t.allowed_addresses}")
                print()
        else:
            print("  NO INBOUND TRUNKS FOUND")
    except Exception as e:
        print(f"  Error: {e}")
    
    # List outbound trunks
    print("=== SIP Outbound Trunks ===")
    try:
        trunks = await lk.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        if trunks.items:
            for t in trunks.items:
                print(f"ID: {t.sip_trunk_id}")
                print(f"  Name: {t.name}")
                print(f"  Address: {t.address}")
                print()
        else:
            print("  NO OUTBOUND TRUNKS FOUND")
    except Exception as e:
        print(f"  Error: {e}")
    
    # List dispatch rules
    print("=== SIP Dispatch Rules ===")
    try:
        rules = await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
        if rules.items:
            for r in rules.items:
                print(f"ID: {r.sip_dispatch_rule_id}")
                print(f"  Name: {r.name}")
                print(f"  Trunk IDs: {r.trunk_ids}")
                print(f"  Rule: {r.rule}")
                print()
        else:
            print("  NO DISPATCH RULES FOUND")
    except Exception as e:
        print(f"  Error: {e}")
    
    await lk.aclose()

asyncio.run(main())
