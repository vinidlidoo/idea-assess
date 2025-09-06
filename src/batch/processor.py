"""Batch processor for concurrent idea evaluation."""

import asyncio
from datetime import datetime
from pathlib import Path

from ..core.config import SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
from ..core.pipeline import AnalysisPipeline
from ..core.types import PipelineMode, PipelineResult
from ..utils.text_processing import create_slug
from .file_manager import move_idea_to_completed, move_idea_to_failed


class BatchProcessor:
    """Process multiple ideas concurrently using asyncio."""
    
    def __init__(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig | None = None,
        fact_checker_config: FactCheckerConfig | None = None,
        mode: PipelineMode = PipelineMode.ANALYZE,
        max_concurrent: int = 3,
    ):
        """Initialize batch processor.
        
        Args:
            system_config: System configuration
            analyst_config: Analyst agent configuration
            reviewer_config: Reviewer agent configuration (optional)
            fact_checker_config: Fact-checker agent configuration (optional)
            mode: Pipeline execution mode
            max_concurrent: Maximum concurrent pipelines (default 3)
        """
        self.system_config: SystemConfig = system_config
        self.analyst_config: AnalystConfig = analyst_config
        self.reviewer_config: ReviewerConfig | None = reviewer_config
        self.fact_checker_config: FactCheckerConfig | None = fact_checker_config
        self.mode: PipelineMode = mode
        self.max_concurrent: int = max_concurrent
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)
        
        # Track processing status
        self.results: dict[str, PipelineResult] = {}
        self.start_times: dict[str, datetime] = {}
        self.end_times: dict[str, datetime] = {}
        
    async def process_with_semaphore(
        self, 
        title: str, 
        description: str
    ) -> tuple[str, PipelineResult]:
        """Process a single idea with semaphore control.
        
        Args:
            title: Idea title
            description: Idea description
            
        Returns:
            Tuple of (slug, result)
        """
        async with self.semaphore:
            # Combine title and description
            if description:
                idea = f"{title}\n\n{description}"
            else:
                idea = title
            
            # Create pipeline
            slug = create_slug(title)
            self.start_times[slug] = datetime.now()
            
            try:
                pipeline = AnalysisPipeline(
                    idea=idea,
                    system_config=self.system_config,
                    analyst_config=self.analyst_config,
                    reviewer_config=self.reviewer_config or ReviewerConfig(),
                    fact_checker_config=self.fact_checker_config or FactCheckerConfig(),
                    mode=self.mode,
                )
                
                result = await pipeline.process()
                self.end_times[slug] = datetime.now()
                return slug, result
                
            except Exception as e:
                self.end_times[slug] = datetime.now()
                # Create error result as PipelineResult TypedDict
                error_result: PipelineResult = {
                    "success": False,
                    "analysis_path": None,
                    "feedback_path": None,
                    "idea_slug": slug,
                    "iterations": 0,
                    "message": str(e),
                }
                return slug, error_result
    
    async def process_batch(
        self,
        ideas: list[tuple[str, str]],
        pending_file: Path | None = None,
        completed_file: Path | None = None,
        failed_file: Path | None = None,
    ) -> dict[str, PipelineResult]:
        """Process multiple ideas concurrently.
        
        Args:
            ideas: List of (title, description) tuples
            pending_file: Path to pending.md (for file management)
            completed_file: Path to completed.md (for file management)
            failed_file: Path to failed.md (for file management)
            
        Returns:
            Dictionary mapping slugs to results
        """
        if not ideas:
            return {}
        
        # Create tasks for all ideas
        tasks = [
            self.process_with_semaphore(title, description)
            for title, description in ideas
        ]
        
        # Simple progress display
        print(f"\nProcessing {len(ideas)} ideas with max {self.max_concurrent} concurrent pipelines...")
        print("=" * 60)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update files
        for (title, description), result_tuple in zip(ideas, results):
            if isinstance(result_tuple, Exception):
                # Handle unexpected exceptions
                slug = create_slug(title)
                error_result: PipelineResult = {
                    "success": False,
                    "analysis_path": None,
                    "feedback_path": None,
                    "idea_slug": slug,
                    "iterations": 0,
                    "message": str(result_tuple),
                }
                self.results[slug] = error_result
                
                if pending_file and failed_file:
                    move_idea_to_failed(
                        title, description, pending_file, failed_file,
                        error_message=str(result_tuple)
                    )
            else:
                slug, result = result_tuple  # type: ignore
                self.results[slug] = result
                
                # Move to appropriate file
                if pending_file:
                    if result["success"]:
                        if completed_file:
                            move_idea_to_completed(
                                title, description, pending_file, completed_file
                            )
                    elif failed_file:
                        error_msg = result.get("message") or "Unknown error"
                        move_idea_to_failed(
                            title, description, pending_file, failed_file,
                            error_message=error_msg
                        )
        
        # Display summary
        self.display_summary()
        
        return self.results
    
    def display_summary(self) -> None:
        """Display a summary table of results."""
        print("\n" + "=" * 60)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 60)
        
        for slug, result in self.results.items():
            # Calculate duration
            duration = "N/A"
            if slug in self.start_times and slug in self.end_times:
                delta = self.end_times[slug] - self.start_times[slug]
                duration = f"{delta.total_seconds():.1f}s"
            
            # Get status
            if result["success"]:
                status = "✓ Success"
                iterations = str(result.get("iterations", 1))
            else:
                status = "✗ Failed"
                iterations = "-"
                
            print(f"\n{slug}:")
            print(f"  Status: {status}")
            print(f"  Duration: {duration}")
            print(f"  Iterations: {iterations}")
            if not result["success"] and result.get("message"):
                msg = result.get("message", "")
                if msg:
                    print(f"  Error: {msg[:100]}...")
        
        # Summary stats
        successful = sum(1 for r in self.results.values() if r["success"])
        failed = len(self.results) - successful
        total_time = sum(
            (self.end_times.get(s, datetime.now()) - self.start_times.get(s, datetime.now())).total_seconds()
            for s in self.results.keys()
        )
        
        print("\n" + "-" * 60)
        print(f"Total: {len(self.results)} ideas")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_time:.1f}s")
        print("=" * 60)