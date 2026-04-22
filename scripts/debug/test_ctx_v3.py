import livekit.agents.llm as llm
import sys

ctx = llm.ChatContext()
print("TYPE:", type(ctx.messages))
public_attrs = [m for m in dir(ctx) if not m.startswith("_")]
for a in public_attrs:
    print(f"  CTX.{a}")

# Try add_message
print("\n--- Approach: ctx.add_message ---")
try:
    result = ctx.add_message(role="system", content="test")
    print(f"SUCCESS: add_message works, result={result}")
except Exception as e:
    print(f"FAILED: {e}")

# Check messages() callable
print("\n--- Messages callable ---")
try:
    msgs = ctx.messages()
    print(f"Messages count: {len(msgs)}")
    for m in msgs:
        print(f"  role={m.role}, content={getattr(m, 'content', None)}")
except Exception as e:
    print(f"FAILED: {e}")

# ChatMessage attrs
print("\n--- ChatMessage attrs ---")
for a in sorted(dir(llm.ChatMessage)):
    if not a.startswith("_"):
        print(f"  ChatMessage.{a}")

sys.stdout.flush()
