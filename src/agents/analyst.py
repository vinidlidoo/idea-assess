"""Analyst agent implementation for business idea analysis."""

import asyncio
import signal
import threading
import time
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.constants import ANALYST_MAX_TURNS, PREVIEW_CHAR_LIMIT
from ..core.message_processor import MessageProcessor
from ..utils.text_processing import create_slug
from ..utils.debug_logging import DebugLogger, setup_debug_logger
from ..utils.file_operations import load_prompt, AnalysisResult


class AnalysisInterrupted(Exception):
    """Raised when analysis is interrupted by user."""
    pass


class AnalystAgent(BaseAgent):
    """Agent responsible for analyzing business ideas."""
    
    def __init__(self, config: AnalysisConfig, prompt_version: str = "v3"):
        """
        Initialize the Analyst agent.
        
        Args:
            config: System configuration
            prompt_version: Version of the analyst prompt to use
        """
        super().__init__(config)
        self.prompt_version = prompt_version
        self.interrupt_event = threading.Event()
        self._interrupted = False
    
    @property
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Analyst"
    
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        return f"analyst_{self.prompt_version}.md"
    
    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        return ["WebSearch"]  # Can be configured per analysis
    
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        """
        Analyze a business idea.
        
        Args:
            input_data: The business idea to analyze
            **kwargs: Additional options:
                - debug: Enable debug logging
                - use_websearch: Enable WebSearch tool
                
        Returns:
            AgentResult containing the analysis
        """
        debug = kwargs.get('debug', False)
        use_websearch = kwargs.get('use_websearch', True)
        
        try:
            result = await self._analyze_idea(
                idea=input_data,
                debug=debug,
                use_websearch=use_websearch
            )
            
            if result:
                return AgentResult(
                    content=result.content,
                    metadata={
                        'idea': result.idea,
                        'slug': result.slug,
                        'timestamp': result.timestamp.isoformat(),
                        'search_count': result.search_count,
                        'message_count': result.message_count,
                        'duration': result.duration,
                        'interrupted': result.interrupted
                    },
                    success=True
                )
            else:
                return AgentResult(
                    content="",
                    metadata={'idea': input_data},
                    success=False,
                    error="Analysis failed to generate content"
                )
                
        except Exception as e:
            return AgentResult(
                content="",
                metadata={'idea': input_data},
                success=False,
                error=str(e)
            )
    
    async def _analyze_idea(
        self,
        idea: str,
        debug: bool = False,
        use_websearch: bool = True
    ) -> Optional[AnalysisResult]:
        """
        Internal method to analyze a business idea.
        
        Args:
            idea: One-liner business idea to analyze
            debug: If True, log all messages to logs/ directory
            use_websearch: If True, allow WebSearch tool usage
            
        Returns:
            AnalysisResult containing the analysis and metadata, or None if error
        """
        # Setup
        logger = setup_debug_logger(idea, self.config.logs_dir) if debug else DebugLogger()
        start_time = time.time()
        client: Optional[ClaudeSDKClient] = None
        # Reset interrupt state
        self.interrupt_event.clear()
        self._interrupted = False
        
        # Message processor
        processor = MessageProcessor(logger)
        
        # Signal handler for interrupts (thread-safe)
        def handle_interrupt(signum, frame):
            self.interrupt_event.set()
            self._interrupted = True
            print("\n⚠️  Interrupt received, attempting graceful shutdown...")
            if client:
                asyncio.create_task(client.interrupt())
        
        # Store original handler for cleanup
        original_handler = signal.getsignal(signal.SIGINT)
        
        # Register signal handler
        signal.signal(signal.SIGINT, handle_interrupt)
        
        try:
            # Load the analyst prompt
            system_prompt = load_prompt(self.get_prompt_file(), self.config.prompts_dir)
            logger.log_event(f"Loaded prompt template: {self.get_prompt_file()}")
            
            # Craft the user prompt with resource constraints
            websearch_instruction = (
                f"Use WebSearch efficiently (maximum {self.config.max_websearches} searches) to gather "
                "the most critical data: recent market size, key competitor metrics, and major trends."
                if use_websearch else 
                "Note: WebSearch is disabled for this analysis. Use your existing knowledge."
            )
            
            # Load and format resource constraints template
            resource_template = load_prompt("analyst_resources.md", Path("config/prompts"))
            resource_note = resource_template.format(
                max_turns=self.config.max_turns,
                max_websearches=self.config.max_websearches if use_websearch else 0
            )
            
            # Load and format user prompt template
            user_template = load_prompt("analyst_user.md", Path("config/prompts"))
            user_prompt = user_template.format(
                idea=idea,
                resource_note=resource_note,
                websearch_instruction=websearch_instruction
            )

            # Configure options
            allowed_tools = self.get_allowed_tools() if use_websearch else []
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=allowed_tools
            )
            
            print(f"🎯 Analyzing: {idea}")
            print(f"🔧 WebSearch: {'Enabled' if use_websearch else 'Disabled'}")
            print("🔌 Connecting to Claude...")
            
            # Create client and analyze
            async with ClaudeSDKClient(options=options) as client_instance:
                client = client_instance
                
                print("📤 Sending analysis request...")
                await client.query(user_prompt)
                
                websearch_note = " (WebSearch may take 30-120s per search)" if use_websearch else ""
                print(f"📥 Receiving analysis{websearch_note}...")
                
                async for message in client.receive_response():
                    # Check for interrupt
                    if self._interrupted:
                        raise AnalysisInterrupted("User interrupted analysis")
                    
                    # Process message
                    processed = processor.process_message(message)
                    
                    # Show progress
                    stats = processor.get_statistics()
                    if stats['message_count'] % self.config.progress_interval == 0:
                        searches_info = f", {stats['search_count']} searches" if use_websearch else ""
                        print(f"  ⏳ Processing... (message {stats['message_count']}{searches_info})")
                    
                    # Check for completion
                    if processed.message_type == "ResultMessage":
                        search_info = f" ({stats['search_count']} searches used)" if use_websearch else ""
                        print(f"✅ Analysis complete{search_info}")
                        logger.log_event("Analysis complete")
                        
                        # Get content from ResultMessage or collected text
                        content = processed.content[0] if processed.content else processor.get_final_content()
                        
                        if content:
                            return AnalysisResult(
                                content=content,
                                idea=idea,
                                slug=create_slug(idea),
                                timestamp=datetime.now(),
                                search_count=stats['search_count'],
                                message_count=stats['message_count'],
                                duration=time.time() - start_time,
                                interrupted=self._interrupted
                            )
                        break
            
            # If no ResultMessage but we have text
            final_content = processor.get_final_content()
            if final_content:
                stats = processor.get_statistics()
                print(f"✅ Analysis complete ({len(final_content)} chars)")
                return AnalysisResult(
                    content=final_content,
                    idea=idea,
                    slug=create_slug(idea),
                    timestamp=datetime.now(),
                    search_count=stats['search_count'],
                    message_count=stats['message_count'],
                    duration=time.time() - start_time,
                    interrupted=False
                )
            else:
                print("❌ No analysis generated")
                return None
                
        except AnalysisInterrupted as e:
            print(f"\n⚠️  {e}")
            # Return partial results if available
            final_content = processor.get_final_content()
            if final_content:
                stats = processor.get_statistics()
                return AnalysisResult(
                    content=final_content,
                    idea=idea,
                    slug=create_slug(idea),
                    timestamp=datetime.now(),
                    search_count=stats['search_count'],
                    message_count=stats['message_count'],
                    duration=time.time() - start_time,
                    # Already set by signal handler
                )
            return None
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"\n❌ Error during analysis after {duration:.1f}s: {e}"
            print(error_msg)
            
            logger.log_event(f"Error: {e}", {
                "duration": duration,
                "error_type": type(e).__name__
            })
            if debug:
                import traceback
                traceback.print_exc()
            return None
            
        finally:
            # Reset signal handler to original
            signal.signal(signal.SIGINT, original_handler)
            
            # Save debug log
            if logger.enabled:
                stats = processor.get_statistics()
                logger.save({
                    "total_messages": stats['message_count'],
                    "total_searches": stats['search_count'],
                    "total_time": time.time() - start_time,
                    "interrupted": self._interrupted
                })