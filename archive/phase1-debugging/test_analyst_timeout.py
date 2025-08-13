#!/usr/bin/env python3
"""
Debug test to understand WebSearch timeout with analyst prompt
"""

import asyncio
import time
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

PROJECT_ROOT = Path(__file__).parent.parent

async def test_analyst_timeout():
    """Test analyst prompt with timing information."""
    
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
    
    print(f"Testing analyst on: {idea}")
    print("Starting test...")
    start_time = time.time()
    message_times = []
    
    try:
        message_count = 0
        tool_count = 0
        
        # Add timeout wrapper
        async with asyncio.timeout(75):  # 75 second timeout
            async for message in query(prompt=user_prompt, options=options):
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
                            tool_count += 1
                            tool_name = getattr(block, 'name', 'unknown')
                            print(f"  -> Tool use #{tool_count}: {tool_name}")
                
                if message_type == "ResultMessage":
                    print("✓ Got ResultMessage - complete!")
                    break
    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"✗ asyncio.TimeoutError after {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
    
    print(f"\nSummary:")
    print(f"  Total time: {time.time() - start_time:.1f}s")
    print(f"  Messages received: {len(message_times)}")
    print(f"  Tool uses: {tool_count}")
    print(f"\nMessage timeline:")
    for t, msg_type in message_times:
        print(f"  {t:.1f}s: {msg_type}")

if __name__ == "__main__":
    asyncio.run(test_analyst_timeout())