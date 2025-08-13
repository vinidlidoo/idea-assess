#!/usr/bin/env python3
"""
Test without system prompt
"""

import asyncio
from claude_code_sdk import query, ClaudeCodeOptions

async def test_no_system():
    """Test without system prompt."""
    
    prompt = """Write a 200-word business analysis of this idea: "AI-powered fitness app for seniors"
    
Include market size (search for it), main competitors, and next steps."""
    
    options = ClaudeCodeOptions(
        max_turns=5,
        allowed_tools=["WebSearch"],
    )
    
    print("Testing without system prompt...")
    message_count = 0
    
    async for message in query(prompt=prompt, options=options):
        message_count += 1
        message_type = type(message).__name__
        print(f"Message {message_count}: {message_type}")
        
        if message_type == "ResultMessage":
            if hasattr(message, 'result'):
                print(f"\nResult ({len(message.result)} chars):")
                print(message.result[:500])
            break
        
        if message_count > 15:
            print("Stopping after 15 messages")
            break

if __name__ == "__main__":
    asyncio.run(test_no_system())