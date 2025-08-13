#!/usr/bin/env python3
"""
Test WebSearch tool specifically
"""

import asyncio
from claude_code_sdk import query, ClaudeCodeOptions

async def test_websearch():
    """Test with WebSearch tool enabled."""
    
    prompt = """Search for the current market size of fitness apps for seniors. 
    Give me just one number or fact, then stop."""
    
    options = ClaudeCodeOptions(
        max_turns=3,
        allowed_tools=["WebSearch"],
    )
    
    print("Testing with WebSearch tool...")
    message_count = 0
    
    async for message in query(prompt=prompt, options=options):
        message_count += 1
        message_type = type(message).__name__
        print(f"Message {message_count}: {message_type}")
        
        if message_count > 10:
            print("Too many messages, stopping")
            break
        
        if message_type == "ResultMessage":
            if hasattr(message, 'result'):
                print(f"Result: {message.result[:200]}")
            break
        elif message_type == "AssistantMessage":
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(f"  Text preview: {block.text[:100]}")

if __name__ == "__main__":
    asyncio.run(test_websearch())