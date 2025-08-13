#!/usr/bin/env python3
"""
Business Idea Analyzer - Analyzes business ideas using Claude SDK
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


async def analyze_idea(idea: str, debug: bool = False) -> Optional[str]:
    """
    Analyze a business idea using ClaudeSDKClient with proper WebSearch handling.
    
    Args:
        idea: One-liner business idea to analyze
        debug: If True, log all messages to logs/ directory
        
    Returns:
        Generated analysis markdown or None if error
    """
    # Setup debug logging if requested
    debug_log = None
    debug_file = None
    start_time = time.time() if debug else None
    
    if debug:
        LOGS_DIR = PROJECT_ROOT / "logs"
        LOGS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = LOGS_DIR / f"debug_{timestamp}.json"
        print(f"📝 Debug logging enabled: {debug_file}")
        
        debug_log = {
            "idea": idea,
            "timestamp": datetime.now().isoformat(),
            "session_id": None,
            "messages": [],
            "timing": []
        }
    
    def log_event(event: str, data: dict = None):
        """Log an event if debug mode is enabled."""
        if debug:
            elapsed = time.time() - start_time
            debug_log["timing"].append({
                "time": elapsed,
                "event": event
            })
            if data:
                debug_log["messages"].append({
                    "timestamp": datetime.now().isoformat(),
                    "elapsed": elapsed,
                    **data
                })
            print(f"  [{elapsed:.1f}s] {event}")
    
    try:
        # Load the analyst prompt (v1 - full version)
        system_prompt = await load_prompt("analyst_v1.md")
        
        # Craft a prompt that guides Claude to use WebSearch efficiently
        user_prompt = f"""Analyze this business idea: "{idea}"

Please generate a comprehensive analysis following the structure and word limits specified in your instructions. Use WebSearch to gather relevant market data, competitor information, and industry trends where helpful."""

        # Configure options
        # Note: WebSearch via SDK can take 30-120s per search
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=15,  # Allow enough turns for thorough research
            allowed_tools=["WebSearch"],
        )
        
        print(f"Analyzing: {idea}")
        print("Connecting to Claude...")
        
        result_text = []
        message_count = 0
        search_count = 0
        
        # Use ClaudeSDKClient for better control
        async with ClaudeSDKClient(options=options) as client:
            print("Sending analysis request...")
            
            # Send the query
            await client.query(user_prompt)
            
            # Collect the response - no timeout, let it complete
            print("Receiving analysis (WebSearch may take 30-120s per search)...")
            
            async for message in client.receive_response():
                message_count += 1
                message_type = type(message).__name__
                
                # Debug logging for message
                if debug:
                    msg_data = {
                        "number": message_count,
                        "type": message_type
                    }
                    
                    # Capture session ID from SystemMessage
                    if message_type == "SystemMessage" and hasattr(message, 'data'):
                        import re
                        data_str = str(getattr(message, 'data', ''))
                        match = re.search(r"'session_id':\s*'([^']+)'", data_str)
                        if match:
                            debug_log["session_id"] = match.group(1)
                            msg_data["session_id"] = match.group(1)
                            print(f"  Session ID: {match.group(1)}")
                    
                    log_event(f"Message {message_count}: {message_type}", msg_data)
                
                # Track WebSearch usage
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'name') and block.name == "WebSearch":
                            search_count += 1
                            query = getattr(block, 'input', {}).get('query', 'unknown')
                            print(f"  Searching #{search_count}: {query} (this may take 30-120s)...")
                            if debug:
                                log_event(f"WebSearch #{search_count}: {query}")
                        elif hasattr(block, 'text'):
                            result_text.append(block.text)
                
                # Show progress
                if message_count % 2 == 0:
                    print(f"  Processing... (message {message_count}, {search_count} searches)")
                
                # ResultMessage signals completion
                if message_type == "ResultMessage":
                    print(f"✓ Analysis complete ({search_count} searches used)")
                    if debug:
                        log_event("Analysis complete")
                    if hasattr(message, 'result'):
                        return message.result
                    break
        
        # If no ResultMessage, return collected text
        if result_text:
            final_analysis = "".join(result_text)
            print(f"✓ Analysis complete ({len(final_analysis)} chars)")
            return final_analysis
        else:
            print("✗ No analysis generated")
            return None
            
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        if debug:
            log_event(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Save debug log if enabled
        if debug and debug_log:
            debug_log["summary"] = {
                "total_messages": message_count,
                "total_searches": search_count,
                "total_time": time.time() - start_time
            }
            with open(debug_file, 'w') as f:
                json.dump(debug_log, f, indent=2, default=str)
            print(f"📊 Debug log saved: {debug_file}")


def save_analysis(idea: str, analysis: str) -> Path:
    """Save analysis to a markdown file."""
    slug = create_slug(idea)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create directory for this idea
    idea_dir = ANALYSES_DIR / slug
    idea_dir.mkdir(parents=True, exist_ok=True)
    
    # Save analysis with timestamp
    output_file = idea_dir / f"analysis_{timestamp}.md"
    
    # Add metadata header
    header = f"""<!-- 
Original Idea: {idea}
Generated: {datetime.now().isoformat()}
Agent: Analyst v1 (Phase 1)
-->

"""
    
    with open(output_file, 'w') as f:
        f.write(header + analysis)
    
    # Create symlink to latest analysis
    latest_link = idea_dir / "analysis.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    
    return output_file


async def main():
    """Main entry point for the analyzer."""
    parser = argparse.ArgumentParser(
        description="Analyze business ideas using Claude"
    )
    parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to logs/ directory"
    )
    
    args = parser.parse_args()
    
    # Run the analysis
    analysis = await analyze_idea(args.idea, debug=args.debug)
    
    if analysis:
        # Save the analysis
        output_path = save_analysis(args.idea, analysis)
        print(f"\n✓ Analysis saved to: {output_path}")
        
        # Show preview
        print("\n--- PREVIEW ---")
        lines = analysis.split('\n')[:20]
        for line in lines:
            print(line)
        if len(analysis.split('\n')) > 20:
            print("...")
    else:
        print("\n✗ Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())