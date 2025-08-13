#!/usr/bin/env python3
"""
Business Idea Analyzer using ClaudeSDKClient
"""

import argparse
import asyncio
import os
import re
import sys
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


async def analyze_idea(idea: str, use_simple: bool = False) -> Optional[str]:
    """
    Analyze a business idea using ClaudeSDKClient.
    
    Args:
        idea: One-liner business idea to analyze
        
    Returns:
        Generated analysis markdown or None if error
    """
    try:
        # Use simple prompt if requested
        prompt_file = "analyst_v1_simple.md" if use_simple else "analyst_v1.md"
        system_prompt = await load_prompt(prompt_file)
        
        user_prompt = f"""Please analyze this business idea:

"{idea}"

Generate a comprehensive analysis following the structure in your instructions. 
Use WebSearch to find relevant market data and competitor information where helpful."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            allowed_tools=["WebSearch"],
            max_turns=5 if use_simple else 10
        )
        
        print(f"Analyzing: {idea}")
        print("Generating analysis with Claude...", flush=True)
        
        analysis_parts = []
        
        async with ClaudeSDKClient(options=options) as client:
            # Send the query
            await client.query(user_prompt)
            
            # Receive and collect the response
            message_count = 0
            async for message in client.receive_response():
                message_count += 1
                message_type = type(message).__name__
                
                # Debug output
                if message_count % 5 == 1:
                    print(f"\n  Processing (message {message_count}: {message_type})", end="", flush=True)
                else:
                    print(".", end="", flush=True)
                
                # Collect text from messages
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            analysis_parts.append(block.text)
                
                # Check for completion
                if message_type == "ResultMessage":
                    print(f"\n✓ Analysis complete")
                    if hasattr(message, 'result') and message.result:
                        # If ResultMessage has the full result, use it
                        return message.result
                    break
        
        # Return collected text
        if analysis_parts:
            full_analysis = "".join(analysis_parts)
            print(f"  Collected {len(analysis_parts)} text blocks, {len(full_analysis)} chars total")
            return full_analysis
        else:
            print("\n⚠ No analysis generated")
            return None
        
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
Agent: Analyst v1 (Phase 1) - Using ClaudeSDKClient
-->

"""
    
    with open(output_file, 'w') as f:
        f.write(header + analysis)
    
    # Create symlink to latest
    latest_link = idea_dir / "analysis.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    
    return output_file


async def main():
    """Main entry point for the analyzer CLI."""
    parser = argparse.ArgumentParser(
        description="Analyze business ideas using Claude SDK Client"
    )
    parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simplified prompt (analyst_v1_simple.md)"
    )
    
    args = parser.parse_args()
    
    analysis = await analyze_idea(args.idea, use_simple=args.simple)
    
    if analysis:
        output_path = save_analysis(args.idea, analysis)
        print(f"\n✓ Analysis saved to: {output_path}")
        print(f"  View with: cat {output_path}")
    else:
        print("\n✗ Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())