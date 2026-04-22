try:
    from livekit.protocol import sip_pb2 as sip
except ImportError:
    try:
        from livekit.protocol import sip
    except ImportError:
        exit(1)

from google.protobuf.json_format import MessageToJson

try:
    rule_entry = sip.SIPDispatchRule(
        dispatch_rule_individual=sip.SIPDispatchRuleIndividual(room_prefix="call-")
    )
    req = sip.CreateSIPDispatchRuleRequest(
        name="saas-dispatch-rule",
        trunk_ids=["ST_A5GekMmjH7n4"],
        rule=rule_entry, 
        metadata='{"called_number": "{{called_number}}"}'
    )
    print(MessageToJson(req))
except Exception:
    pass
