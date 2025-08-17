# Logger Compatibility Methods Deprecation Plan

## Current Status

The logger refactoring is complete with a new simplified `Logger` class. However, we still have 39 calls to compatibility methods that need to be cleaned up.

## Compatibility Methods to Remove

Located in `src/utils/logger.py` lines 192-241:

- `log_event()` - 30 calls remaining
- `log_error()` - 5 calls remaining  
- `log_milestone()` - 4 calls remaining

## Files That Need Updates

### 1. src/agents/analyst.py (7 log_event calls)

- Line 186: `log_event("prompt_loaded")` - Can be removed (redundant)
- Line 240: `log_event("analysis_start")` - Keep as `info()` call
- Line 253: `log_event("analysis_receiving")` - Can be removed (redundant)
- Line 277: `log_event("analysis_progress")` - Can be removed or convert to debug
- Line 288: `log_event("analysis_complete")` - Can be removed (redundant)
- Line 299: `log_event("analysis_complete")` - Duplicate, remove
- Line 326: `log_event("analysis_failed")` - Convert to `error()` call

### 2. src/agents/reviewer.py (11 log_event, 1 log_error)

- Line 132: `log_event("review_start")` - Keep as `info()` call
- Line 189: `log_event("review_start")` - Duplicate, remove
- Line 199: `log_event("review_processing")` - Can be removed (redundant)
- Line 207: `log_event("raw_message_...")` - Can be removed (debug noise)
- Line 220: `log_event("review_progress")` - Can be removed or convert to debug
- Line 231: `log_event("reviewer_message_...")` - Can be removed (debug noise)
- Line 253: `log_event("review_stream_end")` - Can be removed (redundant)
- Line 276: `log_event("feedback_validation_failed")` - Convert to `warning()` call
- Line 290: `log_event("feedback_fixed")` - Convert to `info()` call
- Line 298: `log_error()` - Already proper usage, just remove wrapper
- Line 321: `log_event("review_complete")` - Keep as `info()` call
- Line 370: `log_event("review_error")` - Convert to `error()` call

### 3. src/core/message_processor.py (4 log_event calls)

- Line 85: `log_event("sdk_message_...")` - Can be removed (redundant with debug mode)
- Line 107: `log_event("websearch_query")` - Keep as `info()` call (useful)
- Line 172: `log_event("sdk_message")` - Can be removed (redundant with debug mode)
- Line 330: `log_event("websearch_query")` - Duplicate, remove

### 4. src/core/pipeline.py (8 log_event, 4 log_error, 4 log_milestone)

- Line 88: `log_milestone("Pipeline started")` - Convert to `info()` call
- Line 91: `log_event("pipeline_start")` - Can be removed (redundant with milestone)
- Line 158: `log_event("feedback_file_missing")` - Convert to `warning()` call
- Line 172: `log_error()` - Already proper usage, just remove wrapper
- Line 212: `log_event("analysis_saved")` - Convert to `debug()` call
- Line 267: `log_event("iteration_start")` - Convert to `info()` call
- Line 320: `log_error()` - Already proper usage, just remove wrapper
- Line 365: `log_error()` - Already proper usage, just remove wrapper
- Line 384: `log_event("iteration_complete")` - Can be removed (redundant with milestone)
- Line 411: `log_milestone("Iteration X complete")` - Convert to `info()` call
- Line 421: `log_event("analysis_accepted")` - Can be removed (redundant with milestone)
- Line 436: `log_milestone("Analysis accepted")` - Convert to `info()` call
- Line 442: `log_event("analysis_rejected")` - Convert to `info()` call
- Line 511: `log_milestone("Pipeline complete")` - Convert to `info()` call
- Line 514: `log_event("pipeline_complete")` - Can be removed (redundant with milestone)
- Line 543: `log_error()` - Already proper usage, just remove wrapper

## Conversion Strategy

### Phase 1: Replace Essential Logging

Convert the useful logging calls to proper Logger methods:

- WebSearch queries → `logger.info(f"WebSearch #{num}: {query}")`
- Start/complete events → `logger.info("Starting analysis...")`
- Errors → `logger.error(msg, agent, exc_info=True)`
- Milestones → `logger.info(f"🎯 {title}")`

### Phase 2: Remove Redundant Logging

Delete these redundant events entirely:

- Duplicate start/complete events
- "processing" and "receiving" events
- SDK message events (already logged in debug mode)
- Progress events that don't add value

### Phase 3: Clean Up

1. Remove compatibility methods from `src/utils/logger.py`
2. Run tests to ensure nothing breaks
3. Update any documentation

## Summary of Changes Needed

**Keep and convert to proper calls: ~15 calls**

- Analysis/review start messages
- WebSearch queries  
- Error messages
- Key milestones

**Remove entirely: ~24 calls**

- Redundant/duplicate events
- Debug noise
- SDK message tracking (handled by debug mode)

## Testing Plan

1. Run unit tests after each file update
2. Run integration test with `--debug` flag
3. Verify log output is still useful but less noisy

## Expected Benefits

- Remove ~50 lines of compatibility code
- Cleaner, more focused log output
- Better use of log levels (debug vs info vs error)
- More maintainable codebase

---

*Ready for deprecation in next session. Estimated time: 30-45 minutes*
