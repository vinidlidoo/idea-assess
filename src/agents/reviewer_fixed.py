"""Fixed reviewer agent implementation using proper ContentBlock handling."""

import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
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
            )
            
            # Query Claude for review
            feedback_json = None
            full_text = ""
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)
                
                async for message in client.receive_response():
                    if debug_logger:
                        debug_logger.log_event(f"Message {type(message).__name__}")
                    
                    # Extract text from AssistantMessage ContentBlocks
                    if type(message).__name__ == 'AssistantMessage':
                        if hasattr(message, 'content') and message.content:
                            for block in message.content:
                                # Check if it's a TextBlock
                                if hasattr(block, 'text'):
                                    full_text += block.text
                                    if debug_logger:
                                        debug_logger.log_event("text_block_received", {
                                            "length": len(block.text),
                                            "preview": block.text[:100]
                                        })
                    
                    # Process complete response when we hit ResultMessage
                    elif type(message).__name__ == 'ResultMessage':
                        if debug_logger:
                            debug_logger.log_event("result_message_received", {
                                "has_result": hasattr(message, 'result'),
                                "full_text_length": len(full_text)
                            })
                        break
            
            # Parse JSON from the collected text
            if full_text:
                try:
                    # Try to find JSON in the content
                    if '```json' in full_text:
                        json_start = full_text.find('```json') + 7
                        json_end = full_text.find('```', json_start)
                        json_str = full_text[json_start:json_end].strip()
                    else:
                        # Assume the entire content is JSON
                        json_str = full_text.strip()
                    
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
                            "content_preview": full_text[:500]
                        })
                    # Return raw content if JSON parsing fails
                    feedback_json = {
                        "error": "Failed to parse JSON feedback",
                        "raw_feedback": full_text,
                        "iteration_recommendation": "accept",
                        "iteration_reason": "JSON parse error - defaulting to accept"
                    }
            else:
                feedback_json = {
                    "error": "No content received",
                    "iteration_recommendation": "accept",
                    "iteration_reason": "No feedback generated"
                }
            
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
    """Utility class to process reviewer feedback."""
    
    @staticmethod
    def parse_feedback(feedback_json: str) -> Dict[str, Any]:
        """Parse JSON feedback from reviewer."""
        try:
            return json.loads(feedback_json)
        except json.JSONDecodeError:
            return {"error": "Invalid feedback format"}
    
    @staticmethod
    def should_continue_iteration(feedback: Dict[str, Any], iteration_count: int) -> bool:
        """Determine if another iteration is needed based on feedback."""
        if iteration_count >= 3:
            return False
        
        recommendation = feedback.get('iteration_recommendation', 'accept')
        return recommendation == 'reject'
    
    @staticmethod
    def format_feedback_for_analyst(feedback: Dict[str, Any]) -> str:
        """Format reviewer feedback into instructions for the analyst."""
        instructions = []
        
        if 'overall_assessment' in feedback:
            instructions.append(f"OVERALL ASSESSMENT: {feedback['overall_assessment']}")
            instructions.append("")
        
        if feedback.get('critical_issues'):
            instructions.append("CRITICAL ISSUES TO ADDRESS:")
            for issue in feedback['critical_issues']:
                instructions.append(f"- {issue['section']}: {issue['issue']}")
                instructions.append(f"  Suggestion: {issue['suggestion']}")
            instructions.append("")
        
        if feedback.get('improvements'):
            instructions.append("IMPORTANT IMPROVEMENTS:")
            for improvement in feedback['improvements']:
                instructions.append(f"- {improvement['section']}: {improvement['issue']}")
                instructions.append(f"  Suggestion: {improvement['suggestion']}")
            instructions.append("")
        
        return "\n".join(instructions)