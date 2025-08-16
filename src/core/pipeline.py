"""Pipeline orchestrator that uses file-based communication between agents."""

import asyncio
import json
from typing import Any, Optional
from datetime import datetime
from pathlib import Path

from ..agents import AnalystAgent
from ..agents.reviewer import ReviewerAgent, FeedbackProcessor
from ..core.agent_base import AgentResult
from ..core.config import AnalysisConfig
from ..utils.improved_logging import StructuredLogger
from ..utils.file_operations import save_analysis, create_or_update_symlink
from ..utils.text_processing import create_slug
from ..utils.file_operations import load_prompt
from ..utils.archive_manager import ArchiveManager


class AnalysisPipeline:
    """Orchestrates the flow of data between agents using file-based communication."""
    
    def __init__(self, config: AnalysisConfig):
        """
        Initialize the pipeline with configuration.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.agents = {}
        self.feedback_processor = FeedbackProcessor()
        self.archive_manager = ArchiveManager(max_archives=5)
    
    def register_agent(self, name: str, agent):
        """
        Register an agent in the pipeline.
        
        Args:
            name: Name to register the agent under
            agent: Agent instance
        """
        self.agents[name] = agent
    
    # Helper methods for pipeline refactoring
    def _initialize_logging(self, idea: str, debug: bool, max_iterations: int = 3, 
                           use_websearch: bool = True) -> tuple[Optional[StructuredLogger], str, str]:
        """
        Initialize logging for the pipeline run.
        
        Args:
            idea: Business idea being analyzed
            debug: Whether debug logging is enabled
            max_iterations: Maximum number of iterations
            use_websearch: Whether WebSearch is enabled
            
        Returns:
            Tuple of (logger, run_id, slug)
        """
        import os
        from datetime import datetime
        
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        slug = create_slug(idea)
        run_type = "test" if debug else "production"
        
        # Don't create pipeline logs when running from test harness
        if os.environ.get('TEST_HARNESS_RUN') == '1':
            logger = None
        else:
            logger = StructuredLogger(run_id, slug, run_type) if debug else None
        
        if logger:
            logger.log_milestone("Pipeline started", f"Max iterations: {max_iterations}")
            logger.log_event("pipeline_start", "Pipeline", {
                "idea": idea,
                "max_iterations": max_iterations,
                "use_websearch": use_websearch
            })
        
        return logger, run_id, slug
    
    def _setup_directories(self, slug: str, debug: bool) -> tuple[Path, Path]:
        """
        Setup directories for the analysis.
        
        Args:
            slug: Slugified idea name
            debug: Whether in debug mode
            
        Returns:
            Tuple of (analysis_dir, iterations_dir)
        """
        # Setup file paths
        analysis_dir = Path("analyses") / slug
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Archive existing files before starting new run
        run_type = "test" if debug else "production"
        self.archive_manager.archive_current_analysis(analysis_dir, run_type=run_type)
        
        # Create iterations directory for this run
        iterations_dir = analysis_dir / "iterations"
        iterations_dir.mkdir(exist_ok=True)
        
        return analysis_dir, iterations_dir
    
    def _find_feedback_file(self, iterations_dir: Path, iteration_count: int, 
                           analysis_dir: Path, logger: Optional[StructuredLogger]) -> Optional[Path]:
        """
        Find the appropriate feedback file for the current iteration.
        
        Args:
            iterations_dir: Directory containing iteration files
            iteration_count: Current iteration number
            analysis_dir: Main analysis directory
            logger: Optional logger for warnings
            
        Returns:
            Path to feedback file if found, None otherwise
        """
        # Look for the previous iteration's feedback
        # The reviewer creates files named reviewer_feedback_iteration_{n}.json
        latest_feedback_file = iterations_dir / f"reviewer_feedback_iteration_{iteration_count-1}.json"
        
        if not latest_feedback_file.exists():
            # Log warning about missing file before fallback
            if logger:
                logger.log_event("feedback_file_missing", "Pipeline", {
                    "expected_file": str(latest_feedback_file),
                    "iteration": iteration_count,
                    "falling_back_to": str(analysis_dir / "reviewer_feedback.json")
                })
            # Fallback to main feedback file
            latest_feedback_file = analysis_dir / "reviewer_feedback.json"
            if not latest_feedback_file.exists():
                # Critical error - no feedback available for revision
                if logger:
                    logger.log_error(f"No feedback file found for iteration {iteration_count}", "Pipeline")
                return None
        
        return latest_feedback_file
    
    def _save_analysis_files(self, analysis: str, iteration_count: int,
                           analysis_dir: Path, iterations_dir: Path,
                           logger: Optional[StructuredLogger]) -> Path:
        """
        Save analysis to both iteration file and main file.
        
        Args:
            analysis: Analysis content to save
            iteration_count: Current iteration number
            analysis_dir: Main analysis directory
            iterations_dir: Iterations directory
            logger: Optional logger
            
        Returns:
            Path to the saved iteration file
        """
        # Save iteration in iterations directory
        iteration_file = iterations_dir / f"iteration_{iteration_count}.md"
        with open(iteration_file, 'w') as f:
            f.write(analysis)
        
        # Also save/update main analysis.md (overwritten each iteration)
        main_analysis = analysis_dir / "analysis.md"
        with open(main_analysis, 'w') as f:
            f.write(analysis)
        
        if logger:
            logger.log_event("analysis_saved", "Pipeline", {
                "iteration": iteration_count,
                "file": str(iteration_file),
                "size": len(analysis)
            })
        
        return iteration_file
    
    async def run_analyst_reviewer_loop(
        self,
        idea: str,
        max_iterations: int = 3,
        debug: bool = False,
        use_websearch: bool = True
    ) -> dict[str, Any]:
        """
        Run the analyst-reviewer feedback loop using file-based communication.
        
        Args:
            idea: Business idea to analyze
            max_iterations: Maximum number of iterations
            debug: Enable debug logging
            use_websearch: Enable WebSearch for analyst
            
        Returns:
            Dictionary containing final analysis and metadata
        """
        # Initialize logging
        logger, run_id, slug = self._initialize_logging(idea, debug, max_iterations, use_websearch)
        
        # Initialize agents
        analyst = AnalystAgent(self.config)
        reviewer = ReviewerAgent(self.config)
        
        # Setup directories
        analysis_dir, iterations_dir = self._setup_directories(slug, debug)
        
        # Track iterations
        iteration_count = 0
        current_analysis = None
        current_analysis_file = None
        feedback_history = []
        iteration_results = []
        
        try:
            while iteration_count < max_iterations:
                iteration_count += 1
                
                if logger:
                    logger.log_event("iteration_start", "Pipeline", {
                        "iteration": iteration_count,
                        "has_feedback": len(feedback_history) > 0
                    })
                
                # Step 1: Generate or refine analysis
                if iteration_count == 1:
                    # Initial analysis
                    analyst_input = idea
                    revision_context = None
                else:
                    # Refined analysis based on feedback
                    # Pass the ORIGINAL idea, not revision instructions
                    analyst_input = idea
                    
                    # Find the appropriate feedback file
                    latest_feedback_file = self._find_feedback_file(
                        iterations_dir, iteration_count, analysis_dir, logger
                    )
                    if not latest_feedback_file:
                        # No feedback file found - return error
                        return {
                            "success": False,
                            "error": f"No feedback file found for iteration {iteration_count}",
                            "idea": idea,
                            "slug": slug,
                            "iteration_count": iteration_count,
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    # Pass revision context via kwargs
                    revision_context = {
                        'previous_analysis_file': str(current_analysis_file),
                        'feedback_file': str(latest_feedback_file)
                    }
                
                # Run analyst
                analyst_result = await analyst.process(
                    analyst_input,  # Always the original idea
                    debug=debug,
                    use_websearch=use_websearch and iteration_count == 1,  # Only search on first iteration
                    iteration=iteration_count,
                    analysis_dir=str(analysis_dir),
                    revision_context=revision_context  # Pass revision info separately
                )
                
                if not analyst_result.success:
                    if logger:
                        logger.log_error(
                            f"Analyst failed: {analyst_result.error}",
                            "Analyst"
                        )
                    # Return failure result immediately
                    return {
                        "success": False,
                        "error": f"Analyst failed: {analyst_result.error}",
                        "idea": idea,
                        "slug": slug,
                        "iteration_count": iteration_count,
                        "timestamp": datetime.now().isoformat()
                    }
                
                current_analysis = analyst_result.content
                
                # Save analysis to files
                iteration_file = self._save_analysis_files(
                    current_analysis, iteration_count, analysis_dir, iterations_dir, logger
                )
                current_analysis_file = str(iteration_file)
                
                # Save iteration result
                iteration_results.append({
                    "iteration": iteration_count,
                    "analysis_file": str(iteration_file),
                    "analysis_length": len(current_analysis),
                    "metadata": analyst_result.metadata
                })
                
                # Step 2: Get reviewer feedback (pass filename, not content)
                reviewer_result = await reviewer.process(
                    str(iteration_file),  # Pass the filename instead of content
                    debug=debug,
                    iteration_count=iteration_count,
                    idea_slug=slug
                )
                
                if not reviewer_result.success:
                    if logger:
                        logger.log_error(
                            f"Reviewer failed: {reviewer_result.error}",
                            "Reviewer"
                        )
                    # If reviewer fails, accept the analysis by default
                    break
                
                # Load feedback from file
                feedback_file = reviewer_result.content  # This should be the path to feedback file
                feedback = self.feedback_processor.load_feedback(feedback_file)
                feedback_history.append(feedback)
                
                # Also save/update main reviewer_feedback.json for easy access
                main_feedback = analysis_dir / "reviewer_feedback.json"
                with open(main_feedback, 'w') as f:
                    json.dump(feedback, f, indent=2)
                
                if logger:
                    logger.log_event("iteration_complete", "Pipeline", {
                        "iteration": iteration_count,
                        "feedback_file": feedback_file,
                        "recommendation": feedback.get('iteration_recommendation'),
                        "critical_issues": len(feedback.get('critical_issues', [])),
                        "reason": feedback.get('iteration_reason')
                    })
                    # Also log as milestone for visibility
                    recommendation = feedback.get('iteration_recommendation', 'unknown')
                    issues = len(feedback.get('critical_issues', []))
                    logger.log_milestone(
                        f"Iteration {iteration_count} complete",
                        f"Recommendation: {recommendation}, Critical issues: {issues}"
                    )
                
                # Check if we should continue (reviewer rejected the analysis)
                if not self.feedback_processor.should_continue_iteration(feedback, iteration_count):
                    if logger:
                        logger.log_event("analysis_accepted", "Pipeline", {
                            "iteration": iteration_count,
                            "recommendation": feedback.get('iteration_recommendation'),
                            "reason": feedback.get('iteration_reason')
                        })
                        logger.log_milestone(
                            "Analysis accepted",
                            f"After {iteration_count} iteration(s)"
                        )
                    break
                else:
                    if logger:
                        logger.log_event("analysis_rejected", "Pipeline", {
                            "iteration": iteration_count,
                            "must_continue": iteration_count < max_iterations,
                            "reason": feedback.get('iteration_reason')
                        })
            
            # Prepare final result
            # Determine if analysis was accepted or hit max iterations
            final_status = "accepted"
            if feedback_history:
                last_recommendation = feedback_history[-1].get('iteration_recommendation')
                if last_recommendation == 'reject' and iteration_count >= max_iterations:
                    final_status = "max_iterations_reached"
            
            result = {
                "success": True,
                "idea": idea,
                "slug": slug,
                "final_analysis_file": current_analysis_file,
                "final_analysis": current_analysis,
                "iteration_count": iteration_count,
                "final_status": final_status,
                "iterations": iteration_results,
                "feedback_history": feedback_history,
                "timestamp": datetime.now().isoformat()
            }
            
            # Files are already saved in clean structure (analysis.md, reviewer_feedback.json)
            if current_analysis:
                result["file_path"] = str(analysis_dir / "analysis.md")
                
                # Save consolidated metadata
                metadata = self.archive_manager.create_metadata(
                    result,
                    feedback_history[-1] if feedback_history else None,
                    iteration_results
                )
                metadata_path = analysis_dir / "metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                result["metadata_path"] = str(metadata_path)
                
                # Save iteration history (for compatibility)
                history_path = analysis_dir / "iteration_history.json"
                with open(history_path, 'w') as f:
                    json.dump({
                        "iterations": iteration_results,
                        "feedback": feedback_history,
                        "final_status": final_status,
                        "idea": idea
                    }, f, indent=2)
                result["history_path"] = str(history_path)
            
            if logger:
                logger.log_milestone(
                    "Pipeline complete",
                    f"Success after {iteration_count} iteration(s)"
                )
                logger.log_event("pipeline_complete", "Pipeline", {
                    "success": True,
                    "iterations_used": iteration_count,
                    "final_recommendation": feedback_history[-1].get('iteration_recommendation') if feedback_history else None,
                    "file_path": result.get("file_path")
                })
            
            return result
            
        except Exception as e:
            import traceback
            error_context = f"Pipeline failed at iteration {iteration_count}/{max_iterations}"
            if current_analysis_file:
                error_context += f" (last file: {current_analysis_file})"
            
            if logger:
                logger.log_error(
                    f"{type(e).__name__}: {str(e)}",
                    "Pipeline",
                    traceback=traceback.format_exc()
                )
            
            print(f"\n❌ {error_context}: {e}")
            return {
                "success": False,
                "idea": idea,
                "error": str(e),
                "error_context": error_context,
                "iteration_count": iteration_count,
                "iterations": iteration_results,
                "feedback_history": feedback_history
            }
        
        finally:
            if logger:
                # Finalize the logger with success status and result
                success = 'result' in locals() and result.get('success', False)
                logger.finalize(
                    success=success,
                    result=result if 'result' in locals() else None
                )


class SimplePipeline:
    """Simplified pipeline for single-agent operations."""
    
    @staticmethod
    async def run_analyst_only(
        idea: str,
        config: AnalysisConfig,
        debug: bool = False,
        use_websearch: bool = True
    ) -> dict[str, Any]:
        """
        Run analyst without reviewer feedback.
        
        Args:
            idea: Business idea to analyze
            config: System configuration
            debug: Enable debug logging
            use_websearch: Enable WebSearch
            
        Returns:
            Analysis result dictionary
        """
        # Initialize archive manager
        archive_manager = ArchiveManager(max_archives=5)
        
        analyst = AnalystAgent(config)
        result = await analyst.process(
            idea,
            debug=debug,
            use_websearch=use_websearch
        )
        
        if result.success:
            slug = create_slug(idea)
            
            # Setup file paths
            analysis_dir = Path("analyses") / slug
            analysis_dir.mkdir(parents=True, exist_ok=True)
            
            # Archive existing files before saving new one
            run_type = "test" if debug else "production"
            archive_manager.archive_current_analysis(analysis_dir, run_type=run_type)
            
            # Save to clean file structure (no timestamp)
            analysis_path = analysis_dir / "analysis.md"
            with open(analysis_path, 'w') as f:
                f.write(result.content)
            
            # Create metadata
            analysis_result = {
                "final_status": "completed",
                "word_count": len(result.content.split()),
                "character_count": len(result.content)
            }
            metadata = archive_manager.create_metadata(analysis_result)
            metadata_path = analysis_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "idea": idea,
                "slug": slug,
                "analysis": result.content,
                "file_path": str(analysis_path),
                "metadata": result.metadata
            }
        else:
            return {
                "success": False,
                "idea": idea,
                "error": result.error
            }