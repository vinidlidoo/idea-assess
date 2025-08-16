# Refactoring Plan: run_analyst_reviewer_loop

## Current State Analysis

### Method Statistics

- **Total Lines**: ~295 lines (lines 80-375)
- **Cyclomatic Complexity**: High (multiple nested conditions, while loop, try/catch)
- **Responsibilities**: 12+ distinct responsibilities
- **Direct Dependencies**: 8+ classes/modules

### Main Responsibilities Identified

1. **Setup & Initialization** (30 lines)
   - Logger setup
   - Agent initialization
   - Directory creation
   - Archive management

2. **Iteration Loop Control** (core logic)
   - While loop management
   - Iteration counting
   - Break conditions

3. **Analyst Processing** (50 lines)
   - Input preparation (initial vs revision)
   - Feedback file resolution
   - Analyst invocation
   - Error handling

4. **File Management** (40 lines)
   - Analysis file saving
   - Iteration file management
   - Main file updates

5. **Reviewer Processing** (30 lines)
   - Reviewer invocation
   - Feedback loading
   - Feedback validation

6. **Decision Logic** (20 lines)
   - Continue/stop decisions
   - Acceptance criteria

7. **Result Preparation** (60 lines)
   - Final result assembly
   - Metadata creation
   - History saving

8. **Error Handling** (25 lines)
   - Exception catching
   - Error context
   - Cleanup

## Refactoring Strategy

### Phase 1: Extract Helper Methods (Low Risk)

Extract pure functions that don't change state:

- `_prepare_revision_context()`
- `_save_analysis_files()`
- `_load_and_validate_feedback()`
- `_should_continue_iteration()`
- `_prepare_final_result()`

### Phase 2: Extract State Management (Medium Risk)

Create dedicated classes for state:

- `IterationState` class to track iteration data
- `PipelineContext` class for shared context

### Phase 3: Extract Orchestration Components (High Risk)

Break into separate orchestrator classes:

- `AnalystOrchestrator`
- `ReviewerOrchestrator`
- `FileManager`

## Detailed Refactoring Steps

### Step 1: Create Helper Methods (Safe Extraction)

```python
# Extract these methods first (they're pure functions or have minimal side effects)

async def _initialize_pipeline(self, idea: str, debug: bool) -> tuple[StructuredLogger, str, Path]:
    """Initialize logger, slug, and directories."""
    
async def _setup_directories(self, slug: str) -> tuple[Path, Path]:
    """Create and return analysis_dir and iterations_dir."""
    
def _find_feedback_file(self, iterations_dir: Path, iteration_count: int, 
                        analysis_dir: Path, logger: Optional[StructuredLogger]) -> Optional[Path]:
    """Find the appropriate feedback file for the current iteration."""
    
def _save_analysis_to_files(self, analysis: str, iteration_count: int,
                           analysis_dir: Path, iterations_dir: Path) -> Path:
    """Save analysis to both iteration file and main file."""
    
def _create_iteration_result(self, iteration_count: int, file_path: Path,
                            analysis: str, metadata: dict) -> dict:
    """Create iteration result dictionary."""
    
def _prepare_pipeline_result(self, success: bool, idea: str, slug: str,
                            **kwargs) -> dict:
    """Prepare the final pipeline result dictionary."""
```

### Step 2: Create State Classes

```python
@dataclass
class IterationState:
    """Tracks state for a single iteration."""
    iteration_number: int
    analysis_content: str
    analysis_file: Path
    feedback: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

class PipelineState:
    """Manages overall pipeline state."""
    def __init__(self):
        self.iterations: list[IterationState] = []
        self.current_iteration: int = 0
        self.feedback_history: list[dict] = []
        
    def add_iteration(self, state: IterationState):
        self.iterations.append(state)
        self.current_iteration += 1
```

### Step 3: Create Orchestrators

```python
class AnalystOrchestrator:
    """Handles analyst-specific operations."""
    
    async def run_initial_analysis(self, analyst: AnalystAgent, idea: str, 
                                  **kwargs) -> AgentResult:
        """Run first iteration analysis."""
        
    async def run_revision_analysis(self, analyst: AnalystAgent, idea: str,
                                   revision_context: dict, **kwargs) -> AgentResult:
        """Run revision based on feedback."""

class ReviewerOrchestrator:
    """Handles reviewer-specific operations."""
    
    async def review_analysis(self, reviewer: ReviewerAgent, 
                             analysis_file: Path, **kwargs) -> AgentResult:
        """Run reviewer on analysis file."""
        
    def process_feedback(self, feedback_file: str) -> dict:
        """Load and validate feedback."""

class PipelineFileManager:
    """Manages all file operations for the pipeline."""
    
    def save_analysis(self, content: str, iteration: int) -> Path:
        """Save analysis files."""
        
    def save_feedback(self, feedback: dict, iteration: int) -> Path:
        """Save feedback files."""
        
    def save_metadata(self, metadata: dict) -> Path:
        """Save metadata files."""
```

## Implementation Order & Risk Assessment

### Priority 1: Low Risk Extractions (Can't break existing code)

1. Extract logging setup → `_initialize_logging()`
2. Extract directory creation → `_setup_directories()`
3. Extract feedback file finding → `_find_feedback_file()`
4. Extract file saving methods → `_save_analysis_files()`, `_save_feedback_files()`

### Priority 2: Medium Risk Refactoring

5. Create `IterationState` dataclass
6. Extract iteration result creation → `_create_iteration_result()`
7. Extract final result preparation → `_prepare_final_result()`
8. Create `PipelineFileManager` class

### Priority 3: High Risk Refactoring (Test thoroughly)

9. Create `PipelineState` class
10. Extract analyst orchestration
11. Extract reviewer orchestration
12. Refactor main loop to use new components

## Testing Strategy

### Before Refactoring

1. Run full test suite, save output
2. Create snapshot of current behavior
3. Add integration tests if missing

### During Refactoring

1. Extract one method at a time
2. Run tests after each extraction
3. Commit after each successful extraction

### After Refactoring

1. Run full test suite
2. Compare with original snapshot
3. Performance benchmark

## Rollback Plan

1. Each extraction is a separate commit
2. If tests fail, revert last commit
3. Keep original method commented until all tests pass
4. Delete original only after 100% test coverage

## Success Criteria

- [ ] Method reduced to <50 lines
- [ ] Each extracted method <30 lines
- [ ] All tests still pass
- [ ] No performance degradation
- [ ] Improved readability score
- [ ] Each component is independently testable

## Potential Issues to Watch

1. **Shared State**: Logger and agents are passed around
2. **File System Dependencies**: Many file operations
3. **Async Complexity**: Multiple await points
4. **Error Context**: Must preserve error information
5. **Transaction Semantics**: Some operations should be atomic

## TODO List for Implementation

- [ ] Create backup branch: `git checkout -b refactor-pipeline-god-method`
- [ ] Run and save current test output
- [ ] Extract `_initialize_logging()` method
- [ ] Extract `_setup_directories()` method  
- [ ] Extract `_find_feedback_file()` method
- [ ] Extract `_save_analysis_files()` method
- [ ] Extract `_save_feedback_files()` method
- [ ] Create `IterationState` dataclass
- [ ] Extract `_create_iteration_result()` method
- [ ] Extract `_prepare_final_result()` method
- [ ] Create `PipelineFileManager` class
- [ ] Move file operations to `PipelineFileManager`
- [ ] Create `PipelineState` class
- [ ] Refactor main loop to use `PipelineState`
- [ ] Extract analyst orchestration logic
- [ ] Extract reviewer orchestration logic
- [ ] Clean up main method
- [ ] Update tests for new structure
- [ ] Performance testing
- [ ] Documentation update
- [ ] Final review and cleanup
- [ ] Merge to main branch

## Notes

- Start with the SAFEST extractions first
- Each extraction should be atomic and testable
- Preserve ALL existing behavior
- Keep detailed comments during transition
- Consider using feature flags for gradual rollout
