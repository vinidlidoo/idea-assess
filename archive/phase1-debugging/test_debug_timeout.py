#!/usr/bin/env python3
"""
Debug test to understand WebSearch timeout
"""

import asyncio
import time
from claude_code_sdk import query, ClaudeCodeOptions

async def test_timeout():
    """Test with timing information."""
    
    # Test with a simple prompt that requires WebSearch
    prompt = """Search for the current market size of fitness apps. 
    Give me just one fact."""
    
    options = ClaudeCodeOptions(
        max_turns=3,
        allowed_tools=["WebSearch"],
    )
    
    print("Starting test...")
    start_time = time.time()
    message_times = []
    
    try:
        message_count = 0
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            elapsed = time.time() - start_time
            message_type = type(message).__name__
            
            message_times.append((elapsed, message_type))
            print(f"[{elapsed:.1f}s] Message {message_count}: {message_type}")
            
            # Log tool use
            if hasattr(message, 'content'):
                for block in message.content:
                    block_type = type(block).__name__
                    if block_type == "ToolUseBlock":
                        print(f"  -> Tool use: {getattr(block, 'name', 'unknown')}")
            
            if message_type == "ResultMessage":
                print("✓ Got ResultMessage - complete!")
                break
                
            if elapsed > 70:
                print("⚠ Stopping after 70 seconds")
                break
    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"✗ TimeoutError after {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ Error after {elapsed:.1f}s: {e}")
    
    print(f"\nTotal time: {time.time() - start_time:.1f}s")
    print(f"Messages received: {len(message_times)}")
    for t, msg_type in message_times:
        print(f"  {t:.1f}s: {msg_type}")

if __name__ == "__main__":
    asyncio.run(test_timeout())