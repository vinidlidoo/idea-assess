#!/usr/bin/env python3
"""
Business Idea Analyzer - Phase 1 Prototype
Analyzes one-liner business ideas using Claude SDK
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


async def analyze_idea(idea: str, debug: bool = False) -> Optional[str]:
    """
    Analyze a business idea using Claude SDK.
    
    Args:
        idea: One-liner business idea to analyze
        
    Returns:
        Generated analysis markdown or None if error
    """
    try:
        system_prompt = await load_prompt("analyst_v1.md")
        
        user_prompt = f"""Please analyze this business idea:

"{idea}"

Generate a comprehensive analysis following the structure in your instructions. 
Use WebSearch to find relevant market data and competitor information where helpful."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=5,  # Allow multiple turns for research and generation
            allowed_tools=["WebSearch"],
        )
        
        print(f"Analyzing: {idea}")
        print("Generating analysis with Claude...", flush=True)
        
        result = None
        all_text = []
        message_count = 0
        
        async for message in query(prompt=user_prompt, options=options):
            message_count += 1
            message_type = type(message).__name__
            
            # Debug: print message type
            print(f"\n[Message {message_count}: {message_type}]", end="", flush=True)
            
            # Stop after 10 messages to prevent hanging
            if message_count > 10:
                print(f"\n⚠ Stopping after {message_count} messages")
                break
            
            # Collect text from AssistantMessages
            if message_type == "AssistantMessage":
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text = block.text
                            all_text.append(text)
                            # Show first 50 chars of text for debugging
                            preview = text[:50].replace('\n', ' ') if text else ""
                            print(f"\n  Text: {preview}...", end="", flush=True)
            
            # Check for ResultMessage
            elif message_type == "ResultMessage":
                if hasattr(message, 'result'):
                    result = message.result
                print(f"\n✓ Analysis complete (final message)")
                break
        
        # If no ResultMessage, use collected text
        if not result and all_text:
            result = "".join(all_text)
            print(f"\n✓ Analysis complete (from {len(all_text)} text blocks)")
        elif not result:
            print("\n⚠ No result received from Claude")
            return None
            
        return result
        
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_analysis(idea: str, analysis: str) -> Path:
    """
    Save analysis to a markdown file.
    
    Args:
        idea: Original idea text
        analysis: Generated analysis markdown
        
    Returns:
        Path to saved file
    """
    slug = create_slug(idea)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    idea_dir = ANALYSES_DIR / slug
    idea_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = idea_dir / f"analysis_{timestamp}.md"
    
    header = f"""<!-- 
Original Idea: {idea}
Generated: {datetime.now().isoformat()}
Agent: Analyst v1 (Phase 1)
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
    """Main entry point for the analyzer CLI."""
    parser = argparse.ArgumentParser(
        description="Analyze business ideas using Claude SDK"
    )
    parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    parser.add_argument(
        "--output", "-o",
        help="Custom output directory (default: analyses/)",
        type=Path,
        default=None
    )
    
    args = parser.parse_args()
    
    # Note: Trying to use Claude Code CLI authentication instead of API key
    # if not os.getenv("ANTHROPIC_API_KEY"):
    #     print("Error: ANTHROPIC_API_KEY environment variable not set")
    #     print("Please set it in your .env file or environment")
    #     sys.exit(1)
    
    analysis = await analyze_idea(args.idea)
    
    if analysis:
        output_path = save_analysis(args.idea, analysis)
        print(f"\n✓ Analysis saved to: {output_path}")
        print(f"  View with: cat {output_path}")
    else:
        print("\n✗ Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())