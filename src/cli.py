#!/usr/bin/env python3
"""
Business Idea Analyzer CLI - Modern implementation using agent architecture.

This module provides a CLI tool for analyzing business ideas using the modular
agent system with the Claude SDK.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

from src.core import get_default_config
from src.agents import AnalystAgent
from src.utils.file_operations import save_analysis, AnalysisResult
from src.utils.text_processing import show_preview

# Load environment variables
load_dotenv()


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
    
    # Get configuration
    config = get_default_config()
    
    # Create analyst agent
    analyst = AnalystAgent(config, prompt_version=args.prompt_version)
    
    # Process the idea
    result = await analyst.process(
        args.idea,
        debug=args.debug,
        use_websearch=not args.no_websearch
    )
    
    if result.success:
        # Convert AgentResult to AnalysisResult for compatibility
        analysis_result = AnalysisResult(
            content=result.content,
            idea=result.metadata['idea'],
            slug=result.metadata['slug'],
            timestamp=datetime.fromisoformat(result.metadata['timestamp']),
            search_count=result.metadata.get('search_count', 0),
            message_count=result.metadata.get('message_count', 0),
            duration=result.metadata.get('duration', 0.0),
            interrupted=result.metadata.get('interrupted', False)
        )
        
        # Save the analysis
        output_path = save_analysis(analysis_result, config.analyses_dir)
        
        status = " (PARTIAL)" if analysis_result.interrupted else ""
        print(f"\n✅ Analysis{status} saved to: {output_path}")
        
        # Show statistics
        print(f"\n📊 Statistics:")
        print(f"  • Duration: {analysis_result.duration:.1f}s")
        print(f"  • Messages: {analysis_result.message_count}")
        if not args.no_websearch:
            print(f"  • Web searches: {analysis_result.search_count}")
        word_count = len(result.content.split())
        print(f"  • Output size: {len(result.content):,} characters ({word_count:,} words)")
        
        # Show preview
        show_preview(result.content)
        
        # Exit with appropriate code
        sys.exit(1 if analysis_result.interrupted else 0)
    else:
        print(f"\n❌ Analysis failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())