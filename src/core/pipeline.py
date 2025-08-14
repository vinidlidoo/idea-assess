"""Pipeline orchestrator that uses file-based communication between agents."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..agents import AnalystAgent
from ..agents.reviewer import ReviewerAgent, FeedbackProcessor
from ..core.agent_base import AgentResult
from ..core.config import AnalysisConfig
from ..utils.debug_logging import DebugLogger, setup_debug_logger
from ..utils.file_operations import save_analysis
from ..utils.text_processing import create_slug


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
    
    def register_agent(self, name: str, agent):
        """
        Register an agent in the pipeline.
        
        Args:
            name: Name to register the agent under
            agent: Agent instance
        """
        self.agents[name] = agent
    
    async def run_analyst_reviewer_loop(
        self,
        idea: str,
        max_iterations: int = 3,
        debug: bool = False,
        use_websearch: bool = True
    ) -> Dict[str, Any]:
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
        debug_logger = None
        if debug:
            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            debug_logger = setup_debug_logger(idea, logs_dir)
            debug_logger.log_event("pipeline_start", {
                "agent": "Pipeline",
                "idea": idea,
                "max_iterations": max_iterations
            })
        
        # Initialize agents
        analyst = AnalystAgent(self.config)
        reviewer = ReviewerAgent(self.config)
        
        # Setup file paths
        slug = create_slug(idea)
        analysis_dir = Path("analyses") / slug
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Track iterations
        iteration_count = 0
        current_analysis = None
        current_analysis_file = None
        feedback_history = []
        iteration_results = []
        
        try:
            while iteration_count < max_iterations:
                iteration_count += 1
                
                if debug_logger:
                    debug_logger.log_event("iteration_start", {
                        "agent": "Pipeline",
                        "iteration": iteration_count,
                        "has_feedback": len(feedback_history) > 0
                    })
                
                # Step 1: Generate or refine analysis
                if iteration_count == 1:
                    # Initial analysis
                    analyst_input = idea
                else:
                    # Refined analysis based on feedback
                    latest_feedback_file = analysis_dir / f"reviewer_feedback_iteration_{iteration_count-1}.json"
                    
                    # Create revision prompt that references the feedback file
                    analyst_input = f"""Please revise your analysis based on the reviewer feedback.

ORIGINAL IDEA: {idea}

PREVIOUS ANALYSIS FILE: {current_analysis_file}
REVIEWER FEEDBACK FILE: {latest_feedback_file}

INSTRUCTIONS:
1. Use the Read tool to read your previous analysis from the file above
2. Use the Read tool to read the reviewer feedback JSON from the file above
3. Revise your analysis to address all critical issues and important improvements
4. Maintain all the strong points identified in the feedback
5. Write your revised analysis using the Write tool

Please provide an improved analysis that addresses the feedback."""
                
                # Run analyst
                analyst_result = await analyst.process(
                    analyst_input,
                    debug=debug,
                    use_websearch=use_websearch and iteration_count == 1,  # Only search on first iteration
                    iteration=iteration_count,
                    analysis_dir=str(analysis_dir)
                )
                
                if not analyst_result.success:
                    if debug_logger:
                        debug_logger.log_event("analyst_failed", {
                            "agent": "Analyst",
                            "iteration": iteration_count,
                            "error": analyst_result.error
                        })
                    break
                
                current_analysis = analyst_result.content
                
                # Save analysis to file for reviewer
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                analysis_file = analysis_dir / f"analysis_iteration_{iteration_count}_{timestamp}.md"
                with open(analysis_file, 'w') as f:
                    f.write(current_analysis)
                current_analysis_file = str(analysis_file)
                
                if debug_logger:
                    debug_logger.log_event("analysis_saved", {
                        "agent": "Pipeline",
                        "iteration": iteration_count,
                        "file": str(analysis_file),
                        "size": len(current_analysis)
                    })
                
                # Save iteration result
                iteration_results.append({
                    "iteration": iteration_count,
                    "analysis_file": str(analysis_file),
                    "analysis_length": len(current_analysis),
                    "metadata": analyst_result.metadata
                })
                
                # Step 2: Get reviewer feedback (pass filename, not content)
                reviewer_result = await reviewer.process(
                    str(analysis_file),  # Pass the filename instead of content
                    debug=debug,
                    iteration_count=iteration_count,
                    idea_slug=slug
                )
                
                if not reviewer_result.success:
                    if debug_logger:
                        debug_logger.log_event("reviewer_failed", {
                            "agent": "Reviewer",
                            "iteration": iteration_count,
                            "error": reviewer_result.error
                        })
                    # If reviewer fails, accept the analysis by default
                    break
                
                # Load feedback from file
                feedback_file = reviewer_result.content  # This should be the path to feedback file
                feedback = self.feedback_processor.load_feedback(feedback_file)
                feedback_history.append(feedback)
                
                if debug_logger:
                    debug_logger.log_event("iteration_complete", {
                        "agent": "Pipeline",
                        "iteration": iteration_count,
                        "feedback_file": feedback_file,
                        "recommendation": feedback.get('iteration_recommendation'),
                        "critical_issues": len(feedback.get('critical_issues', [])),
                        "reason": feedback.get('iteration_reason')
                    })
                
                # Check if we should continue (reviewer rejected the analysis)
                if not self.feedback_processor.should_continue_iteration(feedback, iteration_count):
                    if debug_logger:
                        debug_logger.log_event("analysis_accepted", {
                            "agent": "Pipeline",
                            "iteration": iteration_count,
                            "recommendation": feedback.get('iteration_recommendation'),
                            "reason": feedback.get('iteration_reason')
                        })
                    break
                else:
                    if debug_logger:
                        debug_logger.log_event("analysis_rejected", {
                            "agent": "Pipeline",
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
            
            # Save the final analysis with standard naming
            if current_analysis:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                final_analysis_path = analysis_dir / f"analysis_{timestamp}.md"
                with open(final_analysis_path, 'w') as f:
                    f.write(current_analysis)
                result["file_path"] = str(final_analysis_path)
                
                # Create symlink to latest analysis
                latest_link = analysis_dir / "analysis.md"
                if latest_link.exists():
                    latest_link.unlink()
                latest_link.symlink_to(final_analysis_path.name)
                
                # Save iteration history
                history_path = analysis_dir / f"iteration_history_{timestamp}.json"
                with open(history_path, 'w') as f:
                    json.dump({
                        "iterations": iteration_results,
                        "feedback": feedback_history,
                        "final_status": final_status,
                        "idea": idea
                    }, f, indent=2)
                result["history_path"] = str(history_path)
                
                # Save latest reviewer feedback separately for easy access
                if feedback_history:
                    feedback_path = analysis_dir / f"reviewer_feedback_{timestamp}.json"
                    with open(feedback_path, 'w') as f:
                        json.dump(feedback_history[-1], f, indent=2)
                    result["feedback_path"] = str(feedback_path)
                    
                    # Create symlink to latest feedback
                    latest_feedback_link = analysis_dir / "reviewer_feedback.json"
                    if latest_feedback_link.exists():
                        latest_feedback_link.unlink()
                    latest_feedback_link.symlink_to(feedback_path.name)
                
                # Create symlink to latest iteration history
                latest_history_link = analysis_dir / "iteration_history.json"
                if latest_history_link.exists():
                    latest_history_link.unlink()
                latest_history_link.symlink_to(history_path.name)
            
            if debug_logger:
                debug_logger.log_event("pipeline_complete", {
                    "agent": "Pipeline",
                    "success": True,
                    "iterations_used": iteration_count,
                    "final_recommendation": feedback_history[-1].get('iteration_recommendation') if feedback_history else None
                })
            
            return result
            
        except Exception as e:
            if debug_logger:
                debug_logger.log_event("pipeline_error", {
                    "agent": "Pipeline",
                    "error": str(e),
                    "iteration": iteration_count
                })
            
            return {
                "success": False,
                "idea": idea,
                "error": str(e),
                "iteration_count": iteration_count,
                "iterations": iteration_results,
                "feedback_history": feedback_history
            }
        
        finally:
            if debug_logger:
                debug_logger.save({})


class SimplePipeline:
    """Simplified pipeline for single-agent operations."""
    
    @staticmethod
    async def run_analyst_only(
        idea: str,
        config: AnalysisConfig,
        debug: bool = False,
        use_websearch: bool = True
    ) -> Dict[str, Any]:
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
        analyst = AnalystAgent(config)
        result = await analyst.process(
            idea,
            debug=debug,
            use_websearch=use_websearch
        )
        
        if result.success:
            slug = create_slug(idea)
            
            # Save to file
            analysis_dir = Path("analyses") / slug
            analysis_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            analysis_path = analysis_dir / f"analysis_{timestamp}.md"
            with open(analysis_path, 'w') as f:
                f.write(result.content)
            
            # Create symlink to latest
            latest_link = analysis_dir / "analysis.md"
            if latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(analysis_path.name)
            
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