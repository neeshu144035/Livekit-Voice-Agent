import asyncio
import os
from dotenv import load_dotenv
import logging
from livekit.plugins import openai
from livekit.agents import llm

load_dotenv()
from agent import PropertyAgent, fetch_agent_functions

logging.basicConfig(level=logging.INFO)

async def run_test():
    print("Starting CLI test for agent tool calling...")
    
    # 1. Fetch functions configured for the agent
    functions_config = await fetch_agent_functions(1)
    print(f"Functions from API: {functions_config}")

    # 2. Setup the agent function context
    agent = PropertyAgent("You are a helpful assistant capable of property searches.", functions_config)

    # 3. Call the Property Search manually to ensure it handles the webhook correctly
    print("\n[Test 1] Executing Tool Directly:")
    result = await agent.property_search(
        ctx=None,
        postcode="LE1",
        property_type="flat",
        budget="900" 
    )
    print(f"Tool webhook response: {result}\n")
    print("If you successfully see the output above, the tool logic and backend logic works perfectly!")

if __name__ == "__main__":
    asyncio.run(run_test())
