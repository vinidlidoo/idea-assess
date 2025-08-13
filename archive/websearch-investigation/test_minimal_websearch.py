#!/usr/bin/env python3
"""
Minimal test to reproduce WebSearch timeout issue
Tests if the problem is with WebSearch itself or our prompt complexity
"""

import asyncio
import time
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def test_multiple_searches():
    """Test multiple WebSearches in sequence."""
    
    # Very simple prompt that just does searches
    prompt = """Please do exactly 3 web searches and report results:
1. Search for "Python programming language"
2. Search for "JavaScript frameworks 2024"  
3. Search for "Machine learning basics"

After each search, just say what you found in one sentence before the next search."""
    
    options = ClaudeCodeOptions(
        max_turns=10,
        allowed_tools=["WebSearch"],
    )
    
    print("Starting minimal WebSearch test...")
    start_time = time.time()
    search_count = 0
    message_count = 0
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            print("Connected to Claude")
            
            # Send query
            await client.query(prompt)
            print("Query sent")
            
            # Track session ID
            session_id = None
            
            # Receive with generous timeout
            async with asyncio.timeout(180):  # 3 minute timeout
                async for message in client.receive_response():
                    message_count += 1
                    elapsed = time.time() - start_time
                    message_type = type(message).__name__
                    
                    print(f"[{elapsed:.1f}s] Message {message_count}: {message_type}")
                    
                    # Capture session ID from SystemMessage
                    if message_type == "SystemMessage" and hasattr(message, 'data'):
                        import re
                        data_str = str(message.data)
                        match = re.search(r"'session_id':\s*'([^']+)'", data_str)
                        if match:
                            session_id = match.group(1)
                            print(f"  Session ID: {session_id}")
                    
                    # Track WebSearch calls
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'name') and block.name == "WebSearch":
                                search_count += 1
                                query = getattr(block, 'input', {}).get('query', 'unknown')
                                print(f"  -> WebSearch #{search_count}: {query}")
                    
                    # Check for completion
                    if message_type == "ResultMessage":
                        print(f"✓ Complete! {search_count} searches performed")
                        break
                    
                    # Safety limit
                    if message_count > 30:
                        print("⚠️ Too many messages, stopping")
                        break
    
    except asyncio.TimeoutError:
        print(f"✗ Timeout after {time.time() - start_time:.1f}s")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    total_time = time.time() - start_time
    print(f"\nResults:")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Messages: {message_count}")
    print(f"  WebSearches: {search_count}")
    if session_id:
        print(f"  Session file: ~/.claude/projects/-Users-vincent-Projects-recursive-experiments-idea-assess/{session_id}.jsonl")

if __name__ == "__main__":
    asyncio.run(test_multiple_searches())