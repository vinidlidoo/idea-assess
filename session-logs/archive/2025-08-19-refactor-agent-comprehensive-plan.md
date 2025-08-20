# Comprehensive Agent Refactoring Task List

**Created:** 2025-08-19T10:00:00Z
**Author:** Python Refactor Planner
**Target:** analyst.py and reviewer.py refactoring with BaseAgent enhancements

## Executive Summary

This refactoring plan addresses structural inefficiencies, code quality issues, and design patterns in the analyst and reviewer agents. The refactoring will be executed in 4 phases with incremental, testable changes that maintain backward compatibility.

## Scope

### Files to be Modified

- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/utils/file_operations.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/config/prompts/agents/analyst/partials/websearch_instruction.md` (new)

### Impact Analysis

#### Direct Dependencies
- `src/cli.py` - Uses AnalystAgent and ReviewerAgent
- `src/analyze.py` - Wrapper that calls AnalystAgent
- `tests/test_analyst.py` - Unit tests for AnalystAgent
- `tests/test_reviewer.py` - Unit tests for ReviewerAgent

#### Indirect Dependencies
- `src/core/config.py` - Defines AnalystConfig, ReviewerConfig
- `src/core/types.py` - Defines FeedbackDict
- `src/utils/text_processing.py` - Provides create_slug()
- `src/utils/json_validator.py` - Provides FeedbackValidator
- `src/utils/logger.py` - Provides is_sdk_error()

## Prerequisites

1. **Backup Current State**
   ```bash
   git add -A
   git commit -m "chore: Backup before agent refactoring"
   ```

2. **Verify Test Suite**
   ```bash
   python -m pytest tests/test_analyst.py tests/test_reviewer.py -v
   ```

3. **Document Current Behavior**
   - Record current test output
   - Note any existing warnings or deprecations

## Task List

### Phase 1: Simplify Analyst Structure (Priority: HIGH)

#### Task 1.1: Reorganize Imports
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

- Move line 276 import to top: `from claude_code_sdk.types import ResultMessage`
- Move line 322 import to top: `from ..utils.logger import is_sdk_error`
- Group imports by category (standard lib, third-party, local)

**Verification:** Code should still import correctly

#### Task 1.2: Merge _analyze_idea() into process()
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

1. Copy entire body of `_analyze_idea()` (lines 116-354) into `process()` after line 78
2. Remove the intermediate `_analyze_idea()` call at lines 81-87
3. Remove the separate `_analyze_idea()` method definition
4. Update variable names:
   - Change `idea` parameter references to `input_data`
   - Remove redundant parameter passing
5. Simplify the return statement to directly create AgentResult without AnalysisResult

**Before (simplified):**
```python
async def process(self, input_data: str, context: AnalystContext) -> AgentResult:
    result = await self._analyze_idea(idea=input_data, ...)
    if result:
        return AgentResult(content=result.content, ...)
```

**After (simplified):**
```python
async def process(self, input_data: str, context: AnalystContext) -> AgentResult:
    # Direct implementation here
    # ...processing logic...
    return AgentResult(content=content, metadata={...}, success=True)
```

**Verification:** Run analyst tests to ensure functionality preserved

#### Task 1.3: Eliminate AnalysisResult Dependency
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

1. Remove import: `from ..utils.file_operations import AnalysisResult`
2. At line ~290 (after merge), replace AnalysisResult creation with direct AgentResult:
   ```python
   # Old
   return AnalysisResult(content=content, idea=idea, slug=create_slug(idea), ...)
   
   # New
   return AgentResult(
       content=content,
       metadata={
           "idea": input_data,
           "slug": create_slug(input_data),
           "timestamp": datetime.now().isoformat(),
           "interrupted": self.interrupt_event.is_set()
       },
       success=True
   )
   ```

**Verification:** Ensure slug generation still works correctly

#### Task 1.4: Clean Up Logging and Error Handling
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

1. Replace all `print()` statements with logger calls:
   - Line ~162: `print("\n[ANALYST] Interrupt received...")` → `logger.warning("Interrupt received, attempting graceful shutdown...")`
   - Line ~302: `print("[ANALYST] ERROR: No analysis generated...")` → `logger.error("No analysis generated (no ResultMessage received)")`
   - Line ~311: `print(f"\n[ANALYST] WARNING: {e}")` → `logger.warning(f"Analysis interrupted: {e}")`
   - Line ~319: `print(f"[ANALYST] ERROR: {error_msg}")` → `logger.error(error_msg)`

2. Consolidate error handling into single except block with proper logging

**Verification:** Check logs are properly formatted

#### Task 1.5: Extract WebSearch Instructions to Prompt File
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/config/prompts/agents/analyst/partials/websearch_instruction.md` (NEW)

1. Create new file with content:
   ```markdown
   {%- if use_websearch -%}
   Use WebSearch efficiently (maximum {{ max_websearches }} searches) to gather the most critical data: recent market size, key competitor metrics, and major trends.
   {%- else -%}
   Note: WebSearch is disabled for this analysis. Use your existing knowledge.
   {%- endif -%}
   ```

2. Update analyst.py to load this template instead of inline text (lines ~180-187)

**Verification:** Ensure prompts load correctly

#### Task 1.6: Simplify Variable Assignments
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

1. Remove redundant variable at line ~227: `tools_to_use = allowed_tools if (use_websearch and allowed_tools) else []`
   - Use directly in ClaudeCodeOptions
2. Remove redundant assignment at line ~242-243: `client = client_instance`
   - Use `client` directly in async with statement

**Verification:** Code should be cleaner without functional changes

### Phase 2: Streamline Reviewer Logic (Priority: HIGH)

#### Task 2.1: Extract Path Validation to Utils
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/utils/file_operations.py`

1. Add new function:
   ```python
   def validate_analysis_path(file_path: str | Path, analyses_dir: Path | None = None) -> Path:
       """Validate that path is within analyses directory."""
       path = Path(file_path).resolve()
       
       if analyses_dir is None:
           project_root = Path(__file__).parent.parent.parent
           analyses_dir = (project_root / "analyses").resolve()
       
       try:
           _ = path.relative_to(analyses_dir)
       except (ValueError, TypeError) as e:
           raise ValueError("Invalid path: must be within analyses directory") from e
       
       if not path.exists():
           raise FileNotFoundError(f"Analysis file not found: {path}")
       
       return path
   ```

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`

2. Replace `_validate_analysis_path()` method (lines 47-80) with import and call to util function

**Verification:** Path validation should work identically

#### Task 2.2: Simplify Metadata Extraction
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`

1. Create helper method for metadata building:
   ```python
   def _build_feedback_metadata(self, feedback: dict, iteration: int) -> dict:
       """Build standardized metadata from feedback."""
       return {
           "iteration": iteration,
           "feedback_file": str(self.feedback_file),
           "recommendation": feedback.get("iteration_recommendation", "unknown"),
           "critical_issues_count": len(feedback.get("critical_issues", [])) if isinstance(feedback.get("critical_issues"), list) else 0,
           "improvements_count": len(feedback.get("improvements", [])) if isinstance(feedback.get("improvements"), list) else 0,
           "minor_suggestions_count": len(feedback.get("minor_suggestions", [])) if isinstance(feedback.get("minor_suggestions"), list) else 0,
       }
   ```

2. Replace duplicate metadata extraction at lines 256-271 with call to helper

**Verification:** Metadata should be identical

#### Task 2.3: Consolidate Feedback Validation
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`

1. Create single validation method:
   ```python
   def _validate_and_fix_feedback(self, feedback_json: dict, feedback_file: Path) -> tuple[bool, str | None]:
       """Validate feedback and attempt fixes if needed."""
       validator = FeedbackValidator()
       is_valid, error_msg = validator.validate(feedback_json)
       
       if not is_valid:
           logger.warning(f"Feedback validation failed: {error_msg}, attempting fix")
           feedback_json = validator.fix_common_issues(feedback_json)
           is_valid, error_msg = validator.validate(feedback_json)
           
           if is_valid:
               with open(feedback_file, "w") as f:
                   json.dump(feedback_json, f, indent=2)
               logger.info(f"Feedback fixed and saved to {feedback_file}")
       
       return is_valid, error_msg
   ```

2. Replace validation logic at lines 201-230 with call to helper

**Verification:** Validation behavior unchanged

#### Task 2.4: Move FeedbackProcessor to Separate Module
**Decision Point:** Based on usage analysis, FeedbackProcessor should remain in reviewer.py but be moved to top of file after imports

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`

1. Move FeedbackProcessor class (lines 297-416) to after imports (around line 21)
2. Add docstring explaining its role in the review process

**Verification:** Import order and functionality preserved

### Phase 3: Extract Common Patterns to BaseAgent (Priority: MEDIUM)

#### Task 3.1: Move Interrupt Handling to BaseAgent
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`

1. Add interrupt handling methods:
   ```python
   def setup_interrupt_handler(self) -> object:
       """Setup interrupt signal handler."""
       import signal
       import sys
       
       def handle_interrupt(signum: int, frame: object) -> None:
           self.interrupt_event.set()
           logger = logging.getLogger(self.__class__.__name__)
           logger.warning("Interrupt received, attempting graceful shutdown...")
       
       original_handler = signal.getsignal(signal.SIGINT)
       signal.signal(signal.SIGINT, handle_interrupt)
       return original_handler
   
   def restore_interrupt_handler(self, original_handler: object) -> None:
       """Restore original interrupt handler."""
       import signal
       signal.signal(signal.SIGINT, original_handler)
   
   def check_interrupt(self) -> None:
       """Check if interrupt was triggered."""
       if self.interrupt_event.is_set():
           raise InterruptedError(f"{self.agent_name} interrupted by user")
   ```

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

2. Replace interrupt handling code (lines ~153-172) with:
   ```python
   original_handler = self.setup_interrupt_handler()
   try:
       # ... main logic ...
   finally:
       self.restore_interrupt_handler(original_handler)
   ```

3. Replace interrupt checks with: `self.check_interrupt()`

**Verification:** Interrupt handling should work identically

#### Task 3.2: Add Standard SDK Client Setup
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`

1. Add helper method:
   ```python
   def create_sdk_options(
       self,
       system_prompt: str,
       max_turns: int | None = None,
       allowed_tools: list[str] | None = None,
       permission_mode: str = "default"
   ) -> ClaudeCodeOptions:
       """Create standard SDK options."""
       from claude_code_sdk import ClaudeCodeOptions
       
       return ClaudeCodeOptions(
           system_prompt=system_prompt,
           max_turns=max_turns or self.get_max_turns(),
           allowed_tools=allowed_tools or [],
           permission_mode=permission_mode
       )
   ```

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`

2. Update both agents to use `self.create_sdk_options()` instead of manual creation

**Verification:** SDK options should be identical

#### Task 3.3: Standardize RunAnalytics Integration
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`

1. Add tracking helper:
   ```python
   def track_message(
       self,
       message: object,
       context: TContext,
       iteration: int = 0
   ) -> tuple[int, int]:
       """Track message with RunAnalytics if available."""
       if hasattr(context, 'run_analytics') and context.run_analytics:
           context.run_analytics.track_message(message, self.agent_name.lower(), iteration)
           return (
               context.run_analytics.global_message_count,
               context.run_analytics.global_search_count
           )
       return (0, 0)
   ```

2. Update both agents to use this helper method

**Verification:** Tracking should work identically

### Phase 4: Final Cleanup and Optimization (Priority: LOW)

#### Task 4.1: Standardize Context Extraction
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`

1. Simplify revision context extraction (lines 65-77):
   ```python
   revision_context = None
   if context.revision_context:
       rc = context.revision_context
       revision_context = {
           "previous_analysis_file": str(rc.previous_analysis_path) if rc.previous_analysis_path else "",
           "feedback_file": str(rc.feedback_path) if rc.feedback_path else "",
       }
   ```

**Verification:** Context extraction works correctly

#### Task 4.2: Create Agent-Specific Exception Types
**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/exceptions.py` (NEW)

1. Create new file with:
   ```python
   """Agent-specific exceptions."""
   
   class AgentError(Exception):
       """Base exception for agent errors."""
       pass
   
   class AnalysisInterrupted(AgentError):
       """Raised when analysis is interrupted by user."""
       pass
   
   class ReviewError(AgentError):
       """Raised when review process fails."""
       pass
   
   class ValidationError(AgentError):
       """Raised when validation fails."""
       pass
   ```

2. Update imports in both agents to use centralized exceptions

**Verification:** Exception handling unchanged

#### Task 4.3: Add Type Hints for Better IDE Support
**Files:** Both agents

1. Add missing type hints to all methods
2. Use proper return type annotations
3. Add docstrings where missing

**Verification:** Type checking should pass

#### Task 4.4: Remove Redundant Comments and Code
**Files:** Both agents

1. Remove redundant comments marked with "redundant" in code
2. Remove empty `finally: pass` blocks
3. Clean up excessive blank lines
4. Remove unused imports after refactoring

**Verification:** Code should be cleaner

## Verification Steps

After each phase, run:

1. **Unit Tests**
   ```bash
   python -m pytest tests/test_analyst.py tests/test_reviewer.py -v
   ```

2. **Integration Test**
   ```bash
   python -m src.cli analyze "Test idea for refactoring validation"
   ```

3. **Type Checking**
   ```bash
   mypy src/agents/analyst.py src/agents/reviewer.py
   ```

4. **Code Quality**
   ```bash
   ruff check src/agents/
   ```

## Potential Risks

### High Risk
1. **Breaking API Changes** - Ensure process() method signature unchanged
2. **Import Cycles** - Watch for circular imports when moving utilities
3. **Context Loss** - Ensure all context data properly passed through refactoring

### Medium Risk
1. **Test Coverage** - Some edge cases might not be covered by existing tests
2. **Performance** - New abstractions might add slight overhead
3. **Logging Changes** - Different log formats might affect monitoring

### Low Risk
1. **Code Style** - Minor formatting differences
2. **Comment Loss** - Some inline documentation might be removed

## Rollback Strategy

If issues arise at any phase:

1. **Immediate Rollback**
   ```bash
   git stash  # Save current work
   git checkout HEAD~1  # Return to backup commit
   ```

2. **Selective Rollback**
   ```bash
   git checkout HEAD -- src/agents/analyst.py  # Revert specific file
   ```

3. **Incremental Fix**
   - Identify failing test
   - Minimal fix to restore functionality
   - Continue with adjusted plan

## Success Metrics

1. **All tests passing** - 100% of existing tests must pass
2. **No new warnings** - Ruff and mypy should show no new issues
3. **Performance maintained** - Analysis time should not increase by >5%
4. **Code reduction** - At least 10% reduction in lines of code
5. **Improved maintainability** - Reduced cyclomatic complexity

## Additional Recommendations

### Not in Original Plan but Recommended

1. **Add Retry Logic for SDK Calls**
   - Implement exponential backoff for transient failures
   - Add to BaseAgent as reusable pattern

2. **Create Message Buffer Interface**
   - Abstract message accumulation pattern
   - Useful for future agents

3. **Implement Proper Async Context Managers**
   - Better resource cleanup
   - Prevent resource leaks

4. **Add Telemetry Hooks**
   - Prepare for production monitoring
   - Performance tracking infrastructure

5. **Consider Strategy Pattern for Tools**
   - Make tool selection more flexible
   - Easier to add new tools later

### Patterns to Extract to BaseAgent

**Should Extract:**
- Interrupt handling (safety-critical, common)
- SDK client creation (standardization)
- Message tracking (consistency)
- Basic error handling (SDK errors)
- Prompt loading (already there)

**Should Keep Agent-Specific:**
- Business logic (analysis, review logic)
- Output formatting (markdown, JSON)
- Validation rules (what makes good analysis/feedback)
- Tool-specific logic (WebSearch usage patterns)
- Agent-specific prompts and templates

### Configuration Recommendations

1. **Move Magic Numbers to Config**
   - Message log intervals
   - Retry counts and delays
   - Buffer sizes

2. **Environment-Based Config**
   - Development vs. production settings
   - Debug logging toggles

3. **Feature Flags**
   - Enable/disable interrupt handling
   - Toggle analytics tracking

---

*Next Steps: Begin with Phase 1, Task 1.1 - Reorganize imports in analyst.py*
