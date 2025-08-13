#!/usr/bin/env python3
"""
Business Idea Analyzer with comprehensive debug logging
Logs all messages to understand timeout patterns
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "config" / "prompts"
ANALYSES_DIR = PROJECT_ROOT / "analyses"
LOGS_DIR = PROJECT_ROOT / "logs"


def create_slug(idea: str) -> str:
    """Create a filesystem-safe slug from an idea."""
    slug = re.sub(r'[^\w\s-]', '', idea.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:50].strip('-')


async def load_prompt(prompt_file: str = "analyst_v1.md") -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        return f.read()


async def analyze_idea_with_debug(idea: str, prompt_file: str = "analyst_v1.md") -> Optional[str]:
    """
    Analyze a business idea with comprehensive debug logging.
    
    Args:
        idea: One-liner business idea to analyze
        prompt_file: Which prompt file to use
        
    Returns:
        Generated analysis markdown or None if error
    """
    # Setup debug logging
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = LOGS_DIR / f"debug_{timestamp}.json"
    print(f"📝 Debug logging to: {debug_file}")
    
    debug_log = {
        "idea": idea,
        "prompt_file": prompt_file,
        "timestamp": datetime.now().isoformat(),
        "session_id": None,  # Will be captured from SystemMessage
        "messages": [],
        "timing": [],
        "summary": {}
    }
    
    start_time = time.time()
    
    def log_timing(event: str):
        elapsed = time.time() - start_time
        debug_log["timing"].append({
            "time": elapsed,
            "event": event
        })
        print(f"[{elapsed:.1f}s] {event}")
    
    try:
        # Load the analyst prompt
        log_timing("Loading prompt")
        system_prompt = await load_prompt(prompt_file)
        debug_log["system_prompt_length"] = len(system_prompt)
        
        # Craft user prompt
        user_prompt = f"""Analyze this business idea: "{idea}"

Please generate a comprehensive analysis following the structure and word limits specified in your instructions. Use WebSearch to gather relevant market data, competitor information, and industry trends where helpful."""
        
        debug_log["user_prompt_length"] = len(user_prompt)
        
        # Configure options
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=10,
            allowed_tools=["WebSearch"],
        )
        
        debug_log["options"] = {
            "max_turns": options.max_turns,
            "allowed_tools": options.allowed_tools,
        }
        
        print(f"🎯 Analyzing: {idea}")
        print(f"📄 Using prompt: {prompt_file}")
        log_timing("Starting ClaudeSDKClient")
        
        result_text = []
        message_count = 0
        search_count = 0
        
        # Use ClaudeSDKClient for better control
        async with ClaudeSDKClient(options=options) as client:
            log_timing("Client connected")
            
            # Send the query
            await client.query(user_prompt)
            log_timing("Query sent")
            
            # Set a timeout for receiving messages
            try:
                async with asyncio.timeout(120):  # 2 minute timeout for receiving
                    async for message in client.receive_response():
                        message_count += 1
                        elapsed = time.time() - start_time
                        message_type = type(message).__name__
                        
                        # Create detailed message log
                        msg_log = {
                            "number": message_count,
                            "type": message_type,
                            "timestamp": datetime.now().isoformat(),
                            "elapsed": elapsed
                        }
                        
                        # Extract message details
                        if hasattr(message, '__dict__'):
                            for key, value in message.__dict__.items():
                                if key.startswith('_'):
                                    continue
                                if key == 'content' and hasattr(value, '__iter__'):
                                    content_info = []
                                    for block in value:
                                        block_info = {"type": type(block).__name__}
                                        if hasattr(block, 'name'):
                                            block_info["name"] = block.name
                                            if block.name == "WebSearch":
                                                search_count += 1
                                                if hasattr(block, 'input'):
                                                    query = block.input.get('query', 'unknown')
                                                    block_info["query"] = query
                                                    log_timing(f"WebSearch #{search_count}: {query}")
                                        if hasattr(block, 'text'):
                                            block_info["text_length"] = len(block.text)
                                            block_info["text_preview"] = block.text[:100]
                                            result_text.append(block.text)
                                        content_info.append(block_info)
                                    msg_log["content"] = content_info
                                elif isinstance(value, (str, int, float, bool, type(None))):
                                    msg_log[key] = value
                                elif isinstance(value, (list, dict)):
                                    msg_log[key] = str(value)[:200]
                                else:
                                    msg_log[key] = f"<{type(value).__name__}>"
                        
                        debug_log["messages"].append(msg_log)
                        
                        # Save debug log incrementally
                        with open(debug_file, 'w') as f:
                            json.dump(debug_log, f, indent=2, default=str)
                        
                        # Show progress
                        if message_type == "AssistantMessage":
                            log_timing(f"Message {message_count}: Assistant (search count: {search_count})")
                        elif message_type == "UserMessage":
                            log_timing(f"Message {message_count}: User (tool response)")
                        elif message_type == "SystemMessage":
                            subtype = getattr(message, 'subtype', 'unknown')
                            log_timing(f"Message {message_count}: System ({subtype})")
                            # Capture session ID from init message
                            if subtype == 'init' and hasattr(message, 'data'):
                                data_str = str(getattr(message, 'data', ''))
                                # Parse session_id from the data string
                                import re
                                match = re.search(r"'session_id':\s*'([^']+)'", data_str)
                                if match:
                                    session_id = match.group(1)
                                    debug_log["session_id"] = session_id
                                    print(f"📍 Claude Code Session ID: {session_id}")
                                    print(f"   Session file: ~/.claude/projects/-Users-vincent-Projects-recursive-experiments-idea-assess/{session_id}.jsonl")
                        elif message_type == "ResultMessage":
                            log_timing(f"Message {message_count}: Result - COMPLETE")
                            if hasattr(message, 'result'):
                                return message.result
                            break
                        else:
                            log_timing(f"Message {message_count}: {message_type}")
                        
            except asyncio.TimeoutError:
                log_timing("⚠️ Timeout waiting for response")
                debug_log["error"] = "Timeout after 120 seconds"
        
        # If no ResultMessage, return collected text
        if result_text:
            final_analysis = "".join(result_text)
            log_timing(f"✓ Using collected text ({len(final_analysis)} chars)")
            return final_analysis
        else:
            log_timing("✗ No analysis generated")
            return None
            
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"Error after {elapsed:.1f}s: {type(e).__name__}: {e}"
        print(f"✗ {error_msg}")
        
        debug_log["error"] = {
            "message": str(e),
            "type": type(e).__name__,
            "elapsed": elapsed
        }
        
        import traceback
        debug_log["error"]["traceback"] = traceback.format_exc()
        
        with open(debug_file, 'w') as f:
            json.dump(debug_log, f, indent=2, default=str)
        
        return None
    
    finally:
        # Save final summary
        total_time = time.time() - start_time
        debug_log["summary"] = {
            "total_time": total_time,
            "total_messages": message_count,
            "total_searches": search_count,
            "message_types": {},
            "search_times": []
        }
        
        # Count message types and extract search times
        for msg in debug_log["messages"]:
            msg_type = msg["type"]
            debug_log["summary"]["message_types"][msg_type] = \
                debug_log["summary"]["message_types"].get(msg_type, 0) + 1
            
            # Extract WebSearch timings
            if "content" in msg:
                for block in msg["content"]:
                    if block.get("name") == "WebSearch":
                        debug_log["summary"]["search_times"].append({
                            "query": block.get("query", "unknown"),
                            "elapsed": msg["elapsed"]
                        })
        
        with open(debug_file, 'w') as f:
            json.dump(debug_log, f, indent=2, default=str)
        
        print(f"\n📊 Summary:")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Messages: {message_count}")
        print(f"  WebSearches: {search_count}")
        print(f"  Debug log: {debug_file}")


def save_analysis(idea: str, analysis: str) -> Path:
    """Save analysis to a markdown file."""
    slug = create_slug(idea)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    idea_dir = ANALYSES_DIR / slug
    idea_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = idea_dir / f"analysis_{timestamp}.md"
    
    header = f"""<!-- 
Original Idea: {idea}
Generated: {datetime.now().isoformat()}
Agent: Analyst v1 (Phase 1) - Debug Mode
-->

"""
    
    with open(output_file, 'w') as f:
        f.write(header + analysis)
    
    latest_link = idea_dir / "analysis.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    
    return output_file


async def main():
    """Main entry point for the debug analyzer."""
    parser = argparse.ArgumentParser(
        description="Analyze business ideas with debug logging"
    )
    parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    parser.add_argument(
        "--prompt",
        default="analyst_v1.md",
        help="Prompt file to use (default: analyst_v1.md)"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple prompt (analyst_v1_simple.md)"
    )
    
    args = parser.parse_args()
    
    # Choose prompt file
    prompt_file = "analyst_v1_simple.md" if args.simple else args.prompt
    
    # Run the analysis
    analysis = await analyze_idea_with_debug(args.idea, prompt_file)
    
    if analysis:
        output_path = save_analysis(args.idea, analysis)
        print(f"\n✓ Analysis saved to: {output_path}")
        
        print("\n--- PREVIEW ---")
        lines = analysis.split('\n')[:20]
        for line in lines:
            print(line)
        if len(analysis.split('\n')) > 20:
            print("...")
    else:
        print("\n✗ Analysis failed - check debug log")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())