# RunAnalytics Refactoring Task List

**Created**: 2025-08-19 10:15:00 PST
**Author**: Python Refactor Planner
**Status**: Ready for Implementation

## Executive Summary

Complete refactoring of MessageProcessor class into a comprehensive RunAnalytics system for tracking, analyzing, and persisting detailed metrics across multi-agent pipeline executions. This transformation will enable data-driven optimization while maintaining backward compatibility during migration.

## Scope

**Components Being Refactored**:
- `src/core/message_processor.py` → `src/core/run_analytics.py` (new class, new responsibilities)
- `src/core/config.py` → Add `run_analytics` field to BaseContext
- `src/agents/analyst.py` → Switch from MessageProcessor to RunAnalytics
- `src/agents/reviewer.py` → Switch from MessageProcessor to RunAnalytics  
- `src/core/pipeline.py` → Create and manage RunAnalytics lifecycle
- `src/core/agent_base.py` → Simplify AgentResult metadata structure
- Test files → Update to match new structure

## Impact Analysis

**Directly Affected Files** (require modification):
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/message_processor.py` (to be deleted after migration)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/run_analytics.py` (to be created)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/config.py` (lines 168-188, add field)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py` (lines 144, 245, 248, 262, 276-278)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py` (lines 16, 155, and message tracking sections)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py` (initialization and context passing)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py` (lines 14-22, AgentResult structure)
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_message_processor.py` (to be replaced)

**Indirectly Affected** (may need review):
- Integration tests that check AgentResult metadata fields
- Any logging or debugging tools that parse messages.jsonl format
- Session logs or documentation referencing MessageProcessor

## Prerequisites

Before starting the refactoring:

1. **Ensure virtual environment is activated**: `source .venv/bin/activate`
2. **Run existing tests to establish baseline**: `python -m pytest tests/unit/test_message_processor.py -v`
3. **Create a feature branch**: `git checkout -b refactor/runanalytics`
4. **Review the full proposal**: Read `/Users/vincent/Projects/recursive-experiments/idea-assess/session-logs/2025-08-19-message-processor-refactor-v2.md`

## Task List

### Phase 1: Create RunAnalytics Foundation

#### Task 1: Create RunAnalytics class structure
**File**: Create `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/run_analytics.py`

```python
"""Comprehensive analytics engine for multi-agent pipeline runs."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from claude_code_sdk.types import (
    ContentBlock,
    SystemMessage,
    UserMessage, 
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Metrics for a single agent's execution."""
    agent_name: str
    iteration: int
    message_count: int = 0
    tool_uses: dict[str, int] = field(default_factory=dict)
    text_blocks: int = 0
    thinking_blocks: int = 0
    total_text_length: int = 0
    search_queries: list[str] = field(default_factory=list)
    search_results: list[dict] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    session_id: Optional[str] = None
    total_cost_usd: Optional[float] = None
    

class RunAnalytics:
    """
    Comprehensive analytics engine for multi-agent pipeline runs.
    
    Primary responsibilities:
    1. Track messages, tools, and timing across all agents
    2. Extract and correlate artifacts from SDK messages  
    3. Aggregate statistics per agent and globally
    4. Persist analytics data for post-run analysis
    """
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize analytics for a pipeline run."""
        self.run_id = run_id
        self.output_dir = output_dir
        self.start_time = datetime.now()
        
        # Tracking structures
        self.agent_metrics: dict[tuple[str, int], AgentMetrics] = {}
        self.tool_correlations: dict[str, dict] = {}  # tool_use_id -> result mapping
        self.messages_file = output_dir / f"{run_id}_messages.jsonl"
        
        # Global counters
        self.global_message_count = 0
        self.global_tool_count = 0
```

**Warnings**: 
- Ensure ThinkingBlock import exists (may need SDK update)
- Path must be absolute for output_dir

#### Task 2: Implement message tracking method
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/run_analytics.py`
**Location**: Add to RunAnalytics class after __init__

```python
    def track_message(self, message: object, agent_name: str, iteration: int = 0) -> None:
        """
        Track a message and extract artifacts.
        
        Args:
            message: SDK message to track
            agent_name: Name of the agent processing this message
            iteration: Current iteration number (for multi-iteration workflows)
        """
        self.global_message_count += 1
        
        # Get or create agent metrics
        key = (agent_name, iteration)
        if key not in self.agent_metrics:
            self.agent_metrics[key] = AgentMetrics(agent_name, iteration)
        
        metrics = self.agent_metrics[key]
        metrics.message_count += 1
        
        # Extract artifacts based on message type
        artifacts = {}
        
        if isinstance(message, SystemMessage):
            artifacts = self._extract_system_artifacts(message)
            if artifacts.get("session_id"):
                metrics.session_id = artifacts["session_id"]
                
        elif isinstance(message, (UserMessage, AssistantMessage)):
            artifacts = self._extract_content_artifacts(message, metrics)
            
        elif isinstance(message, ResultMessage):
            artifacts = self._extract_result_artifacts(message)
            metrics.end_time = datetime.now()
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            if message.total_cost_usd:
                metrics.total_cost_usd = message.total_cost_usd
        
        # Write to messages.jsonl
        self._write_message_log(message, agent_name, iteration, artifacts)
```

**Warnings**:
- Ensure thread safety if used in async context
- Handle file I/O errors gracefully

#### Task 3: Implement artifact extraction methods
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/run_analytics.py`
**Location**: Add these private methods to RunAnalytics class

```python
    def _extract_system_artifacts(self, message: SystemMessage) -> dict:
        """Extract artifacts from SystemMessage."""
        artifacts = {
            "subtype": message.subtype,
            "data": message.data or {}
        }
        if message.data and "session_id" in message.data:
            artifacts["session_id"] = message.data["session_id"]
        return artifacts
    
    def _extract_content_artifacts(self, message: UserMessage | AssistantMessage, 
                                  metrics: AgentMetrics) -> dict:
        """Extract artifacts from content messages."""
        artifacts = {"blocks": []}
        
        content = message.content
        if isinstance(content, str):
            artifacts["content_type"] = "string"
            artifacts["content_length"] = len(content)
            metrics.total_text_length += len(content)
        else:  # list[ContentBlock]
            artifacts["content_type"] = "blocks"
            for block in content:
                block_artifacts = self._extract_block_artifacts(block, metrics)
                artifacts["blocks"].append(block_artifacts)
        
        return artifacts
    
    def _extract_block_artifacts(self, block: ContentBlock, metrics: AgentMetrics) -> dict:
        """Extract artifacts from a single content block."""
        if isinstance(block, TextBlock):
            metrics.text_blocks += 1
            metrics.total_text_length += len(block.text)
            return {
                "type": "TextBlock",
                "text_length": len(block.text),
                "text_preview": block.text[:200] + "..." if len(block.text) > 200 else block.text
            }
            
        elif isinstance(block, ToolUseBlock):
            tool_name = block.name
            metrics.tool_uses[tool_name] = metrics.tool_uses.get(tool_name, 0) + 1
            self.global_tool_count += 1
            
            artifacts = {
                "type": "ToolUseBlock",
                "tool_id": block.id,
                "tool_name": tool_name,
                "tool_input": {}
            }
            
            # Extract tool-specific inputs
            if tool_name == "WebSearch" and block.input:
                query = block.input.get("query", "")
                metrics.search_queries.append(query)
                artifacts["tool_input"]["query"] = query
                
            # Store for correlation with results
            self.tool_correlations[block.id] = {
                "tool_name": tool_name,
                "input": block.input
            }
            
            return artifacts
            
        elif isinstance(block, ToolResultBlock):
            artifacts = {
                "type": "ToolResultBlock", 
                "tool_use_id": block.tool_use_id if hasattr(block, 'tool_use_id') else None,
                "is_error": block.is_error,
                "content_preview": str(block.content)[:500] if block.content else None
            }
            
            # Extract WebSearch results
            if block.content and isinstance(block.content, str) and "Links:" in block.content:
                links_match = re.search(r'Links:\s*(\[.*?\])', block.content, re.DOTALL)
                if links_match:
                    try:
                        links_data = json.loads(links_match.group(1))
                        search_results = [
                            {"title": link.get("title"), "url": link.get("url")}
                            for link in links_data
                        ]
                        artifacts["search_results"] = search_results
                        metrics.search_results.extend(search_results)
                    except json.JSONDecodeError:
                        logger.debug(f"Failed to parse search results JSON")
            
            return artifacts
            
        elif isinstance(block, ThinkingBlock):
            metrics.thinking_blocks += 1
            return {
                "type": "ThinkingBlock",
                "thinking_length": len(block.thinking),
                "thinking_preview": block.thinking[:200] + "..." if len(block.thinking) > 200 else block.thinking
            }
            
        return {"type": "Unknown"}
```

**Warnings**:
- ThinkingBlock may not be available in current SDK version
- ToolResultBlock may not have tool_use_id attribute in all SDK versions
- JSON parsing of search results is fragile - needs error handling

### Phase 2: Integrate with Configuration

#### Task 4: Update BaseContext with RunAnalytics field
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/config.py`
**Location**: Lines 168-188, in BaseContext dataclass

```python
@dataclass
class BaseContext:
    """Base context with common fields for all agent operations.
    
    Contains fields that all agents need for runtime state and config overrides.
    """
    
    # Runtime state
    output_dir: Path | None = None
    """Custom output directory (None = use default)"""
    
    revision_context: RevisionContext | None = None
    """Revision context if this is an iterative improvement"""
    
    run_analytics: "RunAnalytics | None" = None  # Add this line
    """Analytics tracker for the current pipeline run"""
    
    # Config overrides (None means "use agent's default from config")
    tools_override: list[str] | None = None
    """Custom tool list for this operation (None = use agent's default_tools)"""
    
    prompt_version_override: str | None = None
    """Custom prompt version for this operation (None = use agent's prompt_version)"""
```

**Warnings**:
- Use forward reference string to avoid circular import
- May need TYPE_CHECKING import for proper type hints

### Phase 3: Update Agent Implementations

#### Task 5: Import RunAnalytics in analyst.py
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Location**: Line 16, replace MessageProcessor import

```python
# Replace this line:
from ..core.message_processor import MessageProcessor

# With this line:
from ..core.run_analytics import RunAnalytics  # Once created
# Keep MessageProcessor import temporarily for compatibility
from ..core.message_processor import MessageProcessor  # TODO: Remove after full migration
```

#### Task 6: Update AnalystAgent to use RunAnalytics
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Location**: Lines 144-278, in _analyze_with_sdk method

Replace:
```python
# Line 144
processor = MessageProcessor()
```

With:
```python
# Use RunAnalytics from context if available, fallback to MessageProcessor
if hasattr(context, 'run_analytics') and context.run_analytics:
    analytics = context.run_analytics
    use_analytics = True
else:
    # Fallback for backward compatibility
    processor = MessageProcessor()
    use_analytics = False
```

Then update message tracking (line 245):
```python
# Replace:
processor.track_message(message)

# With:
if use_analytics:
    analytics.track_message(message, agent_name="analyst", iteration=revision_context.get("iteration", 0) if revision_context else 0)
else:
    processor.track_message(message)
```

Update statistics retrieval (line 248):
```python
# Replace:
stats = processor.get_statistics()

# With:
if use_analytics:
    key = ("analyst", revision_context.get("iteration", 0) if revision_context else 0)
    metrics = analytics.agent_metrics.get(key)
    stats = {
        "message_count": metrics.message_count if metrics else 0,
        "search_count": len(metrics.search_queries) if metrics else 0
    }
else:
    stats = processor.get_statistics()
```

**Warnings**:
- Must maintain backward compatibility during migration
- revision_context structure may vary

#### Task 7: Update ReviewerAgent similarly
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
**Location**: Line 16 and around line 155

Apply same pattern as AnalystAgent:
1. Add conditional import
2. Check for run_analytics in context  
3. Use analytics.track_message() with agent_name="reviewer"
4. Adapt statistics retrieval

### Phase 4: Update Pipeline Integration

#### Task 8: Create RunAnalytics in Pipeline
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Location**: In run_analyst_reviewer_loop method, after line 187

```python
# After initializing logging (line 187)
run_id, slug = self._initialize_logging(idea, max_iterations)

# Add RunAnalytics initialization
from ..core.run_analytics import RunAnalytics
from ..utils.logger import get_log_directory  # Assuming this exists

log_dir = get_log_directory() if hasattr(logger, 'handlers') else Path("logs/runs")
run_analytics = RunAnalytics(run_id, log_dir)
```

#### Task 9: Pass RunAnalytics via context
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Location**: When creating contexts for agents

For AnalystContext creation:
```python
analyst_context = AnalystContext(
    output_dir=analysis_dir,
    idea_slug=slug,
    run_analytics=run_analytics,  # Add this
    tools_override=tools_override,
    revision_context=revision_context if iteration_count > 0 else None
)
```

For ReviewerContext creation:
```python
reviewer_context = ReviewerContext(
    analysis_path=iteration_file,
    output_dir=analysis_dir,
    run_analytics=run_analytics,  # Add this
)
```

#### Task 10: Finalize RunAnalytics at pipeline end
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Location**: Before returning PipelineResult

```python
# Before return statement
if run_analytics:
    run_analytics.finalize()  # This will write run_summary.json
```

### Phase 5: Update Result Structures

#### Task 11: Simplify AgentResult metadata
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`
**Location**: Lines 14-22

Document the intended change but DO NOT implement yet:
```python
# TODO: After RunAnalytics migration, simplify metadata to:
# metadata: dict[str, object]  # Only: output_file, word_count
# Remove: message_count, search_count, duration (moved to RunAnalytics)
```

### Phase 6: Implement Output Methods

#### Task 12: Add file writing methods to RunAnalytics
**File**: `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/run_analytics.py`
**Location**: Add to RunAnalytics class

```python
    def _write_message_log(self, message: object, agent_name: str, 
                          iteration: int, artifacts: dict) -> None:
        """Write message and artifacts to JSONL file."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "agent": agent_name,
            "iteration": iteration,
            "message_index": self.global_message_count,
            "message_type": type(message).__name__,
            "artifacts": artifacts,
            "message": self._serialize_message(message)
        }
        
        try:
            with open(self.messages_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write message log: {e}")
    
    def _serialize_message(self, message: object, max_length: int = 1000) -> dict:
        """Serialize SDK message for logging (reuse from MessageProcessor)."""
        # Copy implementation from MessageProcessor._serialize_message
        # This maintains consistency during migration
        pass  # Implementation from MessageProcessor
    
    def finalize(self) -> None:
        """Write final run summary when pipeline completes."""
        summary = {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "global_stats": {
                "total_messages": self.global_message_count,
                "total_tool_uses": self.global_tool_count,
            },
            "agent_metrics": {
                f"{name}_{iter}": asdict(metrics)
                for (name, iter), metrics in self.agent_metrics.items()
            }
        }
        
        summary_file = self.output_dir / f"{self.run_id}_run_summary.json"
        try:
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Run summary written to {summary_file}")
        except Exception as e:
            logger.error(f"Failed to write run summary: {e}")
```

**Warnings**:
- File I/O should be non-blocking if possible
- Handle datetime serialization with default=str

### Phase 7: Testing

#### Task 13: Create unit tests for RunAnalytics
**File**: Create `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_run_analytics.py`

```python
"""Unit tests for RunAnalytics."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from src.core.run_analytics import RunAnalytics, AgentMetrics
from claude_code_sdk.types import (
    SystemMessage, UserMessage, AssistantMessage,
    ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock
)


@pytest.fixture
def analytics(tmp_path):
    """Create RunAnalytics instance for testing."""
    return RunAnalytics("test_run_123", tmp_path)


class TestRunAnalytics:
    """Test RunAnalytics core functionality."""
    
    def test_initialization(self, analytics, tmp_path):
        """Test RunAnalytics initialization."""
        assert analytics.run_id == "test_run_123"
        assert analytics.output_dir == tmp_path
        assert analytics.global_message_count == 0
        assert analytics.global_tool_count == 0
    
    def test_track_system_message(self, analytics):
        """Test tracking SystemMessage with session_id."""
        message = Mock(spec=SystemMessage)
        message.data = {"session_id": "session-456"}
        message.subtype = "start"
        
        analytics.track_message(message, "analyst", 0)
        
        metrics = analytics.agent_metrics[("analyst", 0)]
        assert metrics.session_id == "session-456"
        assert metrics.message_count == 1
    
    def test_track_tool_use(self, analytics):
        """Test tracking ToolUseBlock for WebSearch."""
        message = Mock(spec=AssistantMessage)
        tool_block = Mock(spec=ToolUseBlock)
        tool_block.id = "tool_123"
        tool_block.name = "WebSearch"
        tool_block.input = {"query": "market analysis"}
        message.content = [tool_block]
        
        analytics.track_message(message, "analyst", 0)
        
        metrics = analytics.agent_metrics[("analyst", 0)]
        assert metrics.tool_uses["WebSearch"] == 1
        assert "market analysis" in metrics.search_queries
        assert analytics.global_tool_count == 1
    
    def test_finalize_writes_summary(self, analytics, tmp_path):
        """Test that finalize writes run summary."""
        # Track some messages
        message = Mock(spec=UserMessage)
        message.content = "Test content"
        analytics.track_message(message, "analyst", 0)
        
        # Finalize
        analytics.finalize()
        
        # Check summary file exists
        summary_file = tmp_path / "test_run_123_run_summary.json"
        assert summary_file.exists()
        
        # Verify content structure
        import json
        with open(summary_file) as f:
            summary = json.load(f)
        
        assert summary["run_id"] == "test_run_123"
        assert "global_stats" in summary
        assert summary["global_stats"]["total_messages"] == 1
```

#### Task 14: Update affected existing tests
**File**: Various test files
**Changes needed**:

1. Tests that import MessageProcessor - add compatibility imports
2. Tests that check AgentResult.metadata fields - update expectations after Phase 5
3. Integration tests - ensure they pass RunAnalytics in context when needed

### Phase 8: Migration and Cleanup

#### Task 15: Test parallel operation
Run system with both MessageProcessor and RunAnalytics active to ensure compatibility:
```bash
# Run with debug mode to test both systems
LOG_LEVEL=DEBUG python -m src.cli analyze "test idea" --debug
```

Verify:
- Old messages.jsonl format still works (from MessageProcessor)
- New messages.jsonl has enhanced format (from RunAnalytics)
- No errors or conflicts

#### Task 16: Remove MessageProcessor dependencies
**Files to update** (only after confirming RunAnalytics works):

1. `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py` - Remove MessageProcessor import and fallback code
2. `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py` - Remove MessageProcessor import and fallback code
3. `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py` - Update AgentResult.metadata structure
4. Update any documentation referencing MessageProcessor

#### Task 17: Delete MessageProcessor and its tests
**Files to delete** (only after all updates complete):
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/message_processor.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_message_processor.py`

**Before deleting**:
```bash
# Archive the files for reference
cp src/core/message_processor.py archive/refactoring/message_processor_final.py
cp tests/unit/test_message_processor.py archive/refactoring/test_message_processor_final.py
```

## Verification Steps

After completing all tasks:

1. **Unit Tests Pass**:
   ```bash
   python -m pytest tests/unit/test_run_analytics.py -v
   python -m pytest tests/unit/ -v  # All unit tests
   ```

2. **Integration Tests Pass**:
   ```bash
   python -m pytest tests/integration/ -v
   ```

3. **Manual Testing**:
   ```bash
   # Test basic analysis
   python -m src.cli analyze "AI-powered fitness app"
   
   # Test with reviewer loop
   python -m src.cli analyze "AI-powered fitness app" --max-iterations 2
   
   # Verify output files
   ls logs/runs/*_messages.jsonl
   ls logs/runs/*_run_summary.json
   ```

4. **Output Validation**:
   - Check messages.jsonl has artifact extraction
   - Verify run_summary.json has complete metrics
   - Ensure no data loss from old MessageProcessor

5. **Performance Check**:
   - Measure overhead of new tracking
   - Ensure no significant slowdown

## Potential Risks

### Risk 1: ThinkingBlock Not Available
**Issue**: ThinkingBlock type may not exist in current SDK version
**Mitigation**: 
- Use conditional import with try/except
- Add type checking before instanceof checks
- Document for future SDK update

### Risk 2: Async/Thread Safety
**Issue**: File I/O in async context could cause issues
**Mitigation**:
- Use thread-safe write operations
- Consider buffering writes
- Add proper exception handling

### Risk 3: Large Message Volumes
**Issue**: High message volume could create large JSONL files
**Mitigation**:
- Implement log rotation if file exceeds size limit
- Add compression option for archived logs
- Consider sampling for very long runs

### Risk 4: Backward Compatibility Break
**Issue**: Existing tools parsing old format might break
**Mitigation**:
- Maintain dual output during transition
- Document format changes clearly
- Provide migration script if needed

### Risk 5: Memory Growth
**Issue**: Keeping all metrics in memory could cause issues for long runs
**Mitigation**:
- Implement periodic flush to disk
- Add memory limits and warnings
- Consider streaming aggregation

## Rollback Strategy

If critical issues arise:

1. **Immediate Rollback** (< 5 minutes):
   ```bash
   git stash  # Save any uncommitted changes
   git checkout main
   ```

2. **Partial Rollback** (keep some improvements):
   - Keep RunAnalytics class but disable in pipeline
   - Revert agents to use MessageProcessor
   - Cherry-pick non-breaking improvements

3. **Data Recovery**:
   - Old MessageProcessor logs remain readable
   - No data loss as both systems can coexist
   - Archive new format files for debugging

## Success Criteria

The refactoring is complete when:

1. ✅ All tests pass (unit and integration)
2. ✅ RunAnalytics tracks all message types with artifacts
3. ✅ Output files (messages.jsonl, run_summary.json) are created correctly
4. ✅ Pipeline uses RunAnalytics exclusively (no MessageProcessor)
5. ✅ Performance is comparable or better than before
6. ✅ Documentation is updated
7. ✅ MessageProcessor is safely removed
8. ✅ No regressions in functionality

## Notes

- **Parallel Development**: RunAnalytics can coexist with MessageProcessor during migration
- **Incremental Rollout**: Can enable per-agent or per-run via context flag
- **Future Enhancements**: Architecture supports adding new metrics without breaking changes
- **Observability**: New system provides much richer data for optimization

---

*End of Refactoring Task List*
