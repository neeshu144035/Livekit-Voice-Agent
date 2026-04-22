import asyncio
from livekit import api as livekit_api

async def check_sip():
    lk_api = livekit_api.LiveKitAPI(
        url='http://localhost:7880',
        api_key='devkey',
        api_secret='secret12345678'
    )
    try:
        trunks = await lk_api.sip.list_inbound_trunk(
            livekit_api.ListSIPInboundTrunkRequest()
        )
        print("Inbound trunks:")
        print(trunks)
    finally:
        await lk_api.aclose()

asyncio.run(check_sip())
