#!/usr/bin/env python3
"""
Business Idea Analyzer - Analyzes business ideas using Claude SDK

This module provides a CLI tool for analyzing business ideas using the Claude SDK.
It generates comprehensive market analyses with optional web search capabilities.
"""

import argparse
import asyncio
import json
import os
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "config" / "prompts"
ANALYSES_DIR = PROJECT_ROOT / "analyses"
LOGS_DIR = PROJECT_ROOT / "logs"

# Default configuration
DEFAULT_PROMPT_FILE = "analyst_v1.md"
DEFAULT_MAX_TURNS = 15
DEFAULT_MAX_WEBSEARCHES = 5  # Limit WebSearch calls
SLUG_MAX_LENGTH = 50
PREVIEW_LINES = 20

# Progress indicators
PROGRESS_INTERVAL = 2  # Show progress every N messages


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AnalysisResult:
    """Container for analysis results and metadata."""
    content: str
    idea: str
    slug: str
    timestamp: datetime
    search_count: int = 0
    message_count: int = 0
    duration: float = 0.0
    interrupted: bool = False


@dataclass
class DebugLogger:
    """Handles debug logging to JSON files."""
    enabled: bool = False
    file_path: Optional[Path] = None
    start_time: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=lambda: {
        "idea": None,
        "timestamp": None,
        "session_id": None,
        "messages": [],
        "timing": []
    })
    
    def log_event(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log an event with optional data."""
        if not self.enabled:
            return
            
        elapsed = time.time() - self.start_time
        self.data["timing"].append({
            "time": elapsed,
            "event": event
        })
        
        if data:
            self.data["messages"].append({
                "timestamp": datetime.now().isoformat(),
                "elapsed": elapsed,
                **data
            })
        
        print(f"  [{elapsed:.1f}s] {event}")
    
    def save(self, summary: Dict[str, Any]) -> None:
        """Save the debug log to file."""
        if not self.enabled or not self.file_path:
            return
            
        self.data["summary"] = summary
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
        print(f"📊 Debug log saved: {self.file_path}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_slug(idea: str) -> str:
    """
    Create a filesystem-safe slug from an idea.
    
    Args:
        idea: The business idea text
        
    Returns:
        A sanitized slug suitable for directory names
    """
    slug = re.sub(r'[^\w\s-]', '', idea.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:SLUG_MAX_LENGTH].strip('-')


async def load_prompt(prompt_file: str = DEFAULT_PROMPT_FILE) -> str:
    """
    Load a prompt template from the prompts directory.
    
    Args:
        prompt_file: Name of the prompt file to load
        
    Returns:
        The prompt template content
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        return f.read()


def setup_debug_logger(idea: str) -> DebugLogger:
    """
    Set up debug logging infrastructure.
    
    Args:
        idea: The business idea being analyzed
        
    Returns:
        Configured DebugLogger instance
    """
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = LOGS_DIR / f"debug_{timestamp}.json"
    
    logger = DebugLogger(
        enabled=True,
        file_path=debug_file
    )
    
    logger.data["idea"] = idea
    logger.data["timestamp"] = datetime.now().isoformat()
    
    print(f"📝 Debug logging enabled: {debug_file}")
    return logger


def extract_session_id(message: Any) -> Optional[str]:
    """
    Extract session ID from a SystemMessage.
    
    Args:
        message: The message object to extract from
        
    Returns:
        Session ID if found, None otherwise
    """
    message_type = type(message).__name__
    if message_type == "SystemMessage" and hasattr(message, 'data'):
        data_str = str(getattr(message, 'data', ''))
        match = re.search(r"'session_id':\s*'([^']+)'", data_str)
        if match:
            return match.group(1)
    return None


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

class AnalysisInterrupted(Exception):
    """Raised when analysis is interrupted by user."""
    pass


async def analyze_idea(
    idea: str, 
    debug: bool = False,
    use_websearch: bool = True,
    prompt_version: str = "v2"
) -> Optional[AnalysisResult]:
    """
    Analyze a business idea using ClaudeSDKClient.
    
    Args:
        idea: One-liner business idea to analyze
        debug: If True, log all messages to logs/ directory
        use_websearch: If True, allow WebSearch tool usage
        prompt_version: Analyst prompt version to use ("v1" or "v2")
        
    Returns:
        AnalysisResult containing the analysis and metadata, or None if error
    """
    # Setup
    logger = setup_debug_logger(idea) if debug else DebugLogger()
    start_time = time.time()
    client: Optional[ClaudeSDKClient] = None
    interrupted = False
    
    # Track progress
    result_text: List[str] = []
    message_count = 0
    search_count = 0
    
    # Signal handler for interrupts
    def handle_interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True
        print("\n⚠️  Interrupt received, attempting graceful shutdown...")
        if client:
            asyncio.create_task(client.interrupt())
    
    # Register signal handler
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        # Load the analyst prompt
        prompt_file = f"analyst_{prompt_version}.md"
        system_prompt = await load_prompt(prompt_file)
        logger.log_event(f"Loaded prompt template: {prompt_file}")
        
        # Craft the user prompt with resource constraints
        websearch_instruction = (
            f"Use WebSearch efficiently (maximum {DEFAULT_MAX_WEBSEARCHES} searches) to gather "
            "the most critical data: recent market size, key competitor metrics, and major trends."
            if use_websearch else 
            "Note: WebSearch is disabled for this analysis. Use your existing knowledge."
        )
        
        resource_note = f"""
Resource constraints for this analysis:
- Maximum turns: {DEFAULT_MAX_TURNS}
- Maximum web searches: {DEFAULT_MAX_WEBSEARCHES if use_websearch else 0}
- Complete the analysis in a single comprehensive response if possible
"""
        
        user_prompt = f"""Analyze this business idea: "{idea}"

{resource_note}

Please generate a comprehensive analysis following the structure and word limits 
specified in your instructions. {websearch_instruction}"""

        # Configure options
        # Note: We only allow WebSearch when explicitly enabled
        # The agent should generate content directly without needing file tools
        allowed_tools = ["WebSearch"] if use_websearch else []
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=DEFAULT_MAX_TURNS,
            allowed_tools=allowed_tools,
        )
        
        print(f"🎯 Analyzing: {idea}")
        print(f"🔧 WebSearch: {'Enabled' if use_websearch else 'Disabled'}")
        print("🔌 Connecting to Claude...")
        
        # Create client and analyze
        async with ClaudeSDKClient(options=options) as client_instance:
            client = client_instance
            
            print("📤 Sending analysis request...")
            await client.query(user_prompt)
            
            websearch_note = " (WebSearch may take 30-120s per search)" if use_websearch else ""
            print(f"📥 Receiving analysis{websearch_note}...")
            
            async for message in client.receive_response():
                # Check for interrupt
                if interrupted:
                    raise AnalysisInterrupted("User interrupted analysis")
                
                message_count += 1
                message_type = type(message).__name__
                
                # Debug logging
                if logger.enabled:
                    msg_data = {
                        "number": message_count,
                        "type": message_type
                    }
                    
                    # Capture session ID
                    session_id = extract_session_id(message)
                    if session_id:
                        logger.data["session_id"] = session_id
                        msg_data["session_id"] = session_id
                        print(f"  Session ID: {session_id}")
                    
                    # Capture content preview for different message types
                    if message_type == "UserMessage":
                        # UserMessages contain WebSearch results
                        # According to types.py: content: str | list[ContentBlock]
                        content_preview = []
                        
                        if hasattr(message, 'content'):
                            msg_content = message.content
                            if isinstance(msg_content, str):
                                # Direct string content
                                content_preview.append(msg_content[:500] + "..." if len(msg_content) > 500 else msg_content)
                            elif isinstance(msg_content, list):
                                # List of ContentBlocks
                                for block in msg_content[:3]:  # First 3 blocks
                                    if hasattr(block, 'text'):
                                        # Longer preview for UserMessage text blocks
                                        text = block.text[:400] + "..." if len(block.text) > 400 else block.text
                                        content_preview.append(text)
                                    elif hasattr(block, 'content'):
                                        # ToolResultBlock has content (WebSearch results)
                                        block_content = block.content
                                        if isinstance(block_content, str):
                                            # Clean up WebSearch results for readability
                                            clean_content = block_content
                                            
                                            # Try to extract just the search query and key results
                                            import re
                                            query_match = re.search(r'query:\s*["\']([^"\']+)["\']', clean_content)
                                            query = query_match.group(1) if query_match else "unknown query"
                                            
                                            # Skip the boilerplate and get actual content
                                            if '\n\n' in clean_content:
                                                # Skip to the actual results after the preamble
                                                parts = clean_content.split('\n\n', 1)
                                                if len(parts) > 1:
                                                    clean_content = parts[1]
                                            
                                            # Truncate and clean (longer for UserMessages to see search results better)
                                            preview = clean_content[:800] + "..." if len(clean_content) > 800 else clean_content
                                            preview = ' '.join(preview.split())  # Normalize whitespace
                                            
                                            content_preview.append(f"[Search: {query}] {preview[:600]}...")
                                        elif isinstance(block_content, list):
                                            # List of search result items (structured data)
                                            preview_items = []
                                            for item in block_content[:2]:  # First 2 items
                                                if isinstance(item, dict):
                                                    title = item.get('title', '')
                                                    snippet = item.get('snippet', item.get('content', ''))[:80]
                                                    preview_items.append(f"{title}: {snippet}")
                                            if preview_items:
                                                content_preview.append(f"[Search Results] {'; '.join(preview_items)}")
                        
                        if content_preview:
                            # Clean up and join
                            cleaned = [' '.join(p.replace('\n', ' ').split()) for p in content_preview]
                            msg_data["content_preview"] = cleaned[:3]  # Max 3 previews
                            
                    elif message_type == "ResultMessage":
                        # Capture result preview and cost info
                        if hasattr(message, 'result') and message.result:
                            result = str(message.result)[:200] + "..." if len(str(message.result)) > 200 else str(message.result)
                            msg_data["result_preview"] = result.replace('\n', ' ')
                        if hasattr(message, 'total_cost_usd') and message.total_cost_usd:
                            msg_data["cost_usd"] = message.total_cost_usd
                    
                    logger.log_event(f"Message {message_count}: {message_type}", msg_data)
                
                # Track WebSearch usage and collect text
                if hasattr(message, 'content'):
                    content_preview = []
                    for block in message.content:
                        if hasattr(block, 'name') and block.name == "WebSearch":
                            search_count += 1
                            query = getattr(block, 'input', {}).get('query', 'unknown')
                            print(f"  🔍 Search #{search_count}: {query} (may take 30-120s)...")
                            logger.log_event(f"WebSearch #{search_count}: {query}")
                            content_preview.append(f"[WebSearch: {query}]")
                        elif hasattr(block, 'text'):
                            result_text.append(block.text)
                            # Add text preview to debug log (first 200 chars)
                            text_preview = block.text[:200] + "..." if len(block.text) > 200 else block.text
                            content_preview.append(text_preview.replace('\n', ' '))
                    
                    # Log message content preview if debug enabled
                    if logger.enabled and content_preview:
                        logger.data["messages"][-1]["content_preview"] = content_preview[:3]  # First 3 blocks
                
                # Show progress
                if message_count % PROGRESS_INTERVAL == 0:
                    searches_info = f", {search_count} searches" if use_websearch else ""
                    print(f"  ⏳ Processing... (message {message_count}{searches_info})")
                
                # Check for completion
                if message_type == "ResultMessage":
                    search_info = f" ({search_count} searches used)" if use_websearch else ""
                    print(f"✅ Analysis complete{search_info}")
                    logger.log_event("Analysis complete")
                    
                    # Get content from ResultMessage or collected text
                    content = getattr(message, 'result', None) or "".join(result_text)
                    
                    if content:
                        return AnalysisResult(
                            content=content,
                            idea=idea,
                            slug=create_slug(idea),
                            timestamp=datetime.now(),
                            search_count=search_count,
                            message_count=message_count,
                            duration=time.time() - start_time,
                            interrupted=False
                        )
                    break
        
        # If no ResultMessage but we have text
        if result_text:
            final_analysis = "".join(result_text)
            print(f"✅ Analysis complete ({len(final_analysis)} chars)")
            return AnalysisResult(
                content=final_analysis,
                idea=idea,
                slug=create_slug(idea),
                timestamp=datetime.now(),
                search_count=search_count,
                message_count=message_count,
                duration=time.time() - start_time,
                interrupted=False
            )
        else:
            print("❌ No analysis generated")
            return None
            
    except AnalysisInterrupted as e:
        print(f"\n⚠️  {e}")
        # Return partial results if available
        if result_text:
            return AnalysisResult(
                content="".join(result_text),
                idea=idea,
                slug=create_slug(idea),
                timestamp=datetime.now(),
                search_count=search_count,
                message_count=message_count,
                duration=time.time() - start_time,
                interrupted=True
            )
        return None
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        logger.log_event(f"Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None
        
    finally:
        # Reset signal handler
        signal.signal(signal.SIGINT, signal.default_int_handler)
        
        # Save debug log
        if logger.enabled:
            logger.save({
                "total_messages": message_count,
                "total_searches": search_count,
                "total_time": time.time() - start_time,
                "interrupted": interrupted
            })


def save_analysis(result: AnalysisResult) -> Path:
    """
    Save analysis result to a markdown file.
    
    Args:
        result: The analysis result to save
        
    Returns:
        Path to the saved file
    """
    # Create directory for this idea
    idea_dir = ANALYSES_DIR / result.slug
    idea_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
    output_file = idea_dir / f"analysis_{timestamp_str}.md"
    
    # Add metadata header
    interrupted_note = "\nNote: Analysis was interrupted by user" if result.interrupted else ""
    websearch_note = f"\nWebSearches: {result.search_count}" if result.search_count > 0 else "\nWebSearch: Disabled"
    
    header = f"""<!-- 
Original Idea: {result.idea}
Generated: {result.timestamp.isoformat()}
Agent: Analyst (Phase 1)
Duration: {result.duration:.1f}s
Messages: {result.message_count}{websearch_note}{interrupted_note}
-->

"""
    
    with open(output_file, 'w') as f:
        f.write(header + result.content)
    
    # Create/update symlink to latest analysis
    latest_link = idea_dir / "analysis.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    
    return output_file


def show_preview(content: str, max_lines: int = PREVIEW_LINES) -> None:
    """
    Display a preview of the analysis content.
    
    Args:
        content: The full analysis text
        max_lines: Maximum number of lines to show
    """
    print("\n" + "=" * 60)
    print("ANALYSIS PREVIEW")
    print("=" * 60)
    
    lines = content.split('\n')[:max_lines]
    for line in lines:
        print(line)
    
    if len(content.split('\n')) > max_lines:
        print("...")
        print(f"\n[Preview shows first {max_lines} lines of {len(content.split('\n'))} total]")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for the analyzer CLI."""
    parser = argparse.ArgumentParser(
        description="Analyze business ideas using Claude SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "AI-powered fitness app"
  %(prog)s "Sustainable packaging solution" --debug
  %(prog)s "B2B marketplace" --no-websearch
  %(prog)s "EdTech platform" -n --debug
        """
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
    
    parser.add_argument(
        "--no-websearch", "-n",
        action="store_true",
        help="Disable WebSearch tool for faster analysis (uses existing knowledge only)"
    )
    
    parser.add_argument(
        "--prompt-version", "-p",
        choices=["v1", "v2", "v3"],
        default="v3",
        help="Analyst prompt version to use (default: v3)"
    )
    
    args = parser.parse_args()
    
    # Run the analysis
    print("\n" + "=" * 60)
    print("BUSINESS IDEA ANALYZER")
    print("=" * 60)
    
    result = await analyze_idea(
        idea=args.idea,
        debug=args.debug,
        use_websearch=not args.no_websearch,
        prompt_version=args.prompt_version
    )
    
    if result:
        # Save the analysis
        output_path = save_analysis(result)
        
        status = " (PARTIAL)" if result.interrupted else ""
        print(f"\n✅ Analysis{status} saved to: {output_path}")
        
        # Show statistics
        print(f"\n📊 Statistics:")
        print(f"  • Duration: {result.duration:.1f}s")
        print(f"  • Messages: {result.message_count}")
        if not args.no_websearch:
            print(f"  • Web searches: {result.search_count}")
        word_count = len(result.content.split())
        print(f"  • Output size: {len(result.content):,} characters ({word_count:,} words)")
        
        # Show preview
        show_preview(result.content)
        
        # Exit with appropriate code
        sys.exit(1 if result.interrupted else 0)
    else:
        print("\n❌ Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())