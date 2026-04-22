import asyncio
from livekit import api as livekit_api

async def check_outbound():
    lk = livekit_api.LiveKitAPI(url='http://localhost:7880', api_key='devkey', api_secret='secret12345678')
    try:
        trunks = await lk.sip.list_outbound_trunk(livekit_api.ListSIPOutboundTrunkRequest())
        print("Outbound trunks:")
        for t in trunks.items:
            print("ID:", t.sip_trunk_id, "Name:", t.name, "IPs:", t.allowed_ips)
    finally:
        await lk.aclose()

asyncio.run(check_outbound())
