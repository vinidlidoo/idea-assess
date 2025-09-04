# Phase 2 Simplification: Implementation Tasks

**Date**: 2025-08-21  
**Status**: READY TO EXECUTE  
**Estimated Time**: ~7 hours  
**Approach**: Clean break, archive old code

## Implementation Checklist

### Phase 1: Archive Current Code (30 min)

- [ ] Create archive/phase2-pre-refactor/ directory
- [ ] Move src/core/config.py → archive/phase2-pre-refactor/config_old.py
- [ ] Move src/core/pipeline.py → archive/phase2-pre-refactor/pipeline_old.py
- [ ] Move src/core/agent_base.py → archive/phase2-pre-refactor/agent_base_old.py
- [ ] Copy src/core/types.py → archive/phase2-pre-refactor/types_old.py (keep original)

### Phase 2: Create New Core Structures (2 hours)

#### 2.1 Create new config.py

- [ ] SystemConfig class with paths and limits
- [ ] BaseAgentConfig with common settings
- [ ] AnalystConfig extending BaseAgentConfig
- [ ] ReviewerConfig extending BaseAgentConfig
- [ ] Remove all Phase 3/4 elements
- [ ] Implement get_allowed_tools() method

#### 2.2 Create new contexts.py

- [ ] BaseContext with minimal fields
- [ ] AnalystContext with explicit paths
- [ ] ReviewerContext with explicit paths
- [ ] Remove output_dir from BaseContext
- [ ] Remove websearch_count tracking

#### 2.3 Create new results.py

- [ ] Success dataclass (no data needed)
- [ ] Error dataclass with message
- [ ] AgentResult type alias (Union[Success, Error])
- [ ] Keep simplified PipelineResult TypedDict

### Phase 3: Update Agent Infrastructure (2 hours)

#### 3.1 Update agent_base.py

- [ ] Simplify BaseAgent class
- [ ] Keep generics (TConfig, TContext)
- [ ] Update process() to return AgentResult
- [ ] Remove complex prompt resolution
- [ ] Remove override logic

#### 3.2 Update AnalystAgent

- [ ] Import new Success/Error types
- [ ] Update process() to return Success() or Error(message)
- [ ] Remove metadata from result
- [ ] Use config.allowed_tools directly
- [ ] Handle feedback_input_path for revisions

#### 3.3 Update ReviewerAgent

- [ ] Import new Success/Error types
- [ ] Update process() to return Success() or Error(message)
- [ ] Use explicit paths from context
- [ ] Remove strictness from context (use config)

### Phase 4: Update Pipeline (1.5 hours)

#### 4.1 Core Pipeline Changes

- [ ] Import new configs and contexts
- [ ] Remove PipelineConfig usage
- [ ] Get max_iterations from ReviewerConfig
- [ ] Remove override parameters from **init**
- [ ] Simplify state tracking

#### 4.2 Update Pipeline Methods

- [ ] Update _run_analyst() to return AgentResult
- [ ] Implement pattern matching for Success/Error
- [ ] Update _should_continue_after_review()
- [ ] Simplify _build_result() method
- [ ] Clean up redundant state variables

### Phase 5: Update CLI Integration (30 min)

- [ ] Remove override handling
- [ ] Direct config modification pattern
- [ ] Update config creation
- [ ] Remove unused CLI flags
- [ ] Test argument parsing

### Phase 6: Update Imports & Cleanup (30 min)

- [ ] Update all import statements
- [ ] Remove old config imports
- [ ] Update **init**.py files
- [ ] Remove unused imports
- [ ] Check for circular imports

### Phase 7: Testing & Validation (1 hour)

- [ ] Run basic test: `python -m src.cli analyze "test idea"`
- [ ] Test with review: `python -m src.cli analyze "test idea" --with-review`
- [ ] Test no websearch: `python -m src.cli analyze "test idea" --no-websearch`
- [ ] Check file creation in analyses/
- [ ] Verify symlink updates
- [ ] Run ruff check
- [ ] Run basedpyright

## File Structure After Refactoring

```text
src/
├── core/
│   ├── __init__.py
│   ├── config.py        # NEW: SystemConfig, BaseAgentConfig, agent configs
│   ├── contexts.py      # NEW: BaseContext, AnalystContext, ReviewerContext
│   ├── results.py       # NEW: Success, Error, AgentResult
│   ├── agent_base.py    # UPDATED: Simplified BaseAgent
│   ├── pipeline.py      # UPDATED: Pattern matching, cleaner state
│   ├── types.py         # KEEP: Only PipelineResult and PipelineMode
│   └── run_analytics.py # UNCHANGED
├── agents/
│   ├── __init__.py
│   ├── analyst.py       # UPDATED: Success/Error pattern
│   └── reviewer.py      # UPDATED: Success/Error pattern
├── utils/               # UNCHANGED
└── cli.py              # UPDATED: Direct config modification

archive/
└── phase2-pre-refactor/
    ├── config_old.py
    ├── pipeline_old.py
    ├── agent_base_old.py
    └── types_old.py
```

## Success Criteria

1. ✅ All tests pass
2. ✅ No linting errors
3. ✅ Clean pattern matching in pipeline
4. ✅ No "default_" prefix confusion
5. ✅ max_iterations in ReviewerConfig
6. ✅ Explicit typed paths in contexts
7. ✅ ~30% code reduction achieved

## Risk Mitigation

1. **Archive everything first** - Can revert if needed
2. **Test after each phase** - Catch issues early
3. **Keep types.py** - Only update what's needed
4. **Don't touch utils/** - Already cleaned
5. **Keep run_analytics.py** - Works fine as-is

## Notes

- Pattern matching requires Python 3.10+
- Clean break approach - no backwards compatibility
- Focus on clarity over cleverness
- Keep changes focused on v4 proposal

---

**Ready to execute. Pause here for context compaction.**

