"""Debug logging utilities for the idea assessment system."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DebugLogger:
    """Handles debug logging to JSON files."""
    enabled: bool = False
    file_path: Optional[Path] = None
    start_time: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=lambda: {
        "idea": None,
        "timestamp": None,
        "session_id": None,
        "messages": [],
        "timing": []
    })
    
    def log_event(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log an event with optional data."""
        if not self.enabled:
            return
            
        elapsed = time.time() - self.start_time
        self.data["timing"].append({
            "time": elapsed,
            "event": event
        })
        
        if data:
            self.data["messages"].append({
                "timestamp": datetime.now().isoformat(),
                "elapsed": elapsed,
                **data
            })
        
        print(f"  [{elapsed:.1f}s] {event}")
    
    def save(self, summary: Dict[str, Any]) -> None:
        """Save the debug log to file."""
        if not self.enabled or not self.file_path:
            return
            
        self.data["summary"] = summary
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
        print(f"📊 Debug log saved: {self.file_path}")


def setup_debug_logger(idea: str, logs_dir: Path) -> DebugLogger:
    """
    Set up debug logging infrastructure.
    
    Args:
        idea: The business idea being analyzed
        logs_dir: Directory to save debug logs
        
    Returns:
        Configured DebugLogger instance
    """
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = logs_dir / f"debug_{timestamp}.json"
    
    logger = DebugLogger(
        enabled=True,
        file_path=debug_file
    )
    
    logger.data["idea"] = idea
    logger.data["timestamp"] = datetime.now().isoformat()
    
    print(f"📝 Debug logging enabled: {debug_file}")
    return logger