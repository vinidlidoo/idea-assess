"""Console logger for test harness and debugging."""

import sys
from typing import Any, Optional


class ConsoleLogger:
    """Minimal logger that outputs to stderr for test visibility."""
    
    def __init__(self, agent_name: str):
        """
        Initialize console logger.
        
        Args:
            agent_name: Name of the agent for message prefixing
        """
        self.agent_name = agent_name.upper()
        self.message_count = 0
    
    def log_event(self, event_type: str, agent: str, data: dict[str, Any]) -> None:
        """
        Log an event to console.
        
        Args:
            event_type: Type of event
            agent: Agent name (usually same as self.agent_name)
            data: Event data
        """
        # For now, we only log specific important events to console
        if event_type == "analysis_start":
            idea = data.get('idea', 'unknown')[:50]
            print(f"[{self.agent_name}] Analyzing: {idea}...", file=sys.stderr, flush=True)
            if 'use_websearch' in data:
                websearch = "Enabled" if data['use_websearch'] else "Disabled"
                print(f"[{self.agent_name}] WebSearch: {websearch}", file=sys.stderr, flush=True)
        
        elif event_type == "analysis_receiving":
            print(f"[{self.agent_name}] Receiving analysis...", file=sys.stderr, flush=True)
        
        elif event_type == "analysis_progress":
            self.message_count = data.get('message_count', self.message_count)
            if self.message_count % 2 == 0:
                print(f"[{self.agent_name}] Processing... (message {self.message_count})", file=sys.stderr, flush=True)
        
        elif event_type == "analysis_complete":
            print(f"[{self.agent_name}] Analysis complete", file=sys.stderr, flush=True)
        
        elif event_type == "review_start":
            slug = data.get('idea_slug', 'unknown')
            iteration = data.get('iteration', 1)
            print(f"[{self.agent_name}] Reviewing analysis for: {slug}", file=sys.stderr, flush=True)
            print(f"[{self.agent_name}] Iteration: {iteration}", file=sys.stderr, flush=True)
        
        elif event_type == "review_processing":
            print(f"[{self.agent_name}] Processing review...", file=sys.stderr, flush=True)
        
        elif event_type == "review_progress":
            message_num = data.get('message_count', 0)
            if message_num % 2 == 0:
                print(f"[{self.agent_name}] Processing... (message {message_num})", file=sys.stderr, flush=True)
        
        elif event_type == "review_complete":
            print(f"[{self.agent_name}] Review complete", file=sys.stderr, flush=True)
            if 'recommendation' in data:
                rec = data['recommendation'].upper()
                critical = data.get('critical_issues', 0)
                print(f"[{self.agent_name}] Feedback saved: {rec} (critical issues: {critical})", file=sys.stderr, flush=True)
    
    def log_error(self, error: str, agent: str, traceback: Optional[str] = None) -> None:
        """Log an error to console."""
        print(f"[{self.agent_name}] ERROR: {error}", file=sys.stderr, flush=True)
        if traceback:
            print(f"[{self.agent_name}] Traceback: {traceback}", file=sys.stderr, flush=True)
    
    def log_milestone(self, title: str, description: str) -> None:
        """Log a milestone to console."""
        # Milestones are less important for console output
        pass
    
    def finalize(self, success: bool = True, result: Optional[dict[str, Any]] = None) -> None:
        """Finalize logging (no-op for console logger)."""
        pass