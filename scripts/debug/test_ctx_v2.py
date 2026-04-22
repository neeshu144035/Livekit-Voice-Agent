import livekit.agents.llm as llm
try:
    ctx = llm.ChatContext()
    print(f"Has append: {'append' in dir(ctx)}")
    print(f"Has messages: {'messages' in dir(ctx)}")
    print(f"Messages type: {type(ctx.messages)}")
    msg = llm.ChatMessage(role=\"system\", content=\"test\")
    ctx.messages.append(msg)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
