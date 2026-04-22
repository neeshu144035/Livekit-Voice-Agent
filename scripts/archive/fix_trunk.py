#!/usr/bin/env python3
import asyncio
from livekit import api
from livekit.protocol import sip as sip_proto

async def main():
    lk = api.LiveKitAPI('http://localhost:7880', 'devkey', 'secret12345678')
    
    trunk_id = "ST_MmPcirsWDBPp"
    
    # Update the inbound trunk to allow all addresses
    print(f"Updating inbound trunk {trunk_id}...")
    try:
        # Delete old trunk and recreate with allowed_addresses
        print("Deleting old trunk...")
        await lk.sip.delete_sip_trunk(api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id))
        print("Old trunk deleted.")
        
        print("Creating new inbound trunk with allowed_addresses...")
        new_trunk = await lk.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=sip_proto.SIPInboundTrunkInfo(
                    name="twilio-inbound",
                    numbers=["+447426999697"],
                    allowed_addresses=["0.0.0.0/0"],
                )
            )
        )
        print(f"New trunk created: {new_trunk.sip_trunk_id}")
        print(f"  Name: {new_trunk.name}")
        print(f"  Numbers: {new_trunk.numbers}")
        print(f"  Allowed Addresses: {new_trunk.allowed_addresses}")
        
        # Update dispatch rule to use new trunk ID
        old_rule_id = "SDR_ZPSwNVzdhQt5"
        print(f"\nDeleting old dispatch rule {old_rule_id}...")
        await lk.sip.delete_sip_dispatch_rule(api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=old_rule_id))
        print("Old dispatch rule deleted.")
        
        print("Creating new dispatch rule...")
        new_rule = await lk.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                name="sarah-agent",
                trunk_ids=[new_trunk.sip_trunk_id],
                rule=sip_proto.SIPDispatchRule(
                    dispatch_rule_individual=sip_proto.SIPDispatchRuleIndividual(
                        room_prefix="call-",
                    )
                ),
            )
        )
        print(f"New dispatch rule created: {new_rule.sip_dispatch_rule_id}")
        print(f"  Name: {new_rule.name}")
        print(f"  Trunk IDs: {new_rule.trunk_ids}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await lk.aclose()
    print("\nDone!")

asyncio.run(main())
