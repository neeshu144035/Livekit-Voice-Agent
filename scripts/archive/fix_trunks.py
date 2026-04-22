import asyncio
import warnings
warnings.filterwarnings("ignore")
from livekit import api as livekit_api

async def main():
    lk = livekit_api.LiveKitAPI(
        url="http://localhost:7880",
        api_key="devkey",
        api_secret="secret12345678"
    )
    
    # List all outbound trunks
    trunks = await lk.sip.list_sip_outbound_trunk(livekit_api.ListSIPOutboundTrunkRequest())
    print(f"Found {len(trunks.items)} outbound trunks")
    
    # Delete all old outbound trunks
    for t in trunks.items:
        print(f"Deleting trunk {t.sip_trunk_id} ({t.name} -> {t.address})")
        await lk.sip.delete_sip_trunk(livekit_api.DeleteSIPTrunkRequest(sip_trunk_id=t.sip_trunk_id))
        print(f"  Deleted!")
    
    # Create new clean outbound trunk for +442038287227
    # Using IP ACL - no username/password needed
    from livekit.protocol import sip as sip_proto
    req = livekit_api.CreateSIPOutboundTrunkRequest(
        trunk=sip_proto.SIPOutboundTrunkInfo(
            name="LiveKit-Outbound-442038",
            address="livekit-outbound-442038.pstn.twilio.com",
            numbers=["+442038287227"],
            auth_username="",
            auth_password=""
        )
    )
    res = await lk.sip.create_sip_outbound_trunk(req)
    print(f"\nCreated new trunk: {res.sip_trunk_id}")
    print(f"  Address: livekit-outbound-442038.pstn.twilio.com")
    print(f"  Numbers: ['+442038287227']")
    print(f"  Auth: IP ACL (no credentials)")
    
    await lk.aclose()

asyncio.run(main())
