# Configuration System Refactoring Task List

**Created:** 2025-08-18  
**Author:** Python Refactor Planner  
**Refactoring Type:** Major - 3-Level Configuration Hierarchy Migration

## Executive Summary

Migrating from a single-level configuration system with kwargs to a 3-level hierarchy:

1. System Config (AnalysisConfig) → 2. Agent Configs (AnalystConfig, ReviewerConfig) → 3. Runtime Contexts (AnalystContext, ReviewerContext)

This refactoring will eliminate kwargs usage, improve type safety, and provide clear separation between system configuration and runtime state.

## Scope

### Files to be Modified

- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/cli.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/__init__.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/integration/test_pipeline.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_interrupt.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_pipeline_helpers.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_security.py`

### Files to be Removed

- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/constants.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/config_old.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/contexts.py`

## Impact Analysis

### Direct Impacts

- **BaseAgent**: Constructor signature change, new abstract methods
- **AnalystAgent**: Constructor change, process() signature change, kwargs removal
- **ReviewerAgent**: Constructor change, process() signature change
- **Pipeline**: Context object creation, argument passing changes
- **CLI**: Config hierarchy construction, tool override parsing

### Indirect Impacts

- **All Tests**: Agent instantiation and mock configurations
- **Import Statements**: Constants module removal requires import updates
- **Type Annotations**: New context types throughout codebase

## Prerequisites

- [ ] Backup current working state (git commit)
- [ ] Ensure all tests pass before starting
- [ ] Review new config.py structure is complete

## Detailed Task List

### Phase 1: Foundation Setup (Non-Breaking Changes)

#### Task 1: Update core/**init**.py exports

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/__init__.py`
**Changes:**

```python
# Add new exports
from .config import (
    AnalysisConfig,
    AnalystConfig,
    ReviewerConfig,
    AnalystContext,
    ReviewerContext,
    RevisionContext,
    get_default_config,
)
# Keep old export temporarily for compatibility
```

**Verification:** Import statements still work

---

#### Task 2: Merge constants into config.py

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/config.py`
**Changes:**

- Move module-level constants from constants.py to top of config.py:
  - `MAX_REVIEW_ITERATIONS = 3`
  - `MIN_REVIEW_ITERATIONS = 1`
  - `REVIEWER_MAX_TURNS = 3`
  - Other constants already in config as class attributes
**Verification:** Constants accessible via config module

---

### Phase 2: BaseAgent Refactoring

#### Task 3: Update BaseAgent to accept agent-specific config

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/agent_base.py`
**Changes:**

```python
from typing import TYPE_CHECKING, Generic, TypeVar
import threading

if TYPE_CHECKING:
    from .config import AnalystConfig, ReviewerConfig, BaseContext

TConfig = TypeVar('TConfig', bound='AnalystConfig | ReviewerConfig')
TContext = TypeVar('TContext', bound='BaseContext')

class BaseAgent(ABC, Generic[TConfig, TContext]):
    def __init__(self, config: TConfig):
        self.config = config
        self.interrupt_event = threading.Event()  # Move from AnalystAgent
    
    @abstractmethod
    async def process(self, input_data: str, context: TContext) -> AgentResult:
        """Process with context instead of kwargs"""
        pass
    
    # Remove get_allowed_tools() - now comes from config
    # Remove get_max_turns() - now comes from config
```

**Warnings:** This will temporarily break child classes until updated

---

### Phase 3: AnalystAgent Migration

#### Task 4: Remove prompt_version from AnalystAgent constructor

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Line:** 34
**Changes:**

```python
def __init__(self, config: AnalystConfig):  # Changed from AnalysisConfig
    super().__init__(config)
    # Remove self.prompt_version - use config.prompt_version
    # Remove self.interrupt_event - now in BaseAgent
```

---

#### Task 5: Update AnalystAgent.process to use context

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Lines:** 71-97
**Changes:**

```python
async def process(self, input_data: str, context: AnalystContext) -> AgentResult:
    """
    Analyze a business idea.
    
    Args:
        input_data: The business idea to analyze
        context: Runtime context with tools, revision info, etc.
    """
    # Remove all kwargs parsing (lines 85-91)
    # Replace with context field access:
    tools = context.tools_override or self.config.default_tools
    revision_info = None
    if context.revision_context:
        revision_info = {
            "previous_analysis_file": str(context.revision_context.previous_analysis_path),
            "feedback_file": str(context.revision_context.feedback_path),
        }
```

---

#### Task 6: Update get_prompt_file to use config

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Line:** 57
**Changes:**

```python
def get_prompt_file(self) -> str:
    return f"analyst_{self.config.prompt_version}.md"  # Use config not self
```

---

#### Task 7: Update get_allowed_tools to use config

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/analyst.py`
**Lines:** 60-64
**Changes:**

```python
def get_allowed_tools(self) -> list[str]:
    return self.config.default_tools  # Use config
```

---

### Phase 4: ReviewerAgent Migration

#### Task 8: Update ReviewerAgent constructor

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
**Lines:** 25-34
**Changes:**

```python
def __init__(self, config: ReviewerConfig):  # Changed from AnalysisConfig
    super().__init__(config)
    # Remove prompt_version parameter and field
```

---

#### Task 9: Update ReviewerAgent.process to use context

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
**Changes:**

```python
async def process(self, input_data: str, context: ReviewerContext) -> AgentResult:
    """
    Review an analysis.
    
    Args:
        input_data: Ignored (kept for interface compatibility)
        context: Runtime context with analysis_path
    """
    # Use context.analysis_path instead of kwargs
    # Remove kwargs parsing
```

**Note:** Need to handle analysis_path requirement from context

---

#### Task 10: Update constants imports in reviewer.py

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/agents/reviewer.py`
**Line:** 13
**Changes:**

```python
# Remove: from ..core.constants import MAX_REVIEW_ITERATIONS, REVIEWER_MAX_TURNS
from ..core.config import MAX_REVIEW_ITERATIONS, REVIEWER_MAX_TURNS
```

---

### Phase 5: Pipeline Updates

#### Task 11: Create agent configs in Pipeline.**init**

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Lines:** 30-40
**Changes:**

```python
def __init__(self, config: AnalysisConfig):
    self.config = config
    self.agents = {}
    self.feedback_processor = FeedbackProcessor()
    self.archive_manager = ArchiveManager(max_archives=5)
    
    # Pre-create agents with their specific configs
    self._analyst = AnalystAgent(config.analyst)
    self._reviewer = ReviewerAgent(config.reviewer)
```

---

#### Task 12: Update run_analyst_reviewer_loop to use contexts

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Changes:**

```python
async def run_analyst_reviewer_loop(
    self,
    idea: str,
    max_iterations: int = 3,
    use_websearch: bool = True,
) -> PipelineResult:
    # ... existing setup code ...
    
    # Create contexts instead of kwargs
    analyst_context = AnalystContext(
        tools_override=["WebSearch"] if use_websearch else [],
        idea_slug=slug,
        output_dir=analysis_dir,
    )
    
    # For revisions
    if iteration_count > 1:
        analyst_context.revision_context = RevisionContext(
            iteration=iteration_count,
            previous_analysis_path=previous_analysis_path,
            feedback_path=feedback_path,
        )
    
    # Call with context
    result = await self._analyst.process(idea, analyst_context)
```

---

#### Task 13: Update reviewer calls in pipeline

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Changes:**

```python
# Create reviewer context
reviewer_context = ReviewerContext(
    analysis_path=analysis_file,
)

# Call with context
review_result = await self._reviewer.process("", reviewer_context)
```

---

### Phase 6: CLI Updates

#### Task 14: Build config hierarchy in CLI

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/cli.py`
**Lines:** 113-127
**Changes:**

```python
# Get configuration with overrides
config = get_default_config()

# Apply CLI overrides to agent configs
if args.prompt_version:
    config.analyst.prompt_version = args.prompt_version

# Tool overrides handled in pipeline via context
```

---

#### Task 15: Update SimplePipeline for non-review path

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/pipeline.py`
**Changes:**

```python
class SimplePipeline:
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.analyst = AnalystAgent(config.analyst)
    
    async def run_analysis(self, idea: str, use_websearch: bool = True):
        context = AnalystContext(
            tools_override=["WebSearch"] if use_websearch else [],
        )
        return await self.analyst.process(idea, context)
```

---

### Phase 7: Test Updates

#### Task 16: Update test_pipeline.py agent creation

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/integration/test_pipeline.py`
**Lines:** Various agent creation points
**Changes:**

```python
# Update all AnalystAgent/ReviewerAgent instantiations
config = AnalysisConfig.from_project_root()
analyst = AnalystAgent(config.analyst)
reviewer = ReviewerAgent(config.reviewer)
```

---

#### Task 17: Update test_interrupt.py

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_interrupt.py`
**Changes:**

```python
# Update agent creation
config = AnalysisConfig.from_project_root()
agent = AnalystAgent(config.analyst)
```

---

#### Task 18: Update test_security.py

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_security.py`
**Changes:**

```python
# Update ReviewerAgent creation
config = AnalysisConfig.from_project_root()
agent = ReviewerAgent(config.reviewer)
```

---

#### Task 19: Update test_pipeline_helpers.py

**File:** `/Users/vincent/Projects/recursive-experiments/idea-assess/tests/unit/test_pipeline_helpers.py`
**Changes:**

```python
# Update config usage in tests
config = AnalysisConfig.from_project_root()
```

---

### Phase 8: Cleanup

#### Task 20: Remove old files

**Files to remove:**

- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/constants.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/config_old.py`
- `/Users/vincent/Projects/recursive-experiments/idea-assess/src/core/contexts.py`

**Command:**

```bash
git rm src/core/constants.py src/core/config_old.py src/core/contexts.py
```

---

#### Task 21: Final import cleanup

**All affected files**
**Changes:**

- Remove any remaining `from ..core.constants import`
- Update to use config module for constants
- Verify no references to contexts.py remain

---

## Verification Steps

### After Each Phase

1. [ ] Run unit tests: `python -m pytest tests/unit/`
2. [ ] Check imports: `python -c "from src.core import *"`
3. [ ] Verify no syntax errors: `python -m py_compile src/**/*.py`

### After Phase 8

1. [ ] Full test suite: `python -m pytest`
2. [ ] Manual CLI test: `python -m src.cli "test idea"`
3. [ ] With review test: `python -m src.cli "test idea" --with-review`
4. [ ] Check for unused imports: `python -m pyflakes src/`

## Rollback Strategy

If issues arise during refactoring:

1. **Phase-level rollback**: Each phase is designed to be atomic

   ```bash
   git stash  # Save current work
   git checkout -- <affected_files>  # Revert phase changes
   ```

2. **Full rollback**: Return to pre-refactor state

   ```bash
   git checkout HEAD~1  # Return to backup commit
   ```

3. **Partial rollback**: Keep some changes

   ```bash
   git checkout -p HEAD~1 <specific_files>  # Interactive revert
   ```

## Potential Risks

### Risk 1: Type Incompatibilities

**Issue:** Generic types in BaseAgent may cause mypy errors  
**Mitigation:** Start with simple typing, refine after functionality works  
**Fallback:** Use `Any` types temporarily if blocking

### Risk 2: Test Mocking Breakage

**Issue:** Tests that mock agent internals may break  
**Mitigation:** Update mocks incrementally as each agent is migrated  
**Watch for:** Tests using `patch` on agent methods

### Risk 3: Circular Import Issues

**Issue:** Config importing from types, types importing from config  
**Mitigation:** Use TYPE_CHECKING guards for type-only imports  
**Prevention:** Keep context classes in config.py, not separate file

### Risk 4: Pipeline State Management

**Issue:** RevisionContext state tracking across iterations  
**Mitigation:** Test revision flow explicitly after changes  
**Critical Path:** Lines handling feedback_path and previous_analysis_path

### Risk 5: Default Values Mismatch

**Issue:** Config defaults different from previous hardcoded values  
**Check:** Compare all constants.py values with config.py defaults  
**Specific Values:**

- MAX_TURNS: 30 (analyst) vs 3 (reviewer)
- Tool lists: ["WebSearch"] vs []
- Word limits: Must match SECTION_WORD_LIMITS

## Success Criteria

- [ ] All tests pass without modification to test logic
- [ ] No kwargs remain in agent process() methods
- [ ] Type checker (mypy) reports no errors
- [ ] CLI works with all flag combinations
- [ ] Review iteration flow works correctly
- [ ] No performance degradation

## Notes for Implementation

### Order is Critical

- Foundation changes (Phase 1-2) must complete before agent updates
- Pipeline must be updated after agents to use new interfaces
- Tests should be updated last to verify everything works

### Testing Checkpoints

- Run tests after Phase 2 (expect failures, but no crashes)
- Run tests after Phase 4 (ReviewerAgent should work)
- Run tests after Phase 5 (Pipeline integration should work)
- Full test suite after Phase 8

### CLARIFICATION NEEDED

1. Should prompt_version be mutable at runtime or fixed at startup?
2. Should we support tool override per-iteration or per-run only?
3. How should we handle backward compatibility for external callers?

---

*Generated by Python Refactor Planner - 2025-08-18*
