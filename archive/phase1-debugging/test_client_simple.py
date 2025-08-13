#!/usr/bin/env python3
"""
Test ClaudeSDKClient with simple example
"""

import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def test_client():
    """Test basic client usage."""
    
    print("Testing ClaudeSDKClient...")
    
    options = ClaudeCodeOptions(
        max_turns=1,
        allowed_tools=[]  # No tools for simple test
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            print("Client connected")
            
            # Send query
            await client.query("Write a haiku about Python programming")
            print("Query sent")
            
            # Receive response
            result_text = []
            message_count = 0
            
            async for message in client.receive_response():
                message_count += 1
                message_type = type(message).__name__
                print(f"Message {message_count}: {message_type}")
                
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            result_text.append(block.text)
                            print(f"  Got text: {block.text[:50]}...")
                
                # ResultMessage signals completion
                if message_type == "ResultMessage":
                    print("Got ResultMessage - complete!")
                    if hasattr(message, 'result'):
                        print(f"Result field: {message.result}")
                    break
            
            if result_text:
                final = "".join(result_text)
                print(f"\nFinal output:\n{final}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_client())