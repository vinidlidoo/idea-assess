"""Pipeline orchestrator for coordinating multiple agents."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..agents import AnalystAgent
from ..agents.reviewer_fixed import ReviewerAgent, FeedbackProcessor
from ..core.agent_base import AgentResult
from ..core.config import AnalysisConfig
from ..utils.debug_logging import DebugLogger, setup_debug_logger
from ..utils.file_operations import save_analysis
from ..utils.text_processing import create_slug


class AnalysisPipeline:
    """Orchestrates the flow of data between agents."""
    
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
        Run the analyst-reviewer feedback loop.
        
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
        
        # Track iterations
        iteration_count = 0
        current_analysis = None
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
                    latest_feedback = feedback_history[-1]
                    formatted_feedback = self.feedback_processor.format_feedback_for_analyst(
                        latest_feedback
                    )
                    
                    analyst_input = f"""Please revise your analysis based on the following feedback:

{formatted_feedback}

ORIGINAL IDEA: {idea}

PREVIOUS ANALYSIS:
---
{current_analysis}
---

Please provide an improved analysis that addresses the feedback while maintaining all the strong points identified."""
                
                # Run analyst
                analyst_result = await analyst.process(
                    analyst_input,
                    debug=debug,
                    use_websearch=use_websearch and iteration_count == 1  # Only search on first iteration
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
                
                # Save iteration result
                iteration_results.append({
                    "iteration": iteration_count,
                    "analysis": current_analysis,
                    "metadata": analyst_result.metadata
                })
                
                # Step 2: Get reviewer feedback
                reviewer_result = await reviewer.process(
                    current_analysis,
                    debug=debug,
                    iteration_count=iteration_count
                )
                
                if not reviewer_result.success:
                    if debug_logger:
                        debug_logger.log_event("reviewer_failed", {
                            "agent": "Reviewer",
                            "iteration": iteration_count,
                            "error": reviewer_result.error
                        })
                    break
                
                # Parse feedback
                feedback = self.feedback_processor.parse_feedback(reviewer_result.content)
                feedback_history.append(feedback)
                
                if debug_logger:
                    debug_logger.log_event("iteration_complete", {
                        "agent": "Pipeline",
                        "iteration": iteration_count,
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
            slug = create_slug(idea)
            
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
                "final_analysis": current_analysis,
                "iteration_count": iteration_count,
                "final_status": final_status,
                "iterations": iteration_results,
                "feedback_history": feedback_history,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save the final analysis
            if current_analysis:
                # Create an AnalysisResult for compatibility with save_analysis
                from ..utils.file_operations import AnalysisResult
                analysis_result = AnalysisResult(
                    content=current_analysis,
                    idea=idea,
                    slug=slug,
                    timestamp=datetime.now(),
                    search_count=0,  # Will be in metadata
                    message_count=0,  # Will be in metadata
                    duration=0.0,  # Will be in metadata
                    interrupted=False
                )
                save_path = save_analysis(analysis_result, Path("analyses"))
                result["file_path"] = str(save_path)
                
                # Save iteration history
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                history_path = save_path.parent / f"iteration_history_{timestamp}.json"
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
                    feedback_path = save_path.parent / f"reviewer_feedback_{timestamp}.json"
                    with open(feedback_path, 'w') as f:
                        json.dump(feedback_history[-1], f, indent=2)
                    result["feedback_path"] = str(feedback_path)
                    
                    # Create symlink to latest feedback
                    latest_feedback_link = save_path.parent / "reviewer_feedback.json"
                    if latest_feedback_link.exists():
                        latest_feedback_link.unlink()
                    latest_feedback_link.symlink_to(feedback_path.name)
                
                # Create symlink to latest iteration history
                latest_history_link = save_path.parent / "iteration_history.json"
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
            save_path = save_analysis(result.content, idea, slug)
            
            return {
                "success": True,
                "idea": idea,
                "slug": slug,
                "analysis": result.content,
                "file_path": str(save_path),
                "metadata": result.metadata
            }
        else:
            return {
                "success": False,
                "idea": idea,
                "error": result.error
            }