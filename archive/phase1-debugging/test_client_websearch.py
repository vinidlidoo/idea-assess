#!/usr/bin/env python3
"""
Test ClaudeSDKClient with WebSearch
"""

import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def test_websearch():
    """Test client with WebSearch tool."""
    
    print("Testing ClaudeSDKClient with WebSearch...")
    
    options = ClaudeCodeOptions(
        max_turns=3,
        allowed_tools=["WebSearch"]
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            print("Client connected")
            
            # Send query that requires search
            await client.query("What is the current market size for fitness apps? Give me just one recent statistic.")
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
                            preview = block.text[:80].replace('\n', ' ')
                            print(f"  Text: {preview}...")
                        elif hasattr(block, 'type'):
                            print(f"  Block type: {block.type}")
                
                # Stop after too many messages
                if message_count > 20:
                    print("Too many messages, stopping")
                    break
                
                # ResultMessage signals completion
                if message_type == "ResultMessage":
                    print("Got ResultMessage - complete!")
                    if hasattr(message, 'result'):
                        print(f"Result: {message.result[:200]}...")
                    break
            
            if result_text:
                final = "".join(result_text)
                print(f"\nFinal output ({len(final)} chars):")
                print(final[:500])
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websearch())