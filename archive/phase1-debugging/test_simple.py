#!/usr/bin/env python3
"""
Simple test without WebSearch to isolate the timeout issue
"""

import asyncio
from claude_code_sdk import query, ClaudeCodeOptions

async def test_simple():
    """Test without any tools to see if we get a proper response."""
    
    prompt = """Write a haiku about coding."""
    
    options = ClaudeCodeOptions(
        max_turns=1,
        allowed_tools=[],  # No tools
    )
    
    print("Testing simple query without tools...")
    
    async for message in query(prompt=prompt, options=options):
        message_type = type(message).__name__
        print(f"Got message: {message_type}")
        
        if message_type == "ResultMessage":
            if hasattr(message, 'result'):
                print(f"Result: {message.result}")
            break
        elif message_type == "AssistantMessage":
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(f"Text: {block.text}")

if __name__ == "__main__":
    asyncio.run(test_simple())