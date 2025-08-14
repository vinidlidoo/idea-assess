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

from src.core import get_default_config, AnalysisPipeline, SimplePipeline
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
    
    parser.add_argument(
        "--with-review", "-r",
        action="store_true",
        help="Enable reviewer feedback loop for quality improvement"
    )
    
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Maximum iterations for reviewer feedback (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Run the analysis
    print("\n" + "=" * 60)
    print("BUSINESS IDEA ANALYZER")
    print("=" * 60)
    
    # Get configuration
    config = get_default_config()
    
    if args.with_review:
        # Use the pipeline with reviewer feedback
        print(f"\n🔄 Running analysis with reviewer feedback (max {args.max_iterations} iterations)...")
        
        pipeline = AnalysisPipeline(config)
        result = await pipeline.run_analyst_reviewer_loop(
            idea=args.idea,
            max_iterations=args.max_iterations,
            debug=args.debug,
            use_websearch=not args.no_websearch
        )
        
        if result['success']:
            status_emoji = "✅" if result.get('final_status') == 'accepted' else "⚠️"
            status_text = "ACCEPTED" if result.get('final_status') == 'accepted' else "MAX ITERATIONS REACHED"
            
            print(f"\n{status_emoji} Analysis {status_text} after {result['iteration_count']} iteration(s)")
            print(f"   Saved to: {result.get('file_path', 'unknown')}")
            
            if result.get('history_path'):
                print(f"   Iteration history: {result['history_path']}")
            
            # Show feedback summary
            if result.get('feedback_history'):
                last_feedback = result['feedback_history'][-1]
                print(f"\n📋 Final Review:")
                print(f"   • Assessment: {last_feedback.get('overall_assessment', 'N/A')}")
                print(f"   • Critical issues: {len(last_feedback.get('critical_issues', []))}")
                print(f"   • Improvements: {len(last_feedback.get('improvements', []))}")
                print(f"   • Decision: {last_feedback.get('iteration_recommendation', 'N/A').upper()}")
                if last_feedback.get('iteration_reason'):
                    print(f"   • Reason: {last_feedback.get('iteration_reason')}")
            
            # Show preview of final analysis
            if result.get('final_analysis'):
                word_count = len(result['final_analysis'].split())
                print(f"\n📊 Final Statistics:")
                print(f"   • Size: {len(result['final_analysis']):,} characters ({word_count:,} words)")
                show_preview(result['final_analysis'])
            
            sys.exit(0)
        else:
            print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # Use simple pipeline (analyst only)
        result = await SimplePipeline.run_analyst_only(
            idea=args.idea,
            config=config,
            debug=args.debug,
            use_websearch=not args.no_websearch
        )
        
        if result['success']:
            print(f"\n✅ Analysis saved to: {result['file_path']}")
            
            # Show statistics
            if result.get('metadata'):
                meta = result['metadata']
                print(f"\n📊 Statistics:")
                print(f"  • Duration: {meta.get('duration', 0):.1f}s")
                print(f"  • Messages: {meta.get('message_count', 0)}")
                if not args.no_websearch:
                    print(f"  • Web searches: {meta.get('search_count', 0)}")
            
            word_count = len(result['analysis'].split())
            print(f"  • Output size: {len(result['analysis']):,} characters ({word_count:,} words)")
            
            # Show preview
            show_preview(result['analysis'])
            
            sys.exit(0)
        else:
            print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())