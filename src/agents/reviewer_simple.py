"""Simple reviewer agent implementation for providing feedback on business analyses."""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.message_processor import MessageProcessor
from ..utils.debug_logging import DebugLogger, setup_debug_logger
from ..utils.file_operations import load_prompt


class SimpleReviewerAgent(BaseAgent):
    """Simplified agent for reviewing analyses with plain text output."""
    
    def __init__(self, config: AnalysisConfig):
        """Initialize the Simple Reviewer agent."""
        super().__init__(config)
    
    @property
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "SimpleReviewer"
    
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        return "reviewer_v1_simple.md"
    
    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        return []
    
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        """
        Review a business analysis and provide structured feedback.
        
        Args:
            input_data: The analysis document to review
            **kwargs: Additional options
                
        Returns:
            AgentResult containing structured feedback
        """
        debug = kwargs.get('debug', False)
        iteration_count = kwargs.get('iteration_count', 1)
        
        # Setup debug logging if requested
        debug_logger = None
        if debug:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            debug_logger = setup_debug_logger(f"simple_review_{iteration_count}", logs_dir)
            debug_logger.log_event("review_start", {
                "agent": "SimpleReviewer",
                "iteration": iteration_count,
                "input_length": len(input_data)
            })
        
        try:
            # Load the reviewer prompt
            prompt_content = load_prompt(self.get_prompt_file(), Path("config/prompts"))
            
            # Create the review request
            review_prompt = f"""Review this business analysis:

---
{input_data}
---

Provide your feedback following the exact format in your instructions."""

            # Setup Claude SDK options
            options = ClaudeCodeOptions(
                system_prompt=prompt_content,
                max_turns=1,
                allowed_tools=[]
            )
            
            # Initialize message processor
            processor = MessageProcessor(debug_logger)
            
            # Query Claude for review
            review_content = ""
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(review_prompt)
                
                async for message in client.receive_response():
                    result = processor.process_message(message)
                    
                    # Collect content from AssistantMessages
                    if result.message_type == "AssistantMessage" and result.content:
                        review_content += "\n".join(result.content)
                    
                    # Stop at ResultMessage
                    if result.message_type == "ResultMessage":
                        break
            
            # Parse the plain text response
            feedback = self.parse_text_feedback(review_content)
            
            if debug_logger:
                debug_logger.log_event("review_complete", {
                    "agent": "SimpleReviewer",
                    "iteration": iteration_count,
                    "decision": feedback.get('decision', 'unknown'),
                    "critical_issues": len(feedback.get('critical_issues', [])),
                    "improvements": len(feedback.get('improvements', []))
                })
            
            return AgentResult(
                content=str(feedback),
                metadata={
                    'iteration': iteration_count,
                    'decision': feedback.get('decision', 'unknown'),
                    'critical_issues_count': len(feedback.get('critical_issues', [])),
                    'improvements_count': len(feedback.get('improvements', []))
                },
                success=True
            )
                
        except Exception as e:
            if debug_logger:
                debug_logger.log_event("review_error", {
                    "agent": "SimpleReviewer",
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
    
    def parse_text_feedback(self, text: str) -> Dict[str, Any]:
        """
        Parse plain text feedback into structured format.
        
        Args:
            text: Plain text feedback from reviewer
            
        Returns:
            Dictionary with parsed feedback
        """
        feedback = {
            'decision': 'ACCEPT',  # Default
            'critical_issues': [],
            'improvements': [],
            'strengths': []
        }
        
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Check for decision
            if line.startswith('DECISION:'):
                decision = line.replace('DECISION:', '').strip()
                feedback['decision'] = 'REJECT' if 'REJECT' in decision else 'ACCEPT'
            
            # Check for section headers
            elif 'CRITICAL ISSUES:' in line:
                current_section = 'critical_issues'
            elif 'IMPROVEMENTS:' in line:
                current_section = 'improvements'
            elif 'STRENGTHS:' in line:
                current_section = 'strengths'
            
            # Add items to current section
            elif line.startswith('-') and current_section:
                item = line[1:].strip()
                if item and not item.startswith('[') and item != '':
                    feedback[current_section].append(item)
        
        # Convert to format expected by pipeline
        feedback['iteration_recommendation'] = 'reject' if feedback['decision'] == 'REJECT' else 'accept'
        feedback['iteration_reason'] = f"{len(feedback['critical_issues'])} critical issues" if feedback['critical_issues'] else "Analysis meets standards"
        
        return feedback