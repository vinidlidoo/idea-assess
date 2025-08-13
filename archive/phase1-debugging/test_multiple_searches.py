#!/usr/bin/env python3
"""
Test multiple WebSearch calls to understand the timeout pattern
"""

import asyncio
import time
from claude_code_sdk import query, ClaudeCodeOptions

async def test_multiple_searches():
    """Test with multiple WebSearch calls."""
    
    prompt = """Please do the following searches one by one:
    
1. Search for "fitness app market size 2024" and tell me one fact
2. Search for "senior fitness technology trends" and tell me one fact
3. Search for "AI fitness app competitors" and tell me one fact

Do each search separately and report the result before moving to the next."""
    
    options = ClaudeCodeOptions(
        max_turns=10,
        allowed_tools=["WebSearch"],
    )
    
    print("Starting multiple search test...")
    start_time = time.time()
    search_count = 0
    
    try:
        message_count = 0
        
        async with asyncio.timeout(120):  # 2 minute timeout
            async for message in query(prompt=prompt, options=options):
                message_count += 1
                elapsed = time.time() - start_time
                message_type = type(message).__name__
                
                print(f"[{elapsed:.1f}s] Message {message_count}: {message_type}")
                
                # Log tool use
                if hasattr(message, 'content'):
                    for block in message.content:
                        block_type = type(block).__name__
                        if block_type == "ToolUseBlock":
                            if hasattr(block, 'name') and block.name == "WebSearch":
                                search_count += 1
                                search_query = getattr(block, 'input', {}).get('query', 'unknown')
                                print(f"  -> WebSearch #{search_count}: {search_query}")
                        elif block_type == "TextBlock" and hasattr(block, 'text'):
                            # Show first 100 chars of text
                            preview = block.text[:100].replace('\n', ' ')
                            print(f"  -> Text: {preview}...")
                
                if message_type == "ResultMessage":
                    print("✓ Got ResultMessage - complete!")
                    if hasattr(message, 'result'):
                        print(f"  Result length: {len(message.result)} chars")
                    break
    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"✗ Timeout after {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
    
    print(f"\nSummary:")
    print(f"  Total time: {time.time() - start_time:.1f}s")
    print(f"  Messages: {message_count}")
    print(f"  WebSearches: {search_count}")

if __name__ == "__main__":
    asyncio.run(test_multiple_searches())