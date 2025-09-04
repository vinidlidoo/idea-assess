# FactChecker Agent Implementation Plan

## Current Status: Phase 2 Complete - FactChecker Fully Integrated! ✅

### ✅ What's Working

1. **Pipeline Infrastructure**
   - Parallel execution with `asyncio.gather()` confirmed working
   - Veto logic (both agents must approve) implemented
   - New pipeline mode: `ANALYZE_REVIEW_WITH_FACT_CHECK`
   - CLI flag `--with-fact-check` added

2. **Full Claude SDK Integration**
   - `FactCheckerAgent` class with complete Claude SDK integration
   - System prompt loaded with `load_prompt_with_includes()`
   - User prompt template for fact-checking instructions
   - Proper ClaudeCodeOptions configuration
   - Async message streaming and tracking

3. **Parallel Execution Verified**
   - Reviewer and FactChecker run simultaneously after Analyst
   - Both agents receive run_analytics for logging
   - Error handling for failed agents
   - Veto power logic implemented

### 🔧 Recent Fixes

- Fixed missing include files (`shared/tools.md`, `shared/iteration_context.md`)
- Added proper user prompt template at `config/prompts/agents/fact-checker/user/fact-check.md`
- CLI integration with `--with-fact-check` flag (requires `--with-review`)

### 🎯 Next Priority: Phase 3 - Validation & Polish

**Enhance accuracy and reliability** (1 hour)

1. **Add JSON Schema Validation** (15 min)
2. **Prompt Refinement** (20 min)
3. **Integration Testing** (15 min)
4. **Documentation** (10 min)

## Overview

This document consolidates the FactChecker agent implementation strategy, combining immediate implementation steps with long-term architectural considerations.

## Implementation Phases

### Phase 0: Pipeline Preparation (1 hour) - **COMPLETED ✅**

Enable parallel execution in the pipeline with minimal changes.

#### Task 1: Add Core Types (10 min) ✅

- [x] Add `FactCheckContext` to `src/core/types.py`
- [x] Add `FactCheckerConfig` to `src/core/config.py`
- [x] Add `PipelineMode.ANALYZE_REVIEW_WITH_FACT_CHECK` enum value

#### Task 2: Create Template File (5 min) ✅

- [x] Create `config/templates/agents/fact-checker/fact-check.json`
- [x] Add TODO placeholders for all required fields
- [x] Follow same pattern as `feedback.json`

#### Task 3: Add Pipeline Methods (20 min) ✅

- [x] Add `_run_fact_checker()` method (copy from `_run_reviewer`)
  - Include inline JSON parsing like reviewer does (no separate helper needed)
- [x] Add `run_parallel_review_fact_check()` wrapper function
- [x] Add `_analyze_review_with_fact_check()` mode handler

#### Task 4: Update Pipeline Router (5 min) ✅

- [x] Add new mode to `handlers` dict in `process()`
- [ ] Update `__init__` to accept `fact_checker_config` (deferred to Phase 1)

#### Task 5: Write Tests (20 min) ⏸️

- [ ] Test parallel execution with mocked agents (deferred - need FactCheckerAgent first)
- [ ] Test veto logic (both approve, one rejects, both reject)
- [ ] Test error handling (one agent fails)

**Status:** Phase 0 is functionally complete. All pipeline infrastructure is in place for parallel execution. Tests deferred until Phase 1 when FactCheckerAgent class exists.

### Phase 1: Pipeline Integration & Basic Agent (1.5 hours) - **COMPLETED ✅**

#### Task 1: Update Pipeline Initialization (15 min) ✅

- [x] Add `fact_checker_config` parameter to `AnalysisPipeline.__init__()`
- [x] Update `create_default_configs()` to include FactCheckerConfig
- [x] Import FactCheckerAgent type (with forward reference)

#### Task 2: Create Basic Agent Class (30 min) ✅

- [x] Create `src/agents/fact_checker.py`
- [x] Inherit from `BaseAgent[FactCheckerConfig, FactCheckContext]`
- [x] Implement minimal `process()` method that returns Success
- [x] Add `agent_name` property returning "FactChecker"

#### Task 3: Wire Up Parallel Execution (15 min) ✅

- [x] Import FactCheckerAgent in pipeline
- [x] Update `_analyze_review_with_fact_check()` to instantiate fact_checker
- [x] Replace reviewer-only call with `run_parallel_review_fact_check()`
- [x] Pipeline compiles without errors

#### Task 4: Create Basic System Prompt (15 min) ✅

- [x] Create `config/prompts/agents/fact-checker/system.md`
- [x] Add basic structure with {{include}} for shared components
- [x] Include JSON output format requirements

#### Task 5: Test Parallel Execution (15 min) ✅

- [x] Pipeline type-checks successfully
- [x] Parallel execution logic in place
- [x] Veto logic implemented
- [x] JSON output generation confirmed

### Phase 2: Connect to Claude SDK ✅ COMPLETED

#### Task 1: Load System Prompt (30 min) ✅

- [x] Import `load_prompt_with_includes` from utils
- [x] Load fact-checker system prompt
- [x] Process {{include}} tags (fixed missing includes)
- [x] Format with iteration context

#### Task 2: Create Claude Client (30 min) ✅

- [x] Import ClaudeSDKClient and ClaudeCodeOptions
- [x] Create client with proper configuration
- [x] Set allowed tools (WebFetch, Edit, TodoWrite)
- [x] Handle API key and session

#### Task 3: Send to Claude and Parse Response (45 min) ✅

- [x] Format user message with analysis content
- [x] Call Claude with system prompt
- [x] Extract JSON from response
- [x] Validate and write to output file

#### Task 4: Test End-to-End (15 min) ✅

- [x] Run pipeline with ANALYZE_REVIEW_WITH_FACT_CHECK mode
- [x] Verify Claude is actually called (parallel execution confirmed)
- [x] Check JSON output is valid
- [x] Test veto logic works (both agents run in parallel)

### Phase 3: Validation & Polish (1 hour)

#### Task 1: Add JSON Validation (15 min)

- [ ] Add `FACT_CHECK_SCHEMA` to `src/utils/json_validator.py`
- [ ] Create `FactCheckValidator` class
- [ ] Test schema validation

#### Task 2: Prompt Refinement (20 min)

- [ ] Test with real analyses
- [ ] Refine severity thresholds
- [ ] Add examples to prompt
- [ ] Tune for citation accuracy

#### Task 3: Integration Testing (15 min)

- [ ] Full pipeline run with known-good analysis
- [ ] Test with analysis containing false claims
- [ ] Verify iteration behavior
- [ ] Check parallel execution timing

#### Task 4: Documentation (10 min)

- [ ] Update CLI help text
- [ ] Document configuration options
- [ ] Add usage examples

## Immediate Implementation Plan (Phase 0 Details)

### What We're Building

A FactChecker agent that runs in parallel with ReviewerAgent to verify claims and citations in the Analyst's output. Both agents must approve for the iteration to complete (veto power).

### Implementation Approach: Option B - Minimal Changes

#### Step 1: Add Core Types (10 min)

```python
# In src/core/types.py
@dataclass
class FactCheckContext(BaseContext):
    """Context for fact-checker agent."""
    analysis_input_path: Path
    fact_check_output_path: Path
    iteration: int

# In src/core/config.py
@dataclass
class FactCheckerConfig(BaseAgentConfig):
    """Configuration for FactChecker agent."""
    max_verifications: int = 3
    webfetch_per_iteration: int = 10
    allowed_tools: list[str] = field(
        default_factory=lambda: ["WebFetch", "Edit", "TodoWrite"]
    )
```

#### Step 2: Add Agent Runner Method (15 min)

Copy `_run_reviewer` pattern for fact-checker:

```python
# In src/core/pipeline.py
async def _run_fact_checker(self, fact_checker: FactCheckerAgent) -> bool:
    """Run fact-checker - same pattern as _run_reviewer."""
    # Create fact-check file from template
    # Build context
    # Run agent
    # Parse JSON inline (like reviewer does - no separate helper needed)
    try:
        fact_check = json.loads(fact_check_file.read_text())
        recommendation = fact_check.get("recommendation", "reject")
        return recommendation == "approve"
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse fact-check: {e}")
        return False
```

#### Step 3: Add Parallel Wrapper Function (15 min)

```python
# In src/core/pipeline.py (standalone function, not method)
async def run_parallel_review_fact_check(
    pipeline: AnalysisPipeline,
    reviewer: ReviewerAgent,
    fact_checker: FactCheckerAgent
) -> bool:
    """Run reviewer and fact-checker in parallel."""
    import asyncio
    
    results = await asyncio.gather(
        pipeline._run_reviewer(reviewer),
        pipeline._run_fact_checker(fact_checker),
        return_exceptions=True
    )
    
    # Handle errors
    if any(isinstance(r, Exception) for r in results):
        return True  # Continue iterating on error
    
    # Veto power: both must approve to stop
    reviewer_approved, checker_approved = results
    return not (reviewer_approved and checker_approved)
```

#### Step 4: Add Pipeline Mode (5 min)

```python
# In src/core/pipeline.py
async def _analyze_with_fact_check(self) -> PipelineResult:
    """Same as _analyze_with_review but calls parallel wrapper."""
    # ... identical to _analyze_with_review except:
    should_continue = await run_parallel_review_fact_check(
        self, reviewer, fact_checker
    )
```

#### Step 5: Test (10 min)

Basic test for parallel execution and veto logic.

### Data Flow

```text
Iteration N:
  Analyst writes → analysis_N.md
  ┌─ Reviewer reads analysis_N.md → writes feedback_N.json
  └─ FactChecker reads analysis_N.md → writes fact_check_N.json
  Pipeline reads both JSONs → applies veto logic → decides continue/stop
```

## FactChecker Agent Specification

### Core Responsibilities

1. **Verify Claims**: Check if claims have supporting citations
2. **Validate Citations**: Verify citations are real and accurate
3. **Detect Hallucinations**: Flag likely fabricated information
4. **Assess Credibility**: Score overall citation quality

### Output Format

```json
{
  "issues": [
    {
      "claim": "The specific claim being checked",
      "section": "Section where claim appears",
      "severity": "High|Medium|Low",
      "details": {
        "issue_type": "unsupported_claim|false_citation|outdated_citation|likely_hallucination",
        "explanation": "Why this is an issue",
        "evidence": "What was found when checking",
        "suggestion": "How to fix"
      }
    }
  ],
  "statistics": {
    "total_claims": 15,
    "verified_claims": 10,
    "unverified_claims": 3,
    "false_claims": 2
  },
  "recommendation": "approve|reject",
  "top_priorities": ["Fix issue 1", "Verify claim 2"]
}
```

### Severity Levels

- **High**: Unsupported major claims, false citations, clear hallucinations (auto-reject)
- **Medium**: Minor unsupported claims, outdated sources
- **Low**: Missing optional citations, formatting issues

### Pass/Fail Criteria

- **Pass**: 0 High severity issues AND <3 Medium severity issues
- **Fail**: Any High severity issue OR ≥3 Medium severity issues

## Long-Term Architecture Considerations

### Current Weak Points (As We Scale)

1. **Config Proliferation**: Constructor needs N config parameters for N agents
2. **Mode Handler Explosion**: Each agent combination needs a new mode
3. **Agent Runner Duplication**: 60+ lines of identical code per agent
4. **Hard-Coded Dependencies**: Can't inject mocks or custom agents
5. **Context Type Proliferation**: Each agent needs its own context class

### Future Improvements (Priority Order)

1. **Unified Agent Runner** - One generic method for all agents (reduces 300→60 lines)
2. **Agent Registry Pattern** - Central registry instead of N configs
3. **Composable Mode Definitions** - Define modes as data, not methods
4. **Generic Context Builder** - Build contexts by convention
5. **Plugin Architecture** - Allow custom agents without core changes

### When to Implement Improvements

- **Now**: Stick with minimal Option B for FactChecker
- **After Judge Agent**: Consider Unified Agent Runner
- **After Synthesizer**: Implement full registry pattern
- **Phase 5**: Full architectural improvements

## Key Design Decisions

1. **Parallel Execution**: Use `asyncio.gather()` with `return_exceptions=True`
2. **Veto Power**: Both agents must approve to proceed
3. **Template-Based Output**: JSON with TODO placeholders
4. **Iteration Awareness**: Different prompts for initial vs revision
5. **WebFetch Primary Tool**: Main verification mechanism

## Success Metrics

- Citation accuracy improves from 60% to 90%+
- False claims reduced to near zero
- Iteration efficiency maintained (no significant slowdown)
- Clear, actionable feedback to Analyst

## Implementation Checklist

- [ ] Create FactCheckContext and FactCheckerConfig types
- [ ] Add `_run_fact_checker()` method to pipeline
- [ ] Create `run_parallel_review_fact_check()` wrapper
- [ ] Add `_analyze_with_fact_check()` mode handler
- [ ] Create fact_check.json template file
- [ ] Implement FactCheckerAgent class
- [ ] Add FactChecker system prompt
- [ ] Write parallel execution tests
- [ ] Test veto logic
- [ ] Run end-to-end test with real idea

## Additional Resources

For detailed analysis and rationale:

- [Pipeline Architecture Diagrams](./supplemental/pipeline-architecture-diagrams.md) - Visual flow comparison
- [Scaling Analysis](./supplemental/pipeline-scaling-analysis.md) - Detailed weakness analysis
- [Full Agent Specification](./supplemental/fact-checker-agent-spec.md) - Complete requirements

---

*This plan prioritizes minimal changes (1 hour) while keeping future scalability in mind.*
