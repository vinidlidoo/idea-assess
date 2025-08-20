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
from src.utils.result_formatter import format_pipeline_result


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

    # Get configuration (immutable)
    config = get_default_config()

    # Store context overrides (don't modify config!)
    prompt_variant: str = args.prompt_variant
    analyst_prompt_override = (
        prompt_variant if prompt_variant != config.analyst.prompt_variant else None
    )
    analyst_tools_override = (
        [] if no_websearch else None
    )  # Explicit empty list if no websearch

    # Determine pipeline mode based on CLI flags
    if not with_review:
        mode = PipelineMode.ANALYZE
        print("\n🚀 Running analysis...")
    else:
        mode = PipelineMode.ANALYZE_AND_REVIEW
        print(
            f"\n🔄 Running analysis with reviewer feedback (max {max_iterations} iterations)..."
        )

    # Create pipeline with all parameters upfront
    pipeline = AnalysisPipeline(
        idea=idea,
        config=config,
        mode=mode,
        max_iterations=max_iterations if with_review else None,
        analyst_prompt_override=analyst_prompt_override,
        analyst_tools_override=analyst_tools_override,
    )

    # Run the pipeline (no parameters needed!)
    result = await pipeline.process()

    # Format and display the result
    format_pipeline_result(result, with_review)

    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)


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
