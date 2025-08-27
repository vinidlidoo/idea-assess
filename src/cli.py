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

from pathlib import Path
from src.core.config import create_default_configs
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
        "--no-web-tools",
        "-n",
        action="store_true",
        help="Disable WebSearch and WebFetch tools (uses existing knowledge only)",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--analyst-prompt",
        help="Override analyst system prompt (e.g., 'concise' for experimental/analyst/concise.md)",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--reviewer-prompt",
        help="Override reviewer system prompt (e.g., 'strict' for experimental/reviewer/strict.md)",
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
        choices=[1, 2, 3, 4, 5],
        help="Maximum iterations for reviewer feedback (default: 3)",
    )

    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--slug-suffix",
        help="Suffix to append to analysis slug (e.g., 'baseline', 'v2')",
    )

    args = parser.parse_args()

    # Extract values from args with proper typing
    idea: str = args.idea
    debug: bool = args.debug
    no_web_tools: bool = args.no_web_tools
    with_review: bool = args.with_review
    max_iterations: int = args.max_iterations
    analyst_prompt: str | None = getattr(args, "analyst_prompt", None)
    reviewer_prompt: str | None = getattr(args, "reviewer_prompt", None)
    slug_suffix: str | None = getattr(args, "slug_suffix", None)

    # Setup logging
    idea_slug = create_slug(idea)
    # Apply suffix to slug if provided (must match pipeline behavior)
    if slug_suffix:
        idea_slug = f"{idea_slug}-{slug_suffix}"
    log_file = setup_logging(debug=debug, idea_slug=idea_slug, run_type="run")

    # Run the analysis
    print("\n" + "=" * 60)
    print("BUSINESS IDEA ANALYZER")
    print("=" * 60)
    if debug:
        print(f"Debug logging enabled: {log_file}")

    # Get configurations
    project_root = Path.cwd()
    system_config, analyst_config, reviewer_config = create_default_configs(
        project_root
    )

    # Apply CLI overrides directly to configs
    if analyst_prompt:
        analyst_config.system_prompt = analyst_prompt
    if reviewer_prompt:
        reviewer_config.system_prompt = reviewer_prompt
    if no_web_tools:
        # Remove only web tools, keep TodoWrite
        analyst_config.allowed_tools = ["TodoWrite"]
        analyst_config.max_websearches = 0  # No searches when web tools disabled
    if with_review and max_iterations:
        reviewer_config.max_iterations = max_iterations

    # Determine pipeline mode based on CLI flags
    if not with_review:
        mode = PipelineMode.ANALYZE
        print("\n🚀 Running analysis...")
    else:
        mode = PipelineMode.ANALYZE_AND_REVIEW
        print(
            f"\n🔄 Running analysis with reviewer feedback (max {max_iterations} iterations)..."
        )

    # Create pipeline with configurations
    pipeline = AnalysisPipeline(
        idea=idea,
        system_config=system_config,
        analyst_config=analyst_config,
        reviewer_config=reviewer_config,
        mode=mode,
        slug_suffix=slug_suffix,
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
