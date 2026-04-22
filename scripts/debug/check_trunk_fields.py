from livekit import api
from livekit.protocol import sip as sip_proto
print([f.name for f in sip_proto.SIPOutboundTrunkInfo.DESCRIPTOR.fields])
print([f.name for f in api.CreateSIPParticipantRequest.DESCRIPTOR.fields])
