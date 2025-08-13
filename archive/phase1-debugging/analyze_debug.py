#!/usr/bin/env python3
"""
Business Idea Analyzer with Debug Logging
Debug version to understand message flow and token issues
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_code_sdk import query, ClaudeCodeOptions
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


async def analyze_idea_debug(idea: str) -> Optional[str]:
    """
    Analyze a business idea with comprehensive debug logging.
    
    Args:
        idea: One-liner business idea to analyze
        
    Returns:
        Generated analysis markdown or None if error
    """
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = LOGS_DIR / f"debug_{timestamp}.json"
    print(f"Debug logging to: {debug_file}")
    
    debug_log = {
        "idea": idea,
        "timestamp": datetime.now().isoformat(),
        "messages": [],
        "summary": {}
    }
    
    try:
        system_prompt = await load_prompt("analyst_v1.md")
        debug_log["system_prompt_length"] = len(system_prompt)
        
        user_prompt = f"""Please analyze this business idea:

"{idea}"

Generate a comprehensive analysis following the structure in your instructions. 
Use WebSearch to find relevant market data and competitor information where helpful.
Provide the complete analysis in markdown format."""

        debug_log["user_prompt_length"] = len(user_prompt)
        
        # Try with increased token limits
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=15,  # Allow many turns for research
            allowed_tools=["WebSearch"],
            max_thinking_tokens=20000,  # Significantly increase thinking tokens
        )
        
        # Log options
        debug_log["options"] = {
            "max_turns": options.max_turns,
            "allowed_tools": options.allowed_tools,
            "max_thinking_tokens": options.max_thinking_tokens,
        }
        
        print(f"Analyzing: {idea}")
        print("Generating analysis with Claude...")
        print(f"Options: max_turns={options.max_turns}, max_thinking_tokens={options.max_thinking_tokens}")
        
        result = None
        all_text = []
        message_count = 0
        
        async for message in query(prompt=user_prompt, options=options):
            message_count += 1
            message_type = type(message).__name__
            
            # Create message log entry
            msg_log = {
                "number": message_count,
                "type": message_type,
                "timestamp": datetime.now().isoformat()
            }
            
            # Extract all attributes from message
            if hasattr(message, '__dict__'):
                for key, value in message.__dict__.items():
                    if key.startswith('_'):
                        continue
                    # Try to log the value
                    if key == 'content' and hasattr(value, '__iter__'):
                        # Process content blocks
                        content_info = []
                        for block in value:
                            block_info = {"type": type(block).__name__}
                            if hasattr(block, 'text'):
                                block_info["text_length"] = len(block.text)
                                block_info["text_preview"] = block.text[:200]
                                all_text.append(block.text)
                            content_info.append(block_info)
                        msg_log["content"] = content_info
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        msg_log[key] = value
                    elif isinstance(value, (list, dict)):
                        msg_log[key] = str(value)[:500]
                    else:
                        msg_log[key] = f"<{type(value).__name__}>"
            
            debug_log["messages"].append(msg_log)
            
            # Save debug log after each message (in case of timeout)
            with open(debug_file, 'w') as f:
                json.dump(debug_log, f, indent=2, default=str)
            
            # Print progress
            print(f"\n[Message {message_count}: {message_type}]", end="", flush=True)
            
            # Check for specific message types
            if message_type == "ResultMessage":
                if hasattr(message, 'result'):
                    result = message.result
                    msg_log["has_result"] = True
                    msg_log["result_length"] = len(result) if result else 0
                print(f" - Got ResultMessage with result")
                break
            elif message_type == "AssistantMessage":
                text_count = len([b for b in getattr(message, 'content', []) if hasattr(b, 'text')])
                print(f" - {text_count} text blocks", end="")
            elif message_type == "SystemMessage":
                if hasattr(message, 'subtype'):
                    print(f" - subtype: {message.subtype}", end="")
            
            # Prevent infinite loops
            if message_count > 100:
                print(f"\n⚠ Stopping after {message_count} messages")
                break
        
        # Save debug log
        debug_log["summary"] = {
            "total_messages": message_count,
            "message_types": {},
            "total_text_blocks": len(all_text),
            "total_text_chars": sum(len(t) for t in all_text),
            "got_result_message": result is not None
        }
        
        # Count message types
        for msg in debug_log["messages"]:
            msg_type = msg["type"]
            debug_log["summary"]["message_types"][msg_type] = \
                debug_log["summary"]["message_types"].get(msg_type, 0) + 1
        
        with open(debug_file, 'w') as f:
            json.dump(debug_log, f, indent=2, default=str)
        
        print(f"\n\nDebug Summary:")
        print(f"  Total messages: {message_count}")
        print(f"  Message types: {debug_log['summary']['message_types']}")
        print(f"  Text blocks collected: {len(all_text)}")
        print(f"  Total text length: {sum(len(t) for t in all_text)} chars")
        print(f"  Got ResultMessage: {result is not None}")
        print(f"  Debug log: {debug_file}")
        
        # Return result or collected text
        if result:
            print(f"\n✓ Using ResultMessage result ({len(result)} chars)")
            return result
        elif all_text:
            combined = "".join(all_text)
            print(f"\n✓ Using collected text ({len(combined)} chars)")
            return combined
        else:
            print("\n✗ No result or text collected")
            return None
            
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        
        debug_log["error"] = {
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        
        with open(debug_file, 'w') as f:
            json.dump(debug_log, f, indent=2, default=str)
        
        return None


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
    
    return output_file


async def main():
    """Main entry point for the debug analyzer."""
    parser = argparse.ArgumentParser(
        description="Debug analyzer for business ideas"
    )
    parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    
    args = parser.parse_args()
    
    analysis = await analyze_idea_debug(args.idea)
    
    if analysis:
        output_path = save_analysis(args.idea, analysis)
        print(f"\n✓ Analysis saved to: {output_path}")
    else:
        print("\n✗ Analysis failed - check debug log")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())