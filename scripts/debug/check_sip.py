import inspect
import asyncio
from livekit import api

async def main():
    lk = api.LiveKitAPI(url="http://localhost:7880", api_key="devkey", api_secret="secret")
    print("Methods:", dir(lk.sip))
    if hasattr(lk.sip, "create_sip_participant"):
        print("Signature:", inspect.signature(lk.sip.create_sip_participant))
    else:
        print("create_sip_participant not found!")
    await lk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
