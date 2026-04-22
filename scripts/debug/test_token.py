from livekit import api

# Test creating VideoGrants
grants = api.VideoGrants(
    room_join=True,
    can_publish=True,
    can_subscribe=True,
    room="test-room"
)
print("VideoGrants created:", grants)

# Test creating AccessToken
token = api.AccessToken(
    api_key="devkey",
    api_secret="secret12345678"
)
print("AccessToken created")

# Test with_grants
token = token.with_grants(grants)
print("Token with grants:", token)

# Test to_jwt
jwt = token.to_jwt()
print("JWT token:", jwt[:50] + "...")
