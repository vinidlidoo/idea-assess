#!/usr/bin/env python3
"""
Test with simplified analyst prompt
"""

import asyncio
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

PROJECT_ROOT = Path(__file__).parent.parent

async def test_analyst_simple():
    """Test with simplified analyst prompt."""
    
    # Load simple prompt
    with open(PROJECT_ROOT / "config/prompts/analyst_v1_simple.md") as f:
        system_prompt = f.read()
    
    idea = "AI-powered fitness app for seniors with mobility limitations"
    
    user_prompt = f"""Analyze this business idea: "{idea}"
    
Remember to be concise and complete the analysis in one response."""
    
    options = ClaudeCodeOptions(
        system_prompt=system_prompt,
        max_turns=5,
        allowed_tools=["WebSearch"],
    )
    
    print(f"Testing simplified analyst on: {idea}")
    print("Waiting for analysis...")
    
    result = None
    all_text = []
    message_count = 0
    
    async for message in query(prompt=user_prompt, options=options):
        message_count += 1
        message_type = type(message).__name__
        print(f"  Message {message_count}: {message_type}")
        
        if message_type == "ResultMessage":
            if hasattr(message, 'result'):
                result = message.result
            print("Got ResultMessage!")
            break
        elif message_type == "AssistantMessage":
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        all_text.append(block.text)
        
        if message_count > 20:
            print("Too many messages, stopping")
            break
    
    if result:
        print(f"\n✓ Got result ({len(result)} chars)")
        print("\n--- ANALYSIS ---")
        print(result[:1000])
        if len(result) > 1000:
            print(f"... [{len(result) - 1000} more chars]")
    elif all_text:
        combined = "".join(all_text)
        print(f"\n✓ Got text from messages ({len(combined)} chars)")
        print("\n--- ANALYSIS ---")
        print(combined[:1000])
    else:
        print("\n✗ No result")

if __name__ == "__main__":
    asyncio.run(test_analyst_simple())