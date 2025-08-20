# Pipeline.py Refactoring Plan

**Created**: 2025-08-20 10:00:00 PST  
**Target File**: src/core/pipeline.py  
**Purpose**: Comprehensive refactoring to fix business logic issues, improve type safety, and enhance maintainability

## Scope

Refactoring the `AnalysisPipeline` class and related components to address:

- Critical iteration logic flaws (max_iterations=1 wastes reviewer resources)
- Type safety issues (16 basedpyright warnings with Any types)
- God method complexity (run_analyst_reviewer_loop is 350+ lines)
- File management chaos (inconsistent naming, multiple creation points)
- Poor error handling (generic exceptions, lost context)
- Awkward RunAnalytics integration

## Impact Analysis

### Affected Components

**Direct Dependencies**:
- `src/core/pipeline.py` - Main refactoring target
- `src/core/types.py` - Need to enhance TypedDicts for feedback
- `src/cli.py` - Uses pipeline, must maintain compatibility
- `src/analyze.py` - Thin wrapper using pipeline

**Test Files**:
- `tests/unit/test_pipeline.py` - Will need updates for new logic
- `tests/integration/test_analyst_reviewer_flow.py` - May need iteration count adjustments

**Configuration References**:
- `config/prompts/agents/analyst/revision.md` - Referenced in revision flow
- `config/prompts/agents/reviewer/main.md` - Used by reviewer

**Import Chain**:
- `src/cli.py` → imports `AnalysisPipeline`
- `src/analyze.py` → imports `AnalysisPipeline`, `SimplePipeline`

## Task List

### Phase 1: Type Safety Foundation (Priority: CRITICAL)

#### Task 1.1: Enhance Type Definitions
**File**: `src/core/types.py`
**Changes**:
```python
# Add after line 41:
class IterationResult(TypedDict):
    """Result from a single iteration."""
    iteration: int
    analysis_file: str
    analysis_length: int
    feedback_file: str | None
    metadata: dict[str, object]

class PipelineContext(TypedDict):
    """Context passed through pipeline execution."""
    run_id: str
    slug: str
    idea: str
    analysis_dir: Path
    iterations_dir: Path
    max_iterations: int
    use_websearch: bool
    tools_override: list[str] | None
```
**Warnings**: Ensure all existing TypedDicts remain unchanged for compatibility

#### Task 1.2: Fix Feedback Type Usage
**File**: `src/core/pipeline.py`
**Changes**:
- Line 215: Change `feedback_history: list[dict[str, object]] = []` to `feedback_history: list[FeedbackDict] = []`
- Line 216: Change `iteration_results: list[dict[str, object]] = []` to `iteration_results: list[IterationResult] = []`
- Line 377: Change `feedback = json.load(f)` to `feedback: FeedbackDict = json.load(f)`
- Line 378: Remove the cast, change to `feedback_history.append(feedback)`
- Import FeedbackDict and IterationResult from types at top

#### Task 1.3: Fix Any Type Warnings
**File**: `src/core/pipeline.py`
**Changes**:
- Lines 390-391: Add type annotation before accessing dict
- Lines 403, 414-415: Type feedback as FeedbackDict before accessing
- Line 529: Fix locals().get() type annotation

### Phase 2: Iteration Logic Fix (Priority: CRITICAL)

#### Task 2.1: Document New Iteration Semantics
**File**: `src/core/pipeline.py`
**Changes**:
Add docstring update at line 167:
```python
"""
Run the analyst-reviewer feedback loop using file-based communication.

Iteration Semantics:
- max_iterations=1: Analyst only (no review)
- max_iterations=2: Analyst → Review → Revise once
- max_iterations=3: Analyst → Review → Revise → Review → Revise again
- etc.

The reviewer is ONLY invoked if there will be an opportunity to revise.
"""
```

#### Task 2.2: Implement Skip-Review-On-Last-Iteration Logic
**File**: `src/core/pipeline.py`
**Changes**:
- After line 341 (after iteration_results.append), add:
```python
# Skip reviewer if this is the last iteration (no chance to revise)
if iteration_count >= max_iterations:
    logger.info(f"Skipping review on final iteration {iteration_count}")
    break
```
- Update line 406: Change condition to handle the new logic properly

#### Task 2.3: Standardize Iteration Numbering
**File**: `src/core/pipeline.py`
**Changes**:
- Line 212: Change to `iteration = 0  # Use 0-based internally`
- Line 219: Change loop to `while iteration < max_iterations:`
- Line 220: Remove increment, move to end of loop
- Line 285: Already using 0-based for file naming - keep
- Line 276: Change to `iteration=iteration` (not iteration_count - 1)
- Line 334: Update to use `iteration` not `iteration_count`
- End of loop: Add `iteration += 1`

**CLARIFICATION NEEDED**: Should external APIs (CLI output, metadata) show 1-based counting for user-friendliness while keeping 0-based internally?

### Phase 3: File Management Centralization (Priority: HIGH)

#### Task 3.1: Create IterationFileManager Class
**File**: `src/core/iteration_file_manager.py` (NEW FILE)
**Content**:
```python
"""Centralized file management for pipeline iterations."""

from pathlib import Path
import json
from typing import Optional

class IterationFileManager:
    """Manages all files for pipeline iterations."""
    
    def __init__(self, base_dir: Path, slug: str):
        """Initialize with base directory and idea slug."""
        self.base_dir = base_dir
        self.slug = slug
        self.analysis_dir = base_dir / slug
        self.iterations_dir = self.analysis_dir / "iterations"
        self.archive_dir = self.analysis_dir / ".archive"
        
    def setup_directories(self) -> None:
        """Create all necessary directories."""
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_dir.mkdir(exist_ok=True)
        
    def get_analysis_path(self, iteration: int) -> Path:
        """Get path for analysis file at given iteration."""
        return self.iterations_dir / f"iteration_{iteration:02d}_analysis.md"
        
    def get_feedback_path(self, iteration: int) -> Path:
        """Get path for feedback file at given iteration."""
        return self.iterations_dir / f"iteration_{iteration:02d}_feedback.json"
        
    def get_main_analysis_path(self) -> Path:
        """Get path for main analysis.md file."""
        return self.analysis_dir / "analysis.md"
        
    def get_main_feedback_path(self) -> Path:
        """Get path for main reviewer_feedback.json file."""
        return self.analysis_dir / "reviewer_feedback.json"
        
    def create_analysis_template(self, iteration: int) -> Path:
        """Create empty analysis file for agent to edit."""
        path = self.get_analysis_path(iteration)
        path.touch()
        return path
        
    def create_feedback_template(self, iteration: int) -> Path:
        """Create empty feedback JSON for reviewer to edit."""
        path = self.get_feedback_path(iteration)
        path.write_text("{}")
        return path
        
    def copy_to_main(self, source: Path, target_type: str) -> Path:
        """Copy iteration file to main file."""
        if target_type == "analysis":
            target = self.get_main_analysis_path()
        elif target_type == "feedback":
            target = self.get_main_feedback_path()
        else:
            raise ValueError(f"Unknown target type: {target_type}")
            
        target.write_bytes(source.read_bytes())
        return target
        
    def find_latest_feedback(self, iteration: int) -> Optional[Path]:
        """Find the most recent feedback file before given iteration."""
        for i in range(iteration - 1, -1, -1):
            feedback_path = self.get_feedback_path(i)
            if feedback_path.exists():
                return feedback_path
        
        # Fallback to main feedback file
        main_feedback = self.get_main_feedback_path()
        if main_feedback.exists():
            return main_feedback
            
        return None
```

#### Task 3.2: Integrate IterationFileManager
**File**: `src/core/pipeline.py`
**Changes**:
- Add import: `from .iteration_file_manager import IterationFileManager`
- Line 69-94: Replace `_setup_directories` method with:
```python
def _setup_directories(self, slug: str, debug: bool) -> IterationFileManager:
    """Setup directories using file manager."""
    file_manager = IterationFileManager(Path("analyses"), slug)
    file_manager.setup_directories()
    
    # Archive existing files before starting new run
    run_type = "test" if debug else "production"
    self.archive_manager.archive_current_analysis(
        file_manager.analysis_dir, run_type=run_type
    )
    
    return file_manager
```
- Update all file creation/path logic to use file_manager methods

### Phase 4: Method Extraction (Priority: HIGH)

#### Task 4.1: Extract Analyst Execution Method
**File**: `src/core/pipeline.py`
**Location**: Extract lines 224-341 into new method
**New Method**:
```python
async def _execute_analyst(
    self,
    idea: str,
    iteration: int,
    file_manager: IterationFileManager,
    run_analytics: RunAnalytics,
    revision_context: Optional[RevisionContext] = None,
    tools_override: Optional[list[str]] = None,
) -> tuple[bool, Optional[str], Optional[Path], dict[str, object]]:
    """
    Execute analyst for given iteration.
    
    Returns:
        Tuple of (success, error_msg, analysis_path, metadata)
    """
    # 40 lines of focused analyst execution logic
```

#### Task 4.2: Extract Reviewer Execution Method
**File**: `src/core/pipeline.py`
**Location**: Extract lines 343-426 into new method
**New Method**:
```python
async def _execute_reviewer(
    self,
    iteration: int,
    analysis_path: Path,
    file_manager: IterationFileManager,
    run_analytics: RunAnalytics,
    revision_context: Optional[RevisionContext] = None,
) -> tuple[bool, Optional[FeedbackDict], Optional[str]]:
    """
    Execute reviewer for given iteration.
    
    Returns:
        Tuple of (success, feedback, error_msg)
    """
    # 30 lines of focused reviewer execution logic
```

#### Task 4.3: Extract Result Building Method
**File**: `src/core/pipeline.py`
**Location**: Extract lines 427-481 into new method
**New Method**:
```python
def _build_pipeline_result(
    self,
    success: bool,
    idea: str,
    slug: str,
    iteration_count: int,
    file_manager: IterationFileManager,
    iteration_results: list[IterationResult],
    feedback_history: list[FeedbackDict],
    current_analysis: Optional[str] = None,
    error: Optional[str] = None,
) -> PipelineResult:
    """Build final pipeline result dictionary."""
    # 30 lines of result construction logic
```

### Phase 5: Error Handling Improvements (Priority: MEDIUM)

#### Task 5.1: Create Custom Exception Hierarchy
**File**: `src/core/exceptions.py` (NEW FILE)
**Content**:
```python
"""Custom exceptions for pipeline operations."""

from pathlib import Path
from typing import Optional

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    
    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message)
        self.context = context or {}

class AnalystError(PipelineError):
    """Analyst agent failed."""
    
    def __init__(self, message: str, iteration: int, idea: str):
        super().__init__(message, {"iteration": iteration, "idea": idea})

class ReviewerError(PipelineError):
    """Reviewer agent failed."""
    
    def __init__(self, message: str, iteration: int, analysis_file: Path):
        super().__init__(message, {
            "iteration": iteration, 
            "analysis_file": str(analysis_file)
        })

class FileNotFoundError(PipelineError):
    """Expected file was not created."""
    
    def __init__(self, file_path: Path, operation: str):
        message = f"File not found during {operation}: {file_path}"
        super().__init__(message, {
            "file_path": str(file_path),
            "operation": operation
        })

class ValidationError(PipelineError):
    """Validation failed."""
    pass
```

#### Task 5.2: Implement Specific Error Handling
**File**: `src/core/pipeline.py`
**Changes**:
- Add import: `from .exceptions import AnalystError, ReviewerError, FileNotFoundError`
- Replace generic try/catch blocks with specific exception handling
- Add error recovery for common failures (timeout, file not found)

### Phase 6: RunAnalytics Integration Cleanup (Priority: LOW)

#### Task 6.1: Create Context Manager Wrapper
**File**: `src/core/analytics_context.py` (NEW FILE)
**Content**:
```python
"""Context manager for RunAnalytics integration."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from .run_analytics import RunAnalytics

@asynccontextmanager
async def analytics_context(
    run_id: str, 
    output_dir: Path
) -> RunAnalytics:
    """Context manager for RunAnalytics lifecycle."""
    analytics = RunAnalytics(run_id=run_id, output_dir=output_dir)
    try:
        yield analytics
    finally:
        analytics.finalize()
```

#### Task 6.2: Update Pipeline to Use Context Manager
**File**: `src/core/pipeline.py`
**Changes**:
- Import analytics_context
- Wrap main execution in async with block
- Remove manual finalize calls

## Verification Steps

After each phase:

1. **Run type checker**: `basedpyright src/core/pipeline.py`
2. **Run existing tests**: `pytest tests/unit/test_pipeline.py -xvs`
3. **Test iteration counts manually**:
   - `python -m src.cli analyze "test idea" --max-iterations 1` (should skip review)
   - `python -m src.cli analyze "test idea" --max-iterations 2` (should review and revise once)
4. **Check file naming**: Verify iterations/ contains properly numbered files
5. **Monitor logs**: Ensure proper logging at each step

## Potential Risks

### Risk 1: Breaking CLI Compatibility
**Mitigation**: Keep all public method signatures unchanged, only modify internals

### Risk 2: File Path Dependencies
**Mitigation**: Test with existing analyses/ directory structure before deployment

### Risk 3: Test Breakage
**Mitigation**: Update tests incrementally as each phase completes

### Risk 4: Iteration Count Confusion
**Mitigation**: Add clear documentation and logging to show what iteration means

### Risk 5: RunAnalytics Integration Issues
**Mitigation**: Keep RunAnalytics changes minimal and optional

## Rollback Strategy

If issues arise:

1. **Git revert** to previous commit
2. **Restore original pipeline.py** from backup
3. **Clear analyses/ directory** of any corrupted files
4. **Restart with more conservative changes**

Keep original pipeline.py as pipeline_backup.py during refactoring for quick recovery.

## Implementation Order

1. **Day 1 Morning**: Phase 1 (Type Safety) + Phase 2 (Iteration Logic)
2. **Day 1 Afternoon**: Phase 3 (File Management) 
3. **Day 2 Morning**: Phase 4 (Method Extraction)
4. **Day 2 Afternoon**: Phase 5 (Error Handling) + Phase 6 (RunAnalytics)

## Success Criteria

- ✅ Zero basedpyright warnings
- ✅ max_iterations=1 skips reviewer (no waste)
- ✅ Consistent 0-based iteration numbering internally
- ✅ All methods under 50 lines
- ✅ Centralized file management
- ✅ All existing tests pass
- ✅ New tests for edge cases added

---

*This refactoring plan was generated on 2025-08-20 for the idea-assess project pipeline.py refactoring.*
