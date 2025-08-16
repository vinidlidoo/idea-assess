#!/usr/bin/env python3
"""
Business Idea Analyzer CLI - Modern implementation using agent architecture.

This module provides a CLI tool for analyzing business ideas using the modular
agent system with the Claude SDK.
"""

import sys
import os
import traceback

try:
    import argparse
    import asyncio
    from pathlib import Path
except Exception as e:
    print(f"Import failure: {e}", file=sys.stderr)
    raise

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    
    from src.core import get_default_config
    from src.core.pipeline import AnalysisPipeline, SimplePipeline
    from src.utils.text_processing import show_preview
    
    # Load environment variables
    _ = load_dotenv()
except Exception as e:
    print(f"Module import failure: {e}", file=sys.stderr)
    raise


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
    
    _ = parser.add_argument(
        "idea",
        help="One-liner business idea to analyze"
    )
    
    _ = parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to logs/ directory"
    )
    
    _ = parser.add_argument(
        "--no-websearch", "-n",
        action="store_true",
        help="Disable WebSearch tool for faster analysis (uses existing knowledge only)"
    )
    
    _ = parser.add_argument(
        "--prompt-version", "-p",
        choices=["v1", "v2", "v3"],
        default="v3",
        help="Analyst prompt version to use (default: v3)"
    )
    
    _ = parser.add_argument(
        "--with-review", "-r",
        action="store_true",
        help="Enable reviewer feedback loop for quality improvement"
    )
    
    _ = parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Maximum iterations for reviewer feedback (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Extract typed values from args
    idea: str = args.idea
    debug: bool = args.debug
    no_websearch: bool = args.no_websearch
    with_review: bool = args.with_review
    max_iterations: int = args.max_iterations
    
    # Run the analysis
    print("\n" + "=" * 60)
    print("BUSINESS IDEA ANALYZER")
    print("=" * 60)
    
    # Get configuration
    config = get_default_config()
    
    if with_review:
        # Use the pipeline with reviewer feedback
        print(f"\n🔄 Running analysis with reviewer feedback (max {max_iterations} iterations)...")
        
        pipeline = AnalysisPipeline(config)
        
        result = await pipeline.run_analyst_reviewer_loop(
            idea=idea,
            max_iterations=max_iterations,
            debug=debug,
            use_websearch=not no_websearch
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
                print("\n📋 Final Review:")
                print(f"   • Assessment: {last_feedback.get('overall_assessment', 'N/A')}")
                print(f"   • Critical issues: {len(last_feedback.get('critical_issues', []))}")
                print(f"   • Improvements: {len(last_feedback.get('improvements', []))}")
                print(f"   • Decision: {last_feedback.get('iteration_recommendation', 'N/A').upper()}")
                if last_feedback.get('iteration_reason'):
                    print(f"   • Reason: {last_feedback.get('iteration_reason')}")
            
            # Show preview of final analysis
            if result.get('final_analysis'):
                word_count = len(result['final_analysis'].split())
                print("\n📊 Final Statistics:")
                print(f"   • Size: {len(result['final_analysis']):,} characters ({word_count:,} words)")
                show_preview(result['final_analysis'])
            
            sys.exit(0)
        else:
            print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # Use simple pipeline (analyst only)
        result = await SimplePipeline.run_analyst_only(
            idea=idea,
            config=config,
            debug=debug,
            use_websearch=not no_websearch
        )
        
        if result['success']:
            print(f"\n✅ Analysis saved to: {result['file_path']}")
            
            # Show statistics
            if result.get('metadata'):
                meta = result['metadata']
                print("\n📊 Statistics:")
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] Unhandled error: {e}", file=sys.stderr)
        if os.environ.get('DEBUG'):
            print(f"[FATAL] Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)