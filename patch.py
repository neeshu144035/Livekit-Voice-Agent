import re
with open("agent_retell.py", "r") as f:
    code = f.read()

# We need to replace `def create_dynamic_agent_class(...)` up to `def detect_sip_participant(room):`
match = re.search(r"def create_dynamic_agent_class\(functions_config, base_instructions, current_room=None, call_id=None\):.*?# ==================== SIP Detection ====================", code, flags=re.DOTALL)
if not match:
    print("Match not found")
else:
    with open("new_create_dynamic_agent_class.py", "r") as f2:
        new_fn = f2.read()

    new_code = code[:match.start()] + new_fn + "\n\n# ==================== SIP Detection ====================\n" + code[match.end():]

    with open("agent_retell.py", "w") as f:
        f.write(new_code)
    print("Patched!")
