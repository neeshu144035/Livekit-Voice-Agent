import asyncio
from livekit import api

async def main():
    # Inside Docker, we use the service name
    lk = api.LiveKitAPI(
        url='http://livekit-server:7880',
        api_key='devkey',
        api_secret='secret12345678'
    )
    try:
        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
        print(f"Total Rooms: {len(rooms.rooms)}")
        for r in rooms.rooms:
            print(f"Room: {r.name}")
    finally:
        await lk.aclose()

if __name__ == "__main__":
    asyncio.run(main())
