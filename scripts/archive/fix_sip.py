import asyncio
from livekit import api as livekit_api

async def fix_sip():
    lk = livekit_api.LiveKitAPI(url='http://localhost:7880', api_key='devkey', api_secret='secret12345678')
    try:
        rules = await lk.sip.list_dispatch_rule(livekit_api.ListSIPDispatchRuleRequest())
        for item in rules.items:
            print("Deleting dispatch rule:", item.sip_dispatch_rule_id)
            await lk.sip.delete_dispatch_rule(livekit_api.DeleteSIPDispatchRuleRequest(
                sip_dispatch_rule_id=item.sip_dispatch_rule_id
            ))
        
        trunks = await lk.sip.list_inbound_trunk(livekit_api.ListSIPInboundTrunkRequest())
        for item in trunks.items:
            print("Deleting inbound trunk:", item.sip_trunk_id)
            await lk.sip.delete_sip_trunk(livekit_api.DeleteSIPTrunkRequest(
                sip_trunk_id=item.sip_trunk_id
            ))
            
        print("Old SIP config cleared!")
    finally:
        await lk.aclose()

asyncio.run(fix_sip())
