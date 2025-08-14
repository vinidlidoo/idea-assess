"""Reviewer agent implementation for providing feedback on business analyses."""

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
    """Agent responsible for reviewing and providing feedback on analyses."""
    
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
        # Reviewer doesn't need external tools, just analyzes the document
        return []
    
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        """
        Review a business analysis and provide structured feedback.
        
        Args:
            input_data: The analysis document to review
            **kwargs: Additional options:
                - debug: Enable debug logging
                - iteration_count: Current iteration number (for context)
                
        Returns:
            AgentResult containing structured feedback as JSON
        """
        debug = kwargs.get('debug', False)
        iteration_count = kwargs.get('iteration_count', 1)
        
        # Setup debug logging if requested
        debug_logger = None
        if debug:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            debug_logger = setup_debug_logger(f"review_iteration_{iteration_count}", logs_dir)
            debug_logger.log_event("review_start", {
                "agent": "Reviewer",
                "iteration": iteration_count,
                "input_length": len(input_data)
            })
        
        try:
            # Load the reviewer prompt
            prompt_content = load_prompt(self.get_prompt_file(), Path("config/prompts"))
            
            # Create the review request
            review_prompt = f"""Please review the following business analysis and provide structured feedback according to your instructions.

Current iteration: {iteration_count} of maximum 3

ANALYSIS TO REVIEW:
---
{input_data}
---

Provide your feedback as a properly formatted JSON object as specified in your instructions."""

            # Setup Claude SDK options
            options = ClaudeCodeOptions(
                system_prompt=prompt_content,
                max_turns=1,  # Single response for review
                allowed_tools=[],  # No tools needed for review
                permission_mode='acceptEdits'
            )
            
            # Initialize message processor
            processor = MessageProcessor(debug_logger)
            
            # Query Claude for review
            feedback_json = None
            collected_content = []
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)
                
                async for message in client.receive_response():
                    # Debug log the raw message
                    if debug_logger:
                        debug_logger.log_event(f"raw_message_{type(message).__name__}", {
                            "agent": "Reviewer",
                            "has_content_attr": hasattr(message, 'content'),
                            "has_result_attr": hasattr(message, 'result'),
                            "message_attrs": [attr for attr in dir(message) if not attr.startswith('_')][:10]
                        })
                    
                    result = processor.process_message(message)
                    
                    if debug_logger:
                        debug_logger.log_event(f"reviewer_message_{result.message_type}", {
                            "agent": "Reviewer",
                            "has_content": bool(result.content),
                            "content_length": len(result.content[0]) if result.content else 0
                        })
                    
                    # Collect content from AssistantMessages
                    if result.message_type == "AssistantMessage" and result.content:
                        collected_content.extend(result.content)
                    
                    # Process when we hit ResultMessage (end of stream)
                    if result.message_type == "ResultMessage":
                        # Check if ResultMessage has content in metadata
                        if 'result' in dir(message) and message.result:
                            content = str(message.result)
                        else:
                            # Join all collected content
                            content = "\n".join(collected_content)
                        
                        if debug_logger:
                            debug_logger.log_event("reviewer_content_check", {
                                "agent": "Reviewer",
                                "content_length": len(content),
                                "content_preview": content[:200] if content else "No content"
                            })
                        try:
                            # Try to find JSON in the content
                            if '```json' in content:
                                json_start = content.find('```json') + 7
                                json_end = content.find('```', json_start)
                                json_str = content[json_start:json_end].strip()
                            else:
                                # Assume the entire content is JSON
                                json_str = content.strip()
                            
                            feedback_json = json.loads(json_str)
                            
                            if debug_logger:
                                debug_logger.log_event("review_complete", {
                                    "agent": "Reviewer",
                                    "iteration": iteration_count,
                                    "recommendation": feedback_json.get('iteration_recommendation'),
                                    "critical_issues": len(feedback_json.get('critical_issues', [])),
                                    "improvements": len(feedback_json.get('improvements', []))
                                })
                                
                        except json.JSONDecodeError as e:
                            if debug_logger:
                                debug_logger.log_event("json_parse_error", {
                                    "agent": "Reviewer",
                                    "error": str(e),
                                    "content_preview": content[:500]
                                })
                            # Return raw content if JSON parsing fails
                            feedback_json = {
                                "error": "Failed to parse JSON feedback",
                                "raw_feedback": content,
                                "iteration_recommendation": "continue"
                            }
                        
                        # Break after processing ResultMessage
                        break
            
            if feedback_json:
                return AgentResult(
                    content=json.dumps(feedback_json, indent=2),
                    metadata={
                        'iteration': iteration_count,
                        'recommendation': feedback_json.get('iteration_recommendation', 'unknown'),
                        'critical_issues_count': len(feedback_json.get('critical_issues', [])),
                        'improvements_count': len(feedback_json.get('improvements', [])),
                        'minor_suggestions_count': len(feedback_json.get('minor_suggestions', []))
                    },
                    success=True
                )
            else:
                return AgentResult(
                    content="",
                    metadata={'iteration': iteration_count},
                    success=False,
                    error="No feedback generated"
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
    def parse_feedback(feedback_json: str) -> Dict[str, Any]:
        """
        Parse JSON feedback from reviewer.
        
        Args:
            feedback_json: JSON string containing feedback
            
        Returns:
            Parsed feedback dictionary
        """
        try:
            return json.loads(feedback_json)
        except json.JSONDecodeError:
            return {"error": "Invalid feedback format"}
    
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