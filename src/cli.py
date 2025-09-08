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
from src.batch import BatchProcessor, show_progress, parse_ideas_file


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

    # Make idea positional argument optional when using --batch
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "idea", 
        nargs="?",  # Make optional
        help="One-liner business idea to analyze (or use --batch for multiple ideas)"
    )

    # Batch processing arguments
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--batch",
        "-b",
        action="store_true",
        help="Process multiple ideas from ideas/pending.md"
    )
    
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--ideas-file",
        default="ideas/pending.md",
        help="Path to ideas markdown file (default: ideas/pending.md)"
    )
    
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--max-concurrent",
        type=int,
        default=3,
        choices=range(1, 6),
        help="Maximum concurrent analyses for batch mode (default: 3, max: 5)"
    )

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
        "--with-fact-check",
        "-f",
        action="store_true",
        help="Enable fact-checking in parallel with review (requires --with-review)",
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
    idea: str | None = args.idea
    batch: bool = args.batch
    ideas_file: str = args.ideas_file
    max_concurrent: int = args.max_concurrent
    debug: bool = args.debug
    no_web_tools: bool = args.no_web_tools
    with_review: bool = args.with_review
    with_fact_check: bool = args.with_fact_check
    max_iterations: int = args.max_iterations
    analyst_prompt: str | None = getattr(args, "analyst_prompt", None)
    reviewer_prompt: str | None = getattr(args, "reviewer_prompt", None)
    slug_suffix: str | None = getattr(args, "slug_suffix", None)

    # Validate arguments
    if not batch and not idea:
        parser.error("Either provide an idea or use --batch flag")
    
    if batch and idea:
        parser.error("Cannot specify both an idea and --batch flag")

    # Setup logging based on mode
    if batch:
        # Batch mode logging - creates logs/batch/*/ via special handling in logger
        log_file = setup_logging(debug=debug, idea_slug="batch", run_type="run")
    else:
        # Single idea mode logging
        assert idea is not None  # We've validated this above
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
    system_config, analyst_config, reviewer_config, fact_checker_config = (
        create_default_configs(project_root)
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

    # Validate flag combinations
    if with_fact_check and not with_review:
        print("❌ Error: --with-fact-check requires --with-review")
        sys.exit(1)

    # Determine pipeline mode based on CLI flags
    if not with_review:
        mode = PipelineMode.ANALYZE
        mode_desc = "analysis"
    elif with_fact_check:
        mode = PipelineMode.ANALYZE_REVIEW_WITH_FACT_CHECK
        mode_desc = f"analysis with reviewer and fact-checker (max {max_iterations} iterations)"
    else:
        mode = PipelineMode.ANALYZE_AND_REVIEW
        mode_desc = f"analysis with reviewer feedback (max {max_iterations} iterations)"

    # Process based on batch or single mode
    if batch:
        # Batch processing mode
        ideas_path = Path(ideas_file)
        if not ideas_path.exists():
            print(f"❌ Ideas file not found: {ideas_path}")
            sys.exit(1)
        
        # Parse ideas from file
        try:
            ideas = parse_ideas_file(ideas_path)
        except Exception as e:
            print(f"❌ Error parsing ideas file: {e}")
            sys.exit(1)
        
        if not ideas:
            print(f"❌ No ideas found in {ideas_path}")
            sys.exit(1)
        
        print(f"\n🚀 Processing {len(ideas)} ideas from {ideas_path}")
        print(f"   Mode: {mode_desc}")
        print(f"   Max concurrent: {max_concurrent}")
        
        # Create batch processor
        processor = BatchProcessor(
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=mode,
            max_concurrent=max_concurrent
        )
        
        # Determine file paths for management
        pending_file = ideas_path
        completed_file = ideas_path.parent / "completed.md"
        failed_file = ideas_path.parent / "failed.md"
        
        # Start progress reporter
        progress_task = asyncio.create_task(show_progress(processor))
        
        # Process batch
        results = await processor.process_batch(
            ideas,
            pending_file=pending_file,
            completed_file=completed_file,
            failed_file=failed_file
        )
        
        # Wait for progress to finish
        await progress_task
        
        # Display final summary
        successful = sum(1 for r in results.values() if r["success"])
        failed = len(results) - successful
        
        print(f"\n✅ Batch processing complete: {successful}/{len(results)} successful")
        if failed > 0:
            print(f"❌ Failed: {failed} ideas")
        
        # Exit with appropriate code
        sys.exit(0 if failed == 0 else 1)
    
    else:
        # Single idea processing mode
        assert idea is not None  # We've validated this above
        print(f"\n🚀 Running {mode_desc}...")
        
        # Create pipeline with configurations
        pipeline = AnalysisPipeline(
            idea=idea,
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
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
