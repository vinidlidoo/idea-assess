"""
Improved logging system with better organization and readability.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys


class StructuredLogger:
    """
    Improved logger that creates organized, readable logs.
    """
    
    def __init__(self, run_id: str, idea_slug: str, run_type: str = "production"):
        """
        Initialize a structured logger for a specific run.
        
        Args:
            run_id: Unique identifier for this run (timestamp)
            idea_slug: Slug of the idea being analyzed
            run_type: Type of run (test, production, debug)
        """
        self.run_id = run_id
        self.idea_slug = idea_slug
        self.run_type = run_type
        self.start_time = datetime.now()
        
        # Create organized log directory structure
        self.log_dir = Path("logs") / "runs" / f"{run_id}_{idea_slug[:30]}"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup different log files
        self._setup_loggers()
        
        # Track metrics
        self.metrics = {
            "start_time": self.start_time.isoformat(),
            "idea_slug": idea_slug,
            "run_type": run_type,
            "events": [],
            "errors": [],
            "milestones": []
        }
    
    def _setup_loggers(self):
        """Setup different loggers for different purposes."""
        
        # 1. Human-readable summary log (markdown)
        self.summary_file = self.log_dir / "summary.md"
        self._write_summary_header()
        
        # 2. Structured events log (JSON lines for easy parsing)
        self.events_file = self.log_dir / "events.jsonl"
        
        # 3. Python logger for detailed debugging
        self.debug_logger = logging.getLogger(f"run_{self.run_id}")
        self.debug_logger.setLevel(logging.DEBUG)
        
        # File handler for detailed logs
        debug_handler = logging.FileHandler(self.log_dir / "debug.log")
        debug_handler.setLevel(logging.DEBUG)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Format for readability
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        debug_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.debug_logger.addHandler(debug_handler)
        self.debug_logger.addHandler(console_handler)
    
    def _write_summary_header(self):
        """Write the header for the summary file."""
        with open(self.summary_file, 'w') as f:
            f.write(f"# Run Summary: {self.idea_slug}\n\n")
            f.write(f"**Run ID:** `{self.run_id}`  \n")
            f.write(f"**Type:** {self.run_type}  \n")
            f.write(f"**Started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("## Timeline\n\n")
    
    def log_event(self, event_type: str, agent: str, data: Dict[str, Any]):
        """
        Log a structured event.
        
        Args:
            event_type: Type of event (e.g., "analysis_start", "review_complete")
            agent: Agent that generated the event
            data: Event data
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "event_type": event_type,
            "agent": agent,
            "data": data
        }
        
        # Write to JSON lines file
        with open(self.events_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Add to metrics
        self.metrics["events"].append(event)
        
        # Log to debug logger
        self.debug_logger.debug(f"[{agent}] {event_type}: {data}")
        
        # Update summary for important events
        if event_type in ["analysis_complete", "review_complete", "iteration_complete", "error"]:
            self._update_summary(elapsed, agent, event_type, data)
    
    def log_milestone(self, milestone: str, details: str = ""):
        """
        Log a major milestone in the process.
        
        Args:
            milestone: Description of the milestone
            details: Additional details
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        self.metrics["milestones"].append({
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "milestone": milestone,
            "details": details
        })
        
        # Log to console and debug
        self.debug_logger.info(f"🎯 MILESTONE: {milestone}")
        if details:
            self.debug_logger.info(f"   {details}")
        
        # Update summary
        with open(self.summary_file, 'a') as f:
            f.write(f"- **[{self._format_time(elapsed)}]** 🎯 {milestone}")
            if details:
                f.write(f" - {details}")
            f.write("\n")
    
    def log_error(self, error: str, agent: str, traceback: Optional[str] = None):
        """
        Log an error.
        
        Args:
            error: Error message
            agent: Agent where error occurred
            traceback: Optional traceback
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "agent": agent,
            "error": error,
            "traceback": traceback
        }
        
        self.metrics["errors"].append(error_data)
        
        # Log to debug logger
        self.debug_logger.error(f"[{agent}] ERROR: {error}")
        if traceback:
            self.debug_logger.error(f"Traceback:\n{traceback}")
        
        # Update summary
        with open(self.summary_file, 'a') as f:
            f.write(f"- **[{self._format_time(elapsed)}]** ❌ ERROR in {agent}: {error}\n")
    
    def _update_summary(self, elapsed: float, agent: str, event_type: str, data: Dict[str, Any]):
        """Update the summary file with important events."""
        with open(self.summary_file, 'a') as f:
            time_str = self._format_time(elapsed)
            
            if event_type == "analysis_complete":
                size = data.get("size", 0)
                f.write(f"- **[{time_str}]** ✅ Analysis complete ({size:,} chars)\n")
            
            elif event_type == "review_complete":
                recommendation = data.get("recommendation", "unknown")
                issues = data.get("critical_issues", 0)
                emoji = "✅" if recommendation == "accept" else "⚠️"
                f.write(f"- **[{time_str}]** {emoji} Review: {recommendation.upper()} ({issues} critical issues)\n")
            
            elif event_type == "iteration_complete":
                iteration = data.get("iteration", 0)
                f.write(f"- **[{time_str}]** 🔄 Iteration {iteration} complete\n")
    
    def _format_time(self, seconds: float) -> str:
        """Format elapsed time nicely."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def finalize(self, success: bool, result: Optional[Dict[str, Any]] = None):
        """
        Finalize the logging session.
        
        Args:
            success: Whether the run was successful
            result: Final result data
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        # Update metrics
        self.metrics["end_time"] = datetime.now().isoformat()
        self.metrics["total_elapsed_seconds"] = round(elapsed, 2)
        self.metrics["success"] = success
        self.metrics["result"] = result
        
        # Write final metrics
        metrics_file = self.log_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        # Update summary
        with open(self.summary_file, 'a') as f:
            f.write("\n## Final Result\n\n")
            f.write(f"**Status:** {'✅ Success' if success else '❌ Failed'}  \n")
            f.write(f"**Total Time:** {self._format_time(elapsed)}  \n")
            
            if result:
                if "file_path" in result:
                    f.write(f"**Output:** `{result['file_path']}`  \n")
                if "iteration_count" in result:
                    f.write(f"**Iterations:** {result['iteration_count']}  \n")
                if "final_status" in result:
                    f.write(f"**Final Status:** {result['final_status']}  \n")
            
            if self.metrics["errors"]:
                f.write(f"\n### Errors Encountered\n\n")
                for error in self.metrics["errors"]:
                    f.write(f"- {error['agent']}: {error['error']}\n")
        
        # Log completion
        self.debug_logger.info(f"Run completed in {self._format_time(elapsed)}")
        
        # Archive old logs if needed
        self._archive_old_logs()
    
    def _archive_old_logs(self):
        """Archive old log runs, keeping only recent ones."""
        runs_dir = Path("logs") / "runs"
        if not runs_dir.exists():
            return
        
        # Get all run directories
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()],
                         key=lambda d: d.stat().st_mtime, reverse=True)
        
        # Keep only the 10 most recent runs
        MAX_RUNS = 10
        if len(run_dirs) > MAX_RUNS:
            archive_dir = Path("logs") / "archive" / "runs"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            for old_dir in run_dirs[MAX_RUNS:]:
                # Move to archive
                import shutil
                shutil.move(str(old_dir), str(archive_dir / old_dir.name))


class LoggingContext:
    """Context manager for structured logging."""
    
    def __init__(self, idea: str, run_type: str = "production"):
        """
        Initialize logging context.
        
        Args:
            idea: Business idea being analyzed
            run_type: Type of run
        """
        from ..utils.text_processing import create_slug
        
        self.idea = idea
        self.idea_slug = create_slug(idea)
        self.run_type = run_type
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.logger = None
    
    def __enter__(self) -> StructuredLogger:
        """Enter the context and return the logger."""
        self.logger = StructuredLogger(self.run_id, self.idea_slug, self.run_type)
        self.logger.log_milestone("Run started", f"Analyzing: {self.idea}")
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and finalize logging."""
        if self.logger:
            success = exc_type is None
            if not success and exc_val:
                self.logger.log_error(str(exc_val), "Pipeline", 
                                    traceback=str(exc_tb) if exc_tb else None)
            self.logger.finalize(success)
        return False  # Don't suppress exceptions