"""Analyst agent implementation for business idea analysis."""

import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import Any, override
import types

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..core.agent_base import BaseAgent, AgentResult
from ..core.config import AnalysisConfig
from ..core.message_processor import MessageProcessor
from ..utils.text_processing import create_slug
from ..utils.improved_logging import StructuredLogger
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
        self.prompt_version: str = prompt_version
        self.interrupt_event: threading.Event = threading.Event()
    
    @property
    @override
    def agent_name(self) -> str:
        """Return the name of this agent."""
        return "Analyst"
    
    @override
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent."""
        return f"analyst_{self.prompt_version}.md"
    
    @override
    def get_allowed_tools(self) -> list[str]:
        """Return list of allowed tools for this agent."""
        return ["WebSearch"]  # Can be configured per analysis
    
    @override
    async def process(self, input_data: str, **kwargs: Any) -> AgentResult:
        """
        Analyze a business idea.
        
        Args:
            input_data: The business idea to analyze
            **kwargs: Additional options:
                - debug: Enable debug logging
                - use_websearch: Enable WebSearch tool
                - revision_context: Dict with previous_analysis_file and feedback_file paths
                
        Returns:
            AgentResult containing the analysis
        """
        
        debug = kwargs.get('debug', False)
        use_websearch = kwargs.get('use_websearch', True)
        revision_context = kwargs.get('revision_context', None)
        
        
        try:
            result = await self._analyze_idea(
                idea=input_data,
                debug=debug,
                use_websearch=use_websearch,
                revision_context=revision_context
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
        use_websearch: bool = True,
        revision_context: dict[str, str] | None = None
    ) -> AnalysisResult | None:
        """
        Internal method to analyze a business idea.
        
        Args:
            idea: One-liner business idea to analyze
            debug: If True, log all messages to logs/ directory
            use_websearch: If True, allow WebSearch tool usage
            revision_context: Optional dict with previous_analysis_file and feedback_file paths
            
        Returns:
            AnalysisResult containing the analysis and metadata, or None if error
        """
        
        # Setup
        start_time = time.time()
        client: ClaudeSDKClient | None = None
        
        # Setup logger if debug mode (pipeline already has the main logger)
        import os
        
        # Use appropriate logger based on context
        if os.environ.get('TEST_HARNESS_RUN') == '1':
            # Use console logger for test visibility
            from ..utils.console_logger import ConsoleLogger
            logger = ConsoleLogger("Analyst")
        elif debug and not hasattr(self, '_pipeline_logger'):
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            slug = create_slug(idea)
            logger = StructuredLogger(run_id, slug, "test")
        else:
            logger = getattr(self, '_pipeline_logger', None)
        # Reset interrupt state
        self.interrupt_event.clear()
        
        # Message processor
        # MessageProcessor accepts both StructuredLogger and ConsoleLogger
        processor = MessageProcessor(logger)
        
        # Signal handler for interrupts (thread-safe)
        def handle_interrupt(signum: int, frame: types.FrameType | None) -> None:
            # Only set the event - don't modify other state or create tasks
            # The event is thread-safe and will signal the main async context
            self.interrupt_event.set()
            print("\n[ANALYST] Interrupt received, attempting graceful shutdown...", file=sys.stderr, flush=True)
        
        # Store original handler for cleanup
        original_handler = signal.getsignal(signal.SIGINT)
        
        # Register signal handler
        _ = signal.signal(signal.SIGINT, handle_interrupt)
        
        try:
            # Load the analyst prompt
            system_prompt = load_prompt(self.get_prompt_file(), self.config.prompts_dir)
            if logger:
                _ = logger.log_event("prompt_loaded", "Analyst", {
                    "prompt_file": self.get_prompt_file()
                })
            
            # Craft the user prompt with resource constraints
            websearch_instruction = (
                f"Use WebSearch efficiently (maximum {self.config.max_websearches} searches) to gather "
                "the most critical data: recent market size, key competitor metrics, and major trends."
                if use_websearch else 
                "Note: WebSearch is disabled for this analysis. Use your existing knowledge."
            )
            
            # Load and format resource constraints template
            resource_template = load_prompt("analyst_resources.md", self.config.prompts_dir)
            resource_note = resource_template.format(
                max_turns=self.config.max_turns,
                max_websearches=self.config.max_websearches if use_websearch else 0
            )
            
            # Build user prompt based on whether this is a revision
            if revision_context:
                # Load revision-specific user prompt
                revision_template = load_prompt("analyst_user_revision.md", self.config.prompts_dir)
                user_prompt = revision_template.format(
                    idea=idea,
                    previous_analysis_file=revision_context['previous_analysis_file'],
                    feedback_file=revision_context['feedback_file'],
                    resource_note=resource_note,
                    websearch_instruction=websearch_instruction
                )
            else:
                # Load and format standard user prompt template
                user_template = load_prompt("analyst_user.md", self.config.prompts_dir)
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
            
            if logger:
                _ = logger.log_event("analysis_start", "Analyst", {
                    "idea": idea,
                    "use_websearch": use_websearch
                })
            
            # Create client and analyze
            async with ClaudeSDKClient(options=options) as client_instance:
                client = client_instance
                
                await client.query(user_prompt)
                
                if logger:
                    _ = logger.log_event("analysis_receiving", "Analyst", {
                        "use_websearch": use_websearch
                    })
                
                async for message in client.receive_response():
                    
                    # Check for interrupt using thread-safe event
                    if self.interrupt_event.is_set():
                        if client:
                            # Safely interrupt the client in async context
                            await client.interrupt()
                        raise AnalysisInterrupted("User interrupted analysis")
                    
                    # Process message
                    processed = processor.process_message(message)
                    
                    # Show progress
                    stats = processor.get_statistics()
                    
                    if logger and stats['message_count'] % self.config.progress_interval == 0:
                        _ = logger.log_event("analysis_progress", "Analyst", {
                            "message_count": stats['message_count'],
                            "search_count": stats['search_count'] if use_websearch else 0
                        })
                    
                    # Check for completion
                    if processed.message_type == "ResultMessage":
                        if logger:
                            _ = logger.log_event("analysis_complete", "Analyst", {
                                "search_count": stats['search_count'] if use_websearch else 0
                            })
                        
                        # Get content from ResultMessage or collected text
                        content = processed.content[0] if processed.content else processor.get_final_content()
                        
                        if logger and content:
                            _ = logger.log_event("analysis_complete", "Analyst", {
                                "duration": time.time() - start_time,
                                "size": len(content),
                                "search_count": processor.search_count
                            })
                        
                        if content:
                            return AnalysisResult(
                                content=content,
                                idea=idea,
                                slug=create_slug(idea),
                                timestamp=datetime.now(),
                                search_count=stats['search_count'],
                                message_count=stats['message_count'],
                                duration=time.time() - start_time,
                                interrupted=self.interrupt_event.is_set()
                            )
                        break
                    
            
            
            # If no ResultMessage but we have text
            final_content = processor.get_final_content()
            if final_content:
                stats = processor.get_statistics()
                if logger:
                    _ = logger.log_event("analysis_complete", "Analyst", {
                        "size": len(final_content)
                    })
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
                print("[ANALYST] ERROR: No analysis generated", file=sys.stderr, flush=True)
                return None
                
        except AnalysisInterrupted as e:
            print(f"\n[ANALYST] WARNING: {e}", file=sys.stderr, flush=True)
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
            print(f"[ANALYST] ERROR: {error_msg}", file=sys.stderr, flush=True)
            
            if logger:
                _ = logger.log_error(str(e), "Analyst", traceback=traceback.format_exc() if debug else None)
            if debug:
                traceback.print_exc()
            return None
            
        finally:
            # Reset signal handler to original
            _ = signal.signal(signal.SIGINT, original_handler)
            
            # Finalize logging
            if logger:
                stats = processor.get_statistics()
                _ = logger.finalize(
                    success=True,
                    result={
                        "total_messages": stats['message_count'],
                        "total_searches": stats['search_count'],
                        "total_time": time.time() - start_time,
                        "interrupted": self.interrupt_event.is_set()
                    }
                )