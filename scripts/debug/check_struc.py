from livekit import api
from livekit.protocol import sip as sip_proto

print("TRUNK FIELDS:", [f.name for f in sip_proto.SIPOutboundTrunkInfo.DESCRIPTOR.fields])
print("PARTICIPANT FIELDS:", [f.name for f in api.CreateSIPParticipantRequest.DESCRIPTOR.fields])
