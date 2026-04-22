import asyncio
from livekit import api

async def main():
    lk = api.LiveKitAPI(
        url='http://livekit-server:7880',
        api_key='devkey',
        api_secret='secret12345678'
    )
    try:
        trunks = await lk.sip.list_sip_trunk(api.ListSIPTrunkRequest())
        print(f"Total Trunks: {len(trunks.items)}")
        for t in trunks.items:
            print(f"Trunk ID: {t.sip_trunk_id}")
            print(f"Name: {t.name}")
            if hasattr(t, 'outbound'):
                print(f"Outbound Address: {t.outbound.address}")
            if hasattr(t, 'inbound'):
                print(f"Inbound Numbers: {list(t.inbound.numbers)}")
            print("-" * 20)
    finally:
        await lk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
