import asyncio
from livekit import api
from livekit.protocol import sip as sip_proto

async def main():
    lk_api = api.LiveKitAPI(url="http://localhost:7880", api_key="devkey", api_secret="secret12345678")
    try:
        req = api.CreateSIPOutboundTrunkRequest(
            trunk=sip_proto.SIPOutboundTrunkInfo(
                name="test_outbound",
                address="example.sip.twilio.com",
                numbers=["+1234567890"],
                auth_username="user",
                auth_password="password"
            )
        )
        print("Trunk Request struct:", dir(req))
        res = await lk_api.sip.create_sip_outbound_trunk(req)
        print("Created trunk:", res)
    finally:
        await lk_api.aclose()

if __name__ == "__main__":
    asyncio.run(main())
