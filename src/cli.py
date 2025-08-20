#!/usr/bin/env python3
# pyright: reportAny=false
"""
Business Idea Analyzer CLI - Modern implementation using agent architecture.

This module provides a CLI tool for analyzing business ideas using the modular
agent system with the Claude SDK.
"""

import sys
import argparse
import asyncio
import logging

from src.core import get_default_config
from src.core.pipeline import AnalysisPipeline
from src.core.types import PipelineMode
from src.utils.text_processing import create_slug
from src.utils.logger import setup_logging


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
        """,
    )

    parser.add_argument("idea", help="One-liner business idea to analyze")  # pyright: ignore[reportUnusedCallResult]

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--debug", action="store_true", help="Enable debug logging to logs/ directory"
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--no-websearch",
        "-n",
        action="store_true",
        help="Disable WebSearch tool for faster analysis (uses existing knowledge only)",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--prompt-variant",
        "-p",
        choices=["main", "v1", "v2", "v3", "revision"],
        default="main",
        help="Prompt variant to use (default: main)",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--with-review",
        "-r",
        action="store_true",
        help="Enable reviewer feedback loop for quality improvement",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--max-iterations",
        "-m",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Maximum iterations for reviewer feedback (default: 3)",
    )

    args = parser.parse_args()

    # Extract values from args with proper typing
    idea: str = args.idea
    debug: bool = args.debug
    no_websearch: bool = args.no_websearch
    with_review: bool = args.with_review
    max_iterations: int = args.max_iterations

    # Setup logging
    idea_slug = create_slug(idea)
    log_file = setup_logging(debug=debug, idea_slug=idea_slug, run_type="run")

    # Run the analysis
    print("\n" + "=" * 60)
    print("BUSINESS IDEA ANALYZER")
    print("=" * 60)
    if debug:
        print(f"Debug logging enabled: {log_file}")

    # Get configuration and apply CLI overrides
    config = get_default_config()

    # Apply prompt variant override to analyst config
    prompt_variant: str = args.prompt_variant
    if prompt_variant != config.analyst.prompt_variant:
        config.analyst.prompt_variant = prompt_variant

    # Always use the main pipeline
    pipeline = AnalysisPipeline(config)

    # Determine pipeline mode based on CLI flags
    if not with_review:
        mode = PipelineMode.ANALYZE
        print("\n🚀 Running analysis...")
    else:
        mode = PipelineMode.ANALYZE_AND_REVIEW
        print(
            f"\n🔄 Running analysis with reviewer feedback (max {max_iterations} iterations)..."
        )

    # Apply websearch preference to config
    if no_websearch:
        config.analyst.default_tools = []

    # Run the pipeline with the new interface
    result = await pipeline.process(
        idea=idea,
        mode=mode,
        max_iterations_override=max_iterations if with_review else None,
    )

    if result.get("success", False):
        if with_review:
            # Review mode - show detailed feedback
            status_emoji = "✅" if result.get("final_status") == "accepted" else "⚠️"
            status_text = (
                "ACCEPTED"
                if result.get("final_status") == "accepted"
                else "MAX ITERATIONS REACHED"
            )

            print(
                f"\n{status_emoji} Analysis {status_text} after {result.get('iteration_count', 1)} iteration(s)"
            )
            print(f"   Saved to: {result.get('file_path', 'unknown')}")

            if result.get("history_path"):
                print(f"   Iteration history: {result.get('history_path', 'N/A')}")

            # Show feedback summary
            if result.get("feedback_history"):
                last_feedback = result.get("feedback_history", [])[-1]
                print("\n📋 Final Review:")
                print(
                    f"   • Assessment: {last_feedback.get('overall_assessment', 'N/A')}"
                )
                print(
                    f"   • Critical issues: {len(last_feedback.get('critical_issues', []))}"
                )
                print(
                    f"   • Improvements: {len(last_feedback.get('improvements', []))}"
                )
                print(
                    f"   • Decision: {last_feedback.get('iteration_recommendation', 'N/A').upper()}"
                )
                if last_feedback.get("iteration_reason"):
                    print(f"   • Reason: {last_feedback.get('iteration_reason')}")
        else:
            # Simple mode - just show basic info
            print(f"\n✅ Analysis saved to: {result.get('file_path', 'unknown')}")

        sys.exit(0)
    else:
        print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        sys.exit(1)
