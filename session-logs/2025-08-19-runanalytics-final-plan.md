# RunAnalytics Implementation Plan - Final Consolidated Version

## Executive Summary

Complete refactoring of MessageProcessor into RunAnalytics - a comprehensive analytics engine for multi-agent pipeline runs. This consolidated plan merges the architectural design with detailed implementation tasks.

## Core Architecture Decisions

1. **Class Name**: `RunAnalytics` (replaces MessageProcessor entirely)
2. **Architecture**: Single class with clean internal methods
3. **File Ownership**:
   - `stdout.log`: Owned by logger.py (unchanged)
   - `messages.jsonl`: Owned by RunAnalytics (enhanced format)
   - `run_summary.json`: Owned by RunAnalytics (new)
4. **Integration**: Via BaseContext field, created by pipeline
5. **Block Support**: TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock

## Implementation Phases

### Phase 1: Core RunAnalytics Class (Tasks 1-3)

**Create**: `src/core/run_analytics.py`

Key components:

- `AgentMetrics` dataclass for per-agent tracking
- `RunAnalytics` class with message tracking and artifact extraction
- Full block type support including ThinkingBlock
- Tool correlation via tool_use_id mapping
- WebSearch result link extraction via regex

**Critical Details**:

- Thread-safe file I/O operations
- Handle ThinkingBlock even if unused by agents
- Correlate ToolUseBlock with ToolResultBlock via tool_use_id

### Phase 2: Configuration Integration (Task 4)

**Modify**: `src/core/config.py`

Add to BaseContext:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.run_analytics import RunAnalytics

@dataclass
class BaseContext:
    # ... existing fields ...
    run_analytics: "RunAnalytics | None" = None  # Forward reference to avoid circular import
```

**Critical**: Must use TYPE_CHECKING to avoid actual circular import at runtime

### Phase 3: Agent Updates (Tasks 5-7)

**Modify**: `src/agents/analyst.py` and `src/agents/reviewer.py`

**Problem Found**: Agents still need to extract content from ResultMessage for their return value. RunAnalytics tracks but doesn't replace this functionality.

**Solution**: Keep minimal extraction logic in agents:

```python
# In _run_analysis method
async for message in client.receive_response():
    # Track with RunAnalytics
    if context.run_analytics:
        context.run_analytics.track_message(message, "analyst", iteration)
    
    # Still need to check for ResultMessage to get content
    if isinstance(message, ResultMessage):
        # Extract content for agent's return value
        content = message.result if message.result else ""
        if content:
            return AnalysisResult(content=content, ...)
```

**Key Insight**: Messages come from `client.receive_response()` in SDK stream

### Phase 4: Pipeline Integration (Tasks 8-10)

**Modify**: `src/core/pipeline.py`

Pipeline responsibilities:

- Create RunAnalytics instance with run_id and log directory
- Pass via context to all agents
- Call `run_analytics.finalize()` at pipeline end (in finally block)

**Critical Addition**: Must get log directory properly:

```python
# Get log directory from logger setup
from pathlib import Path
import logging

log_dir = Path("logs/runs")  # Default
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler):
        log_dir = Path(handler.baseFilename).parent
        break

run_analytics = RunAnalytics(run_id=run_id, output_dir=log_dir)
```

### Phase 5: Result Structure Cleanup (Task 11)

**Modify**: `src/core/agent_base.py`

Simplify AgentResult.metadata to minimum:

- Keep: `output_file`, `word_count` (needed for validation)
- Remove: `message_count`, `search_count`, `duration` (moved to RunAnalytics)

### Phase 6: Output Methods (Task 12)

Implement in RunAnalytics:

- `_write_message_log()`: Append to messages.jsonl with artifacts
- `_serialize_message()`: Truncate messages for storage
- `finalize()`: Write run_summary.json with aggregated metrics

### Phase 7: Testing (Tasks 13-14)

**Create**: `tests/unit/test_run_analytics.py`

Test coverage:

- Message tracking for all types
- Artifact extraction accuracy
- Tool correlation logic
- File output generation
- ThinkingBlock handling

### Phase 8: Migration & Cleanup (Tasks 15-17)

**Modified Approach**: No parallel operation - too complex and error-prone

1. ~~Test parallel operation (both systems active)~~ Skip - direct migration instead
2. Complete migration in one go (all agents at once)
3. Run comprehensive tests before deletion
4. Archive and delete MessageProcessor files only after full validation

## Risk Mitigation

### Technical Risks

1. **Thread Safety**
   - Solution: Proper async file I/O, exception handling

2. **Memory Growth**
   - Solution: Periodic flush, streaming aggregation for long runs

3. **WebSearch Result Parsing**
   - Solution: Robust regex with fallback, comprehensive error handling

### Migration Risks

1. **Backward Compatibility**
   - Solution: Support both systems during transition
   - Fallback code in agents until fully migrated

2. **Data Format Changes**
   - Solution: Document format changes
   - Maintain dual output if needed

## Verification Checklist

### Pre-Implementation

- [ ] Create feature branch: `git checkout -b refactor/runanalytics`
- [ ] Run baseline tests: `pytest tests/unit/test_message_processor.py`
- [ ] Review full proposal and task list

### During Implementation

- [ ] Each phase has unit tests passing
- [ ] No regressions in existing functionality
- [ ] Output files generated correctly
- [ ] Performance comparable or better

### Post-Implementation

- [ ] All tests pass (unit and integration)
- [ ] Manual testing with real ideas
- [ ] Both simple and reviewer pipeline flows work
- [ ] ThinkingBlock tracked even if unused
- [ ] Tool correlations working
- [ ] MessageProcessor safely removed

## File Change Summary

### Files to Create

- `src/core/run_analytics.py` - New analytics engine
- `tests/unit/test_run_analytics.py` - Unit tests

### Files to Modify

- `src/core/config.py` - Add run_analytics to BaseContext
- `src/agents/analyst.py` - Use RunAnalytics
- `src/agents/reviewer.py` - Use RunAnalytics  
- `src/core/pipeline.py` - Create and manage RunAnalytics
- `src/core/agent_base.py` - Simplify AgentResult.metadata

### Files to Delete (Phase 8)

- `src/core/message_processor.py` - After migration
- `tests/unit/test_message_processor.py` - After migration

## Success Metrics

1. **Functional**: All existing features work without regression
2. **Performance**: No significant slowdown (< 5% overhead)
3. **Data Quality**: Rich artifacts extracted from all message types
4. **Output Files**: All three files generated with correct format
5. **Code Quality**: Clean separation of concerns maintained

## Implementation Order

1. **Start**: Create RunAnalytics class with core methods
2. **Integrate**: Update BaseContext and pipeline
3. **Migrate Agents**: Update analyst and reviewer to use RunAnalytics
4. **Test**: Comprehensive unit and integration testing
5. **Cleanup**: Remove MessageProcessor after verification

## Notes for Implementation

- RunAnalytics completely replaces MessageProcessor (not extends)
- Use existing utils where applicable (json_validator, text_processing)
- Coordinate with logger.py for paths only
- ThinkingBlock support is forward-looking (not currently used)
- Tool correlation is critical for search result tracking
- File I/O must be robust with proper error handling

## Critical Corrections Made

1. **Import Cycles**: Added TYPE_CHECKING pattern for BaseContext to avoid runtime circular imports
2. **Agent Logic**: Clarified that agents still need ResultMessage extraction for return values
3. **Log Directory**: Added proper code to get log directory from logger handlers
4. **Migration Strategy**: Removed parallel operation - direct migration is cleaner
5. **Pipeline Finalization**: Emphasized finalize() must be in finally block

## Implementation Starting Point

Begin with Phase 1, but create a minimal working version first:

1. Basic RunAnalytics class with just message counting
2. Test with one agent before full implementation
3. Add artifact extraction incrementally
4. This allows early validation of the architecture

## Implementation Todo List

### Phase 1: Core RunAnalytics Class

- [ ] Create `src/core/run_analytics.py` with basic structure
- [ ] Implement `AgentMetrics` dataclass
- [ ] Implement `RunAnalytics.__init__()` method
- [ ] Implement `track_message()` with basic counting
- [ ] Add `_extract_system_artifacts()` for SystemMessage
- [ ] Add `_extract_content_artifacts()` for User/AssistantMessage
- [ ] Add `_extract_block_artifacts()` with all block types (including ThinkingBlock)
- [ ] Add `_extract_result_artifacts()` for ResultMessage
- [ ] Implement tool correlation tracking (tool_use_id mapping)
- [ ] Add WebSearch result link extraction with regex

### Phase 2: Configuration Integration

- [ ] Add TYPE_CHECKING import to `src/core/config.py`
- [ ] Add `run_analytics` field to BaseContext
- [ ] Verify no circular import issues

### Phase 3: Agent Updates

- [ ] Update `src/agents/analyst.py` imports
- [ ] Modify analyst's `_run_analysis()` to use RunAnalytics
- [ ] Keep ResultMessage content extraction for return value
- [ ] Update `src/agents/reviewer.py` similarly
- [ ] Remove all MessageProcessor usage

### Phase 4: Pipeline Integration

- [ ] Import RunAnalytics in `src/core/pipeline.py`
- [ ] Add log directory retrieval logic
- [ ] Create RunAnalytics instance in `run_analyst_reviewer_loop()`
- [ ] Pass RunAnalytics via context to agents
- [ ] Add `run_analytics.finalize()` in finally block
- [ ] Update SimplePipeline similarly

### Phase 5: Result Structure Cleanup

- [ ] Document planned changes to AgentResult.metadata
- [ ] Remove `message_count`, `search_count`, `duration` from metadata
- [ ] Keep only `output_file` and `word_count`

### Phase 6: Output Methods

- [ ] Implement `_write_message_log()` for messages.jsonl
- [ ] Implement `_serialize_message()` with truncation
- [ ] Implement `finalize()` to write run_summary.json
- [ ] Add proper error handling for all file I/O

### Phase 7: Testing

- [ ] Create `tests/unit/test_run_analytics.py`
- [ ] Test initialization and basic tracking
- [ ] Test all message type extractions
- [ ] Test ThinkingBlock handling specifically
- [ ] Test tool correlation logic
- [ ] Test WebSearch result extraction
- [ ] Test file output generation
- [ ] Update existing tests that use MessageProcessor

### Phase 8: Migration & Cleanup

- [ ] Run full test suite with RunAnalytics
- [ ] Manual test with simple idea
- [ ] Manual test with reviewer pipeline
- [ ] Verify all three output files generated correctly
- [ ] Archive MessageProcessor files
- [ ] Delete `src/core/message_processor.py`
- [ ] Delete `tests/unit/test_message_processor.py`
- [ ] Update any remaining references in docs

### Final Validation

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Manual smoke test successful
- [ ] Output files have correct format
- [ ] No performance regression
- [ ] Code review completed

---

*This is the final consolidated plan ready for implementation. Begin with Phase 1: Creating the RunAnalytics class.*
