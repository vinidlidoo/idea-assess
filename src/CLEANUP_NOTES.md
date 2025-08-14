# Code Cleanup Notes - Phase 2 Completion

## Files to Remove (Old/Broken Implementations)

### Reviewer Implementations

- `src/agents/reviewer.py` - Original broken implementation (passed full content)
- `src/agents/reviewer_fixed.py` - Attempted fix, still had issues
- `src/agents/reviewer_simple.py` - Simplified version, not used

**Keep:** `src/agents/reviewer_file.py` - Working file-based implementation

### Pipeline Implementations  

- `src/core/pipeline.py` - Original pipeline that passed content directly

**Keep:** `src/core/pipeline_file.py` - Working file-based pipeline

## Import Updates Needed

1. `src/agents/__init__.py` - Update to import from reviewer_file instead of reviewer_fixed
2. Verify no other files import the old implementations

## Code Quality Issues to Address

1. **Permission Mode**: Ensure all agents use 'default' not 'acceptEdits' or invalid modes
2. **Type Checking**: Replace string-based type checking with isinstance()
3. **Error Handling**: Add better error recovery for file operations
4. **Unused Imports**: Clean up any imports from removed modules

## Testing Artifacts to Clean

Check `analyses/` folder for test runs that can be removed:

- Multiple iterations of test analyses
- Broken/incomplete analysis attempts

## Documentation Updates

1. Remove references to old implementations in comments
2. Update docstrings to reflect file-based approach
3. Add notes about SDK limitations and workarounds

## Next Session Priorities

1. Run claude-sdk-expert review on cleaned codebase
2. Run code-reviewer agent for quality assessment
3. Implement recommended improvements
4. Begin Phase 3 (Judge agent) with clean foundation
