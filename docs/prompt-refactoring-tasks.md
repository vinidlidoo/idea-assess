# Prompt Refactoring Task List

## Overview

Implementing the prompt structure improvements to eliminate duplication and standardize organization.

## Task List

### Phase 1: Setup Infrastructure

- [ ] Create `load_prompt_with_includes()` function in `src/utils/file_operations.py`
- [ ] Write unit tests for include mechanism in `tests/test_prompt_loading.py`
- [ ] Update `BaseAgent.get_prompt_path()` to support variants (system, system_v1, etc.)
- [ ] Add `BaseAgent.load_system_prompt()` method for include processing

### Phase 2: Create Shared Components

- [ ] Create `config/prompts/shared/` directory
- [ ] Create `shared/file_edit_rules.md` with Read-before-Edit rules
- [ ] Remove duplicate rules from existing prompts

### Phase 3: Restructure Analyst Prompts

- [ ] Rename `config/prompts/agents/analyst/main.md` → `system.md`
- [ ] Move `partials/` → `user/` directory
- [ ] Rename files in user/:
  - [ ] `user_instruction.md` → `initial.md`
  - [ ] Keep `revision.md` as is
  - [ ] `resource_constraints.md` → `constraints.md`
  - [ ] Keep websearch files as is
- [ ] Add `{{include:shared/file_edit_rules.md}}` to system.md
- [ ] Update `analyst.py` to use new paths

### Phase 4: Restructure Reviewer Prompts  

- [ ] Rename `config/prompts/agents/reviewer/main.md` → `system.md`
- [ ] Create `user/` directory
- [ ] Move `instructions.md` → `user/review.md`
- [ ] Create `user/constraints.md` for reviewer-specific limits
- [ ] Add `{{include:shared/file_edit_rules.md}}` to system.md
- [ ] Update `reviewer.py` to use new paths

### Phase 5: Update Code References

- [ ] Update `analyst.py`:
  - [ ] Use `load_prompt_with_includes()` for system prompt
  - [ ] Update all prompt paths from `partials/` to `user/`
  - [ ] Update `resource_constraints.md` to `constraints.md`
- [ ] Update `reviewer.py`:
  - [ ] Use `load_prompt_with_includes()` for system prompt
  - [ ] Update path from `instructions.md` to `user/review.md`

### Phase 6: Documentation & Testing

- [ ] Update `config/prompts/README.md` with new structure
- [ ] Run all existing tests to ensure compatibility
- [ ] Test both agents with sample ideas
- [ ] Verify include mechanism works correctly
- [ ] Test A/B variant loading (create test system_v1.md files)

### Phase 7: Cleanup

- [ ] Remove old prompt files after confirming everything works
- [ ] Update any remaining documentation
- [ ] Create migration notes for team

## File Structure After Refactoring

```text
config/prompts/
├── shared/
│   └── file_edit_rules.md           # Shared Read-before-Edit rules
│
├── agents/
│   ├── analyst/
│   │   ├── system.md                # Main prompt with {{include}}
│   │   ├── system_v1.md            # A/B test variant (optional)
│   │   └── user/
│   │       ├── initial.md
│   │       ├── revision.md
│   │       ├── constraints.md      # Agent-specific limits
│   │       ├── websearch_instruction.md
│   │       └── websearch_disabled.md
│   │
│   └── reviewer/
│       ├── system.md                # Main prompt with {{include}}
│       └── user/
│           ├── review.md
│           └── constraints.md      # Agent-specific limits
```

## Success Criteria

1. **No Duplication**: File edit rules exist in only one place
2. **Consistent Structure**: Both agents follow same directory pattern
3. **Working Includes**: `{{include:shared/file_edit_rules.md}}` processes correctly
4. **Backwards Compatible**: Existing functionality unchanged
5. **A/B Testing Ready**: Variant system works for prompt experiments
6. **Well Tested**: Unit tests pass for include mechanism
7. **Documented**: README.md accurately reflects new structure

## Notes

- Keep changes minimal - only restructure what's necessary
- Preserve all existing prompt content (just reorganize)
- Test after each phase to catch issues early
- Create backups before making changes
