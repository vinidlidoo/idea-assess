"""Reviewer agent implementation that reads analysis from file."""

import json
import asyncio
import traceback
from typing import Any, Optional
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.constants import MAX_REVIEW_ITERATIONS, REVIEWER_MAX_TURNS
from ..core.message_processor import MessageProcessor
from ..utils.improved_logging import StructuredLogger
from ..utils.file_operations import load_prompt


class ReviewerAgent(BaseAgent):
    """Agent responsible for reviewing analyses by reading from files."""
    
    def __init__(self, config: AnalysisConfig, prompt_version: str = "v1"):
        """
        Initialize the Reviewer agent.
        
        Args:
            config: System configuration
            prompt_version: Version of the reviewer prompt to use
        """
        super().__init__(config)
        self.prompt_version = prompt_version
    
    @property
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Reviewer"
    
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        return f"reviewer_{self.prompt_version}.md"
    
    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        # Reviewer needs Read and Write tools to read analysis and write feedback
        return ['Read', 'Write']
    
    def _validate_analysis_path(self, file_path: str) -> Path:
        """Validate that path is within analyses directory.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValueError: If path is outside analyses directory
            FileNotFoundError: If file doesn't exist
        """
        # Convert to absolute path and resolve any .. or symlinks
        path = Path(file_path).resolve()
        
        # Get the analyses directory (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        analyses_dir = (project_root / "analyses").resolve()
        
        # Check if path is within analyses directory
        # Python 3.12+ compatibility: handle both ValueError and new exception types
        try:
            path.relative_to(analyses_dir)
        except (ValueError, TypeError) as e:
            # Also check if path is a parent of analyses_dir (path traversal attempt)
            if not str(path).startswith(str(analyses_dir)):
                raise ValueError(f"Invalid path: must be within analyses directory")
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"Analysis file not found: {path}")
            
        return path
    
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        """
        Review a business analysis by reading from file and write feedback to JSON.
        
        Args:
            input_data: Path to the analysis file to review
            **kwargs: Additional options:
                - debug: Enable debug logging
                - iteration_count: Current iteration number (for context)
                - idea_slug: The idea slug for file naming
                
        Returns:
            AgentResult containing path to feedback JSON file
        """
        debug = kwargs.get('debug', False)
        iteration_count = kwargs.get('iteration_count', 1)
        idea_slug = kwargs.get('idea_slug', 'unknown')
        
        # Setup debug logging if requested
        import os
        logger = None
        
        # Use appropriate logger based on context
        if os.environ.get('TEST_HARNESS_RUN') == '1':
            # Use console logger for test visibility
            from ..utils.console_logger import ConsoleLogger
            logger = ConsoleLogger("Reviewer")
        elif debug:
            from datetime import datetime
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            logger = StructuredLogger(run_id, idea_slug, "test")
            logger.log_event("review_start", "Reviewer", {
                "iteration": iteration_count,
                "analysis_file": input_data,
                "idea_slug": idea_slug
            })
        
        try:
            # Validate input path for security
            analysis_path = self._validate_analysis_path(input_data)
            
            # Load the reviewer prompt
            prompt_content = load_prompt(self.get_prompt_file(), Path("config/prompts"))
            # Save to both iterations directory and main directory
            iterations_dir = analysis_path.parent / "iterations"
            if iterations_dir.exists():
                feedback_file = iterations_dir / f"feedback_{iteration_count}.json"
            else:
                # Fallback to old structure
                feedback_file = analysis_path.parent / f"reviewer_feedback_iteration_{iteration_count}.json"
            
            # Load review instructions template and format it
            review_template = load_prompt("reviewer_instructions.md", Path("config/prompts"))
            review_prompt = review_template.format(
                iteration_count=iteration_count,
                max_iterations=MAX_REVIEW_ITERATIONS,
                analysis_path=analysis_path,
                feedback_file=feedback_file
            )

            # Setup Claude SDK options with tools enabled
            options = ClaudeCodeOptions(
                system_prompt=prompt_content,
                max_turns=REVIEWER_MAX_TURNS,  # Allow multiple turns for reading, analyzing, writing
                allowed_tools=['Read', 'Write'],  # Enable file operations
                permission_mode='default'  # Use default permission mode for automation
            )
            
            # Initialize message processor
            processor = MessageProcessor(logger)
            
            # Query Claude for review
            review_complete = False
            
            if logger:
                logger.log_event("review_start", "Reviewer", {
                    "idea_slug": idea_slug,
                    "iteration": iteration_count
                })
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)
                
                if logger:
                    logger.log_event("review_processing", "Reviewer", {})
                
                message_count = 0
                
                async for message in client.receive_response():
                    message_count += 1
                    # Debug log the raw message
                    if logger:
                        logger.log_event(f"raw_message_{type(message).__name__}", "Reviewer", {
                            "message_type": type(message).__name__,
                            "has_content_attr": hasattr(message, 'content')
                        })
                    
                    result = processor.process_message(message)
                    
                    # Show progress periodically
                    if logger and message_count % 2 == 0:
                        logger.log_event("review_progress", "Reviewer", {
                            "message_count": message_count
                        })
                    
                    if logger:
                        logger.log_event(f"reviewer_message_{result.message_type}", "Reviewer", {
                            "has_content": bool(result.content),
                            "content_preview": result.content[0][:100] if result.content else None
                        })
                    
                    # Check if review is complete
                    if result.message_type == "AssistantMessage" and result.content:
                        if any("REVIEW_COMPLETE" in content for content in result.content):
                            review_complete = True
                    
                    # Process when we hit ResultMessage (end of stream)
                    if result.message_type == "ResultMessage":
                        if logger:
                            logger.log_event("review_stream_end", "Reviewer", {
                                "review_complete": review_complete,
                                "feedback_file_expected": str(feedback_file)
                            })
                        break
            
            # Check if the feedback file was created
            if feedback_file.exists():
                # Read the feedback to verify and get metadata
                with open(feedback_file, 'r') as f:
                    feedback_json = json.load(f)
                
                # Log summary of feedback
                recommendation = feedback_json.get('iteration_recommendation', 'unknown')
                critical_count = len(feedback_json.get('critical_issues', []))
                
                if logger:
                    logger.log_event("review_complete", "Reviewer", {
                        "iteration": iteration_count,
                        "feedback_file": str(feedback_file),
                        "recommendation": recommendation,
                        "critical_issues": critical_count,
                        "improvements": len(feedback_json.get('improvements', []))
                    })
                
                return AgentResult(
                    content=str(feedback_file),  # Return the path to the feedback file
                    metadata={
                        'iteration': iteration_count,
                        'feedback_file': str(feedback_file),
                        'recommendation': feedback_json.get('iteration_recommendation', 'unknown'),
                        'critical_issues_count': len(feedback_json.get('critical_issues', [])),
                        'improvements_count': len(feedback_json.get('improvements', [])),
                        'minor_suggestions_count': len(feedback_json.get('minor_suggestions', []))
                    },
                    success=True
                )
            else:
                # Reviewer failed to create feedback file
                return AgentResult(
                    content="",
                    metadata={'iteration': iteration_count},
                    success=False,
                    error="Reviewer did not create the expected feedback file"
                )
                
        except Exception as e:
            if logger:
                logger.log_event("review_error", "Reviewer", {
                    "error": str(e),
                    "iteration": iteration_count
                })
            
            return AgentResult(
                content="",
                metadata={'iteration': iteration_count},
                success=False,
                error=str(e)
            )
        finally:
            pass  # Logger finalization handled in pipeline


class FeedbackProcessor:
    """Utility class to process reviewer feedback and apply it to analyses."""
    
    @staticmethod
    def load_feedback(feedback_file: str) -> dict[str, Any]:
        """
        Load JSON feedback from file.
        
        Args:
            feedback_file: Path to the feedback JSON file
            
        Returns:
            Parsed feedback dictionary
        """
        try:
            with open(feedback_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": f"Failed to load feedback: {str(e)}"}
    
    @staticmethod
    def should_continue_iteration(feedback: dict[str, Any], iteration_count: int) -> bool:
        """
        Determine if another iteration is needed based on feedback.
        
        Args:
            feedback: Parsed feedback dictionary
            iteration_count: Current iteration number
            
        Returns:
            True if another iteration should occur (reviewer rejected)
        """
        # Check iteration limit
        if iteration_count >= 3:
            return False
        
        # Check recommendation - only continue if rejected
        recommendation = feedback.get('iteration_recommendation', 'accept')
        return recommendation == 'reject'
    
    @staticmethod
    def format_feedback_for_analyst(feedback: dict[str, Any]) -> str:
        """
        Format reviewer feedback into instructions for the analyst.
        
        Args:
            feedback: Parsed feedback dictionary
            
        Returns:
            Formatted instructions for analyst to incorporate
        """
        instructions = []
        
        # Add overall assessment
        if 'overall_assessment' in feedback:
            instructions.append(f"OVERALL ASSESSMENT: {feedback['overall_assessment']}")
            instructions.append("")
        
        # Add critical issues that must be addressed
        if feedback.get('critical_issues'):
            instructions.append("CRITICAL ISSUES TO ADDRESS:")
            for issue in feedback['critical_issues']:
                instructions.append(f"- {issue['section']}: {issue['issue']}")
                instructions.append(f"  Suggestion: {issue['suggestion']}")
            instructions.append("")
        
        # Add important improvements
        if feedback.get('improvements'):
            instructions.append("IMPORTANT IMPROVEMENTS:")
            for improvement in feedback['improvements']:
                instructions.append(f"- {improvement['section']}: {improvement['issue']}")
                instructions.append(f"  Suggestion: {improvement['suggestion']}")
            instructions.append("")
        
        # Add minor suggestions if no critical issues
        if not feedback.get('critical_issues') and feedback.get('minor_suggestions'):
            instructions.append("MINOR ENHANCEMENTS:")
            for suggestion in feedback['minor_suggestions'][:3]:  # Limit to top 3
                instructions.append(f"- {suggestion['section']}: {suggestion['suggestion']}")
            instructions.append("")
        
        return "\n".join(instructions)