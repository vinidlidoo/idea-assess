"""Reviewer agent implementation that reads analysis from file."""

import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.message_processor import MessageProcessor
from ..utils.debug_logging import DebugLogger, setup_debug_logger
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
        debug_logger = None
        if debug:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            debug_logger = setup_debug_logger(f"review_iteration_{iteration_count}", logs_dir)
            debug_logger.log_event("review_start", {
                "agent": "Reviewer",
                "iteration": iteration_count,
                "analysis_file": input_data,
                "idea_slug": idea_slug
            })
        
        try:
            # Load the reviewer prompt
            prompt_content = load_prompt(self.get_prompt_file(), Path("config/prompts"))
            
            # Construct the feedback file path
            analysis_path = Path(input_data)
            feedback_file = analysis_path.parent / f"reviewer_feedback_iteration_{iteration_count}.json"
            
            # Create the review request - just pass the filename
            review_prompt = f"""Please review the business analysis document and provide structured feedback.

Current iteration: {iteration_count} of maximum 3

ANALYSIS FILE TO REVIEW: {input_data}

INSTRUCTIONS:
1. Use the Read tool to read the analysis document at the path above
2. Review it according to your system instructions
3. Generate structured JSON feedback as specified
4. Use the Write tool to save your feedback to: {feedback_file}

The feedback JSON should follow the format specified in your system prompt.
After writing the feedback file, respond with "REVIEW_COMPLETE" to confirm."""

            # Setup Claude SDK options with tools enabled
            options = ClaudeCodeOptions(
                system_prompt=prompt_content,
                max_turns=3,  # Allow multiple turns for reading, analyzing, writing
                allowed_tools=['Read', 'Write'],  # Enable file operations
                permission_mode='default'  # Use default permission mode for automation
            )
            
            # Initialize message processor
            processor = MessageProcessor(debug_logger)
            
            # Query Claude for review
            review_complete = False
            collected_content = []
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)
                
                async for message in client.receive_response():
                    # Debug log the raw message
                    if debug_logger:
                        debug_logger.log_event(f"raw_message_{type(message).__name__}", {
                            "agent": "Reviewer",
                            "message_type": type(message).__name__,
                            "has_content_attr": hasattr(message, 'content')
                        })
                    
                    result = processor.process_message(message)
                    
                    if debug_logger:
                        debug_logger.log_event(f"reviewer_message_{result.message_type}", {
                            "agent": "Reviewer",
                            "has_content": bool(result.content),
                            "content_preview": result.content[0][:100] if result.content else None
                        })
                    
                    # Collect content from AssistantMessages
                    if result.message_type == "AssistantMessage" and result.content:
                        collected_content.extend(result.content)
                        # Check if review is complete
                        if any("REVIEW_COMPLETE" in content for content in result.content):
                            review_complete = True
                    
                    # Process when we hit ResultMessage (end of stream)
                    if result.message_type == "ResultMessage":
                        if debug_logger:
                            debug_logger.log_event("review_stream_end", {
                                "agent": "Reviewer",
                                "review_complete": review_complete,
                                "feedback_file_expected": str(feedback_file)
                            })
                        break
            
            # Check if the feedback file was created
            if feedback_file.exists():
                # Read the feedback to verify and get metadata
                with open(feedback_file, 'r') as f:
                    feedback_json = json.load(f)
                
                if debug_logger:
                    debug_logger.log_event("review_complete", {
                        "agent": "Reviewer",
                        "iteration": iteration_count,
                        "feedback_file": str(feedback_file),
                        "recommendation": feedback_json.get('iteration_recommendation'),
                        "critical_issues": len(feedback_json.get('critical_issues', [])),
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
                # Fallback: try to extract JSON from collected content if file wasn't created
                content = "\n".join(collected_content)
                if '```json' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.find('```', json_start)
                    json_str = content[json_start:json_end].strip()
                    
                    # Write it ourselves
                    feedback_json = json.loads(json_str)
                    with open(feedback_file, 'w') as f:
                        json.dump(feedback_json, f, indent=2)
                    
                    return AgentResult(
                        content=str(feedback_file),
                        metadata={
                            'iteration': iteration_count,
                            'feedback_file': str(feedback_file),
                            'recommendation': feedback_json.get('iteration_recommendation', 'unknown')
                        },
                        success=True
                    )
                else:
                    return AgentResult(
                        content="",
                        metadata={'iteration': iteration_count},
                        success=False,
                        error="Feedback file was not created and no JSON found in output"
                    )
                
        except Exception as e:
            if debug_logger:
                debug_logger.log_event("review_error", {
                    "agent": "Reviewer",
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
            if debug_logger:
                debug_logger.save({})


class FeedbackProcessor:
    """Utility class to process reviewer feedback and apply it to analyses."""
    
    @staticmethod
    def load_feedback(feedback_file: str) -> Dict[str, Any]:
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
    def should_continue_iteration(feedback: Dict[str, Any], iteration_count: int) -> bool:
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
    def format_feedback_for_analyst(feedback: Dict[str, Any]) -> str:
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