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
    
    trunk_id = "ST_tf7YSZP47YE7"
    to_number = "+916238602144"
    room_name = "test-outbound-direct"
    
    # Step 1: Create room
    print("1. Creating room...")
    try:
        room = await lk.room.create_room(
            livekit_api.CreateRoomRequest(name=room_name, empty_timeout=120, max_participants=3)
        )
        print(f"   Room created: {room.name} ({room.sid})")
    except Exception as e:
        print(f"   ERROR creating room: {e}")
        await lk.aclose()
        return
    
    # Step 2: Create SIP participant
    print(f"2. Creating SIP participant (trunk={trunk_id}, to={to_number})...")
    try:
        result = await lk.sip.create_sip_participant(
            livekit_api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=to_number,
                room_name=room_name,
                participant_identity=f"sip_{to_number}",
                play_ringtone=True,
            )
        )
        print(f"   SIP participant created!")
        print(f"   Participant ID: {result.participant_id}")
        print(f"   Participant Identity: {result.participant_identity}")
        print(f"   SIP Call ID: {result.sip_call_id}")
    except Exception as e:
        print(f"   ERROR creating SIP participant: {type(e).__name__}: {e}")
    
    await lk.aclose()

asyncio.run(main())
