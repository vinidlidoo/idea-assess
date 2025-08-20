# Action Items from Codebase Review - 2025-08-20

## Quick Fixes (Do Immediately)

*Items that can be fixed in < 2 minutes*

### src/cli.py ✅

1. ~~**Unnecessary variable assignments** (lines 51-73): All those `_ = parser.add_argument()` assignments~~ - Actually needed for basedpyright
2. ~~**Redundant type casting** (lines 99-103)~~ - Fixed, added type annotations instead
3. ~~**Unnecessary try-except blocks and dotenv** (lines 13-34)~~ - Removed, simplified imports
4. ~~**sys.path hack** (lines 16-17)~~ - Removed, not needed when running from project root
5. ~~**Move imports to top** (lines 80-82)~~ - Fixed, imports now at module level
6. ~~**Remove --tools option** - Removed, not needed yet
7. ~~**Consistent error handling** (lines 169-176)~~ - Now uses logger with print() fallback

---

## Medium Fixes (Do This Session)

*Items that need 5-15 minutes of work*

### src/cli.py

1. **Update prompt-variant choices** (lines 47-53): Align with new prompt structure (system.md vs main.md)
<!-- FEEDBACK: need to keep -->
2. **Remove prompt-variant option entirely?** - May not be needed with new structure

### config/prompts/README.md

1. **Remove references to prompt_registry.py** - No longer exists
2. **Update file loading examples** - Reflect current implementation
3. **Fix main.md vs system.md confusion** - Document actual primary files

### src/core/pipeline.py

1. **Standardize imports** (lines 8-19): Use module-level imports with qualified names
   - Change to: `from ..agents import analyst, reviewer`
   - Then use: `analyst.AnalystAgent`, `reviewer.ReviewerAgent`
   - More concise and still clear given our directory structure
2. **Remove tools_override parameter** - Not used anymore since we removed --tools from CLI
<!-- FEEDBACK: not needed -->
3. **Consider TypedDict for feedback structure** - Would eliminate all the `reportAny` warnings

---

## Larger Tasks (Document for Later)

*Items that need careful planning or significant refactoring*

**Pipeline Architecture Refactoring:** ✅ COMPLETED

1. ~~**Implement mode-driven pipeline**~~ - DONE! See `2025-08-20-pipeline-refactoring-complete.md`
   - ~~Add PipelineMode enum and PipelineConfig~~
   - ~~Refactor pipeline to use `process(idea, mode)` interface~~
   - ~~Remove redundant parameters (use_websearch, max_iterations, tools_override)~~
   - ~~Update CLI to use new interface~~
   - ~~Full task list in refactoring document~~

**cli.py - Result Formatting:**

1. **Extract result formatting logic** (lines 120-163): Move to PipelineResult class or result_formatter utility
   - Too much business logic in CLI
   - Should be testable separately
   - CLI should just display pre-formatted output

---

## Questions for User

*Things that need clarification before proceeding*

---

## Notes & Observations

*General observations about code quality and patterns*

**cli.py observations:**

- Clean async/await structure
- Good error handling with KeyboardInterrupt
- Clear help text and examples
- Proper use of environment variables (dotenv)
- Good separation of concerns (CLI vs pipeline)

**pipeline.py observations:**

- Successfully simplified from 640 to 205 lines (68% reduction!)
- Clean orchestration logic with clear iteration flow
- Good error handling with try/finally for analytics
- Proper use of logging throughout
- File-based communication pattern works well for agent isolation
- Minor issues: untyped feedback dict, hardcoded paths, unused tools_override

---

## File Review Progress

- [x] src/cli.py ✅
- [x] src/core/pipeline.py ✅
- [ ] src/agents/analyst.py
- [ ] src/agents/reviewer.py
- [ ] src/core/agent_base.py
- [ ] src/core/config.py
- [ ] src/core/run_analytics.py
- [ ] src/core/types.py
- [ ] src/utils/logger.py
- [ ] src/utils/file_operations.py
- [ ] src/utils/text_processing.py
- [ ] src/utils/cleanup_manager.py
- [ ] src/utils/archive_manager.py
- [ ] src/utils/json_validator.py
- [ ] src/utils/retry.py

---

*This document tracks all findings during the 2025-08-20 codebase review session*
