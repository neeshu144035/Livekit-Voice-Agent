try:
    from livekit.protocol import sip_pb2 as sip
except ImportError:
    try:
        from livekit.protocol import sip
    except ImportError:
        print("Cannot import sip")
        exit(1)

from google.protobuf.json_format import MessageToJson

print("--- ATTEMPT 1: Using 'rule' field ---")
try:
    rule_entry = sip.SIPDispatchRule(
        dispatch_rule_individual=sip.SIPDispatchRuleIndividual(room_prefix="call-")
    )
    # Note: trunk_ids is repeated string
    req = sip.CreateSIPDispatchRuleRequest(
        name="saas-dispatch-rule",
        trunk_ids=["ST_A5GekMmjH7n4"],
        rule=rule_entry, 
        metadata='{"called_number": "{{called_number}}"}'
    )
    print(MessageToJson(req))
except Exception as e:
    print(f"Error: {e}")

print("\n--- ATTEMPT 2: Using 'dispatch_rule' field ---")
try:
    rule_entry = sip.SIPDispatchRule(
        dispatch_rule_individual=sip.SIPDispatchRuleIndividual(room_prefix="call-")
    )
    req = sip.CreateSIPDispatchRuleRequest(
        name="saas-dispatch-rule",
        trunk_ids=["ST_A5GekMmjH7n4"],
        dispatch_rule=rule_entry,
        metadata='{"called_number": "{{called_number}}"}'
    )
    print(MessageToJson(req))
except Exception as e:
    print(f"Error: {e}")
