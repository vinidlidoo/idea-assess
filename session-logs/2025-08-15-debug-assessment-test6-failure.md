# Debug Assessment: Test 6 Failure - Virtual Interior Design AR

## Executive Summary

Test 6 (review_multi) for Virtual Interior Design AR is producing empty logs and failing with UNKNOWN status. The test command executes but produces no output before the 180-second timeout, indicating a critical early-stage failure that prevents any logging from occurring.

## Critical Issues

### 1. Silent Failure Pattern

**Location**: Test execution immediately after launch  
**Evidence**: Empty output.log and debug.log files (0 bytes)  
**Impact**: Complete loss of observability into failure cause  

The test executes: `timeout --foreground 180 python src/cli.py "Virtual interior design using AR" --no-websearch --with-review --max-iterations 2`

But produces absolutely no output, not even initial connection messages or startup logs.

### 2. Race Condition in Logger Initialization

**Location**: `src/core/pipeline.py` lines 68-76  
**Pattern**: Conditional logger creation based on TEST_HARNESS_RUN environment variable  

```python
if os.environ.get('TEST_HARNESS_RUN') == '1':
    logger = None
else:
    logger = StructuredLogger(run_id, slug, run_type) if debug else None
```

**Issue**: When TEST_HARNESS_RUN=1, logger is None, but test 6 doesn't use --debug flag, so logger would be None anyway. This creates a double-null scenario.

### 3. Early Exception in Pipeline

**Location**: `src/core/pipeline.py` run_analyst_reviewer_loop method  
**Critical Path**: Lines 67-84 (initialization phase)  
**Risk**: Any exception before line 108 (try block) will cause silent failure:

- create_slug() failure on special characters
- Path operations before try block
- Archive manager initialization issues

### 4. Stdout/Stderr Capture Issue

**Location**: `test_locally.sh` line 101  
**Command**: `timeout --foreground 180 python src/cli.py "$idea" $flags 2>&1 | tee "$log_file"`  
**Problem**: If the Python process crashes immediately or gets stuck in initialization, the pipe to tee might not capture anything.

## Potential Failure Points

### 1. Import-Time Failures

- Circular imports between modules
- Missing dependencies for reviewer functionality
- Import errors that occur before any logging is initialized

### 2. Slug Generation Edge Case

**Function**: `create_slug()` in `src/utils/text_processing.py`  
**Input**: "Virtual interior design using AR"  
**Risk**: Special handling of "AR" or character limits might cause issues

### 3. File System Race Conditions

- Multiple tests running in parallel accessing same directories
- Archive manager trying to move files that don't exist yet
- Permission issues on newly created directories

### 4. Async Event Loop Issues

- Event loop already running when test 6 starts
- Uncaught exceptions in async context
- Deadlock in reviewer agent initialization

## Testing Gaps

### 1. No Pre-Execution Validation

- Missing verification that all required directories exist
- No checks for environment setup before main execution
- No fallback logging for catastrophic failures

### 2. Insufficient Error Boundaries

- No top-level exception handler in CLI entry point
- Missing try-catch around critical initialization code
- No emergency logging mechanism for startup failures

### 3. Test Isolation Issues

- Tests share file system state
- No cleanup between test runs
- Potential interference from previous test artifacts

## Debuggability Improvements

### Logging Strategy

#### 1. Add Emergency Logger

```python
# At very start of cli.py
import sys
import traceback

def emergency_log(msg):
    with open('/tmp/idea-assess-emergency.log', 'a') as f:
        f.write(f"{datetime.now()}: {msg}\n")
    print(f"EMERGENCY: {msg}", file=sys.stderr)

try:
    # All imports and main code
except Exception as e:
    emergency_log(f"Catastrophic failure: {e}\n{traceback.format_exc()}")
    raise
```

#### 2. Add Startup Markers

Before any complex operations:

```python
print(f"[STARTUP] CLI starting with args: {sys.argv}", flush=True)
print(f"[STARTUP] Environment: TEST_HARNESS_RUN={os.environ.get('TEST_HARNESS_RUN')}", flush=True)
```

#### 3. Defensive Logger Creation

```python
# Always create a basic logger, even in test mode
if os.environ.get('TEST_HARNESS_RUN') == '1':
    logger = MinimalLogger()  # Logs to stderr only
else:
    logger = StructuredLogger(...) if debug else MinimalLogger()
```

### Error Handling

#### 1. Wrap Main Entry Point

```python
def main():
    try:
        # Existing CLI code
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)
```

#### 2. Add Initialization Guards

```python
# In pipeline.py, before line 67
try:
    slug = create_slug(idea)
except Exception as e:
    print(f"Failed to create slug for '{idea}': {e}", file=sys.stderr)
    slug = "fallback-slug-" + datetime.now().strftime('%Y%m%d_%H%M%S')
```

### Observability

#### 1. Process Health Check

Add a heartbeat mechanism:

```python
def heartbeat(msg="alive"):
    print(f"[HEARTBEAT] {datetime.now()}: {msg}", flush=True)
```

#### 2. Resource Monitoring

Track file handles and memory:

```python
import resource
def log_resources():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    print(f"[RESOURCES] Memory: {usage.ru_maxrss}, Files: {len(os.listdir('/proc/self/fd'))}")
```

## Resilience Recommendations

### 1. Implement Fail-Fast Pattern

- Add startup validation phase
- Check all dependencies before processing
- Verify file system permissions upfront

### 2. Add Circuit Breaker for Claude API

- Detect repeated connection failures
- Implement exponential backoff
- Provide clear failure messages

### 3. Improve Test Robustness

- Add per-test timeout handling
- Implement test result verification
- Create test-specific temporary directories

### 4. Add Graceful Degradation

- Fallback to simpler prompts on failure
- Skip optional features when errors occur
- Continue with partial results when possible

## Priority Actions

### 1. **Add Emergency Logging** (Critical - Immediate)

Add stderr-based emergency logging at the very start of cli.py to capture any startup failures. This will immediately reveal what's happening in test 6.

### 2. **Fix Logger Initialization** (High - Next Hour)

Ensure a logger is ALWAYS created, even if minimal, to maintain observability. The current dual-null condition (TEST_HARNESS_RUN=1 AND no --debug flag) leaves the system completely blind.

### 3. **Add Startup Validation** (High - Today)

Implement a validation phase that checks:

- All required directories exist and are writable
- Configuration files are present and valid
- Claude API is reachable
- No conflicting processes or locks

### 4. **Wrap Entry Points** (Medium - This Session)

Add comprehensive try-catch blocks around:

- CLI main() function
- Pipeline initialization
- Each agent's process() method

### 5. **Improve Test Isolation** (Medium - Next Session)

- Use unique temporary directories per test
- Clean up before and after each test
- Add mutex/locking for shared resources

## Root Cause Hypothesis

Most likely cause: **The combination of TEST_HARNESS_RUN=1 environment variable and missing --debug flag creates a null logger scenario, followed by an exception in the pipeline initialization (possibly in create_slug or archive_manager) that occurs before the try block, resulting in a silent crash with no output.**

The specific trigger for "Virtual interior design using AR" might be:

1. The slug generation handling "AR" specially
2. Archive manager finding existing files from a previous failed run
3. A race condition with test 5 which might still be cleaning up

## Progress Update - Investigation Results

### What We've Fixed So Far

1. **Added Emergency Logging** ✅
   - Added startup markers to cli.py
   - Added stderr output throughout execution path
   - Now we can see execution reaches the SDK message loop

2. **Fixed Print Statement Buffering** ✅
   - Changed all print() to use file=sys.stderr, flush=True
   - Prevents output buffering when stdout is redirected

3. **Fixed MessageProcessor Logger Bug** ✅
   - Line 186: Added None check before logger.log_event()
   - Prevents AttributeError when logger is None

4. **Traced Execution Path** ✅
   - Execution reaches client.receive_response() loop
   - Receives at least one SystemMessage
   - Then hangs after processing SystemMessage

### Current Hang Point

```text
[ANALYST] Starting receive_response loop...
[ANALYST] Received message type: SystemMessage
<HANGS HERE>
```

### Key Discovery

The hang occurs AFTER receiving SystemMessage but BEFORE processing completes. This means:

- The SDK connection is working
- The async loop is functioning
- The issue is likely in message processing logic

### Critical Observation

**Tests 4 & 5 work** (--max-iterations 1)
**Test 6 fails** (--max-iterations 2)

But the hang is still in iteration 1! This suggests the issue isn't about iteration count, but something environmental.

## Comprehensive Fix Strategy

### Phase 1: Precise Hang Location (IMMEDIATE - 5 mins)

Add debug markers around EVERY line in the message processing loop:

```python
async for message in client.receive_response():
    print(f"[1] Received: {type(message).__name__}", file=sys.stderr, flush=True)
    
    if self._interrupted:  # Check this
        print("[2] Checking interrupt", file=sys.stderr, flush=True)
        
    print("[3] Calling processor.process_message", file=sys.stderr, flush=True)
    processed = processor.process_message(message)
    print(f"[4] Processed: {processed.message_type}", file=sys.stderr, flush=True)
    
    print("[5] Getting stats", file=sys.stderr, flush=True)
    stats = processor.get_statistics()
    print(f"[6] Stats: {stats}", file=sys.stderr, flush=True)
    
    # Continue for all branches...
```

### Phase 2: Root Cause Analysis (10 mins)

Based on Phase 1, investigate:

1. **If hang at [3]**: MessageProcessor.process_message has an issue
   - Check for None access
   - Check for infinite loop
   - Check for blocking I/O

2. **If hang at [5]**: Statistics calculation issue
   - Division by zero?
   - Infinite recursion?

3. **If hang between messages**: SDK protocol issue
   - Missing acknowledgment?
   - Awaiting user input?

### Phase 3: Targeted Fix Implementation

Likely fixes based on pattern:

1. **Progress interval issue**: `stats['message_count'] % self.config.progress_interval`
   - If progress_interval is 0, this causes ZeroDivisionError
   - Fix: Add guard `if self.config.progress_interval > 0:`

2. **Message processing exception**:
   - Wrap in try/catch with proper error reporting
   - Continue loop on non-fatal errors

3. **Async deadlock**:
   - Check for blocking operations in async context
   - Ensure all awaits are properly handled

### Phase 4: Verification Protocol

1. Test the specific fix
2. Run test 6 in isolation
3. Run full test suite
4. Document the root cause

## ACTUAL ROOT CAUSE FOUND

### The Real Issue: Incorrect Revision Prompt Design

After running the test with extended timeout, the test DOES NOT hang - it runs but has a fundamental design flaw:

1. **Iteration 1 works correctly**:
   - Analyst generates analysis
   - Reviewer provides feedback
   - Both complete successfully

2. **Iteration 2 has wrong design**:
   - Pipeline passes the ENTIRE revision prompt template as the "idea" to analyze
   - Analyst receives: `"# Analyst Revision Prompt\n\nPlease revise your analysis..."`
   - This causes the analyst to have a conversation trying to read files
   - Multiple UserMessage/AssistantMessage exchanges occur (15+ messages)
   - The analyst is using its tools (Read/Write) instead of just generating text

### Evidence from Test Output

```text
[ANALYST] Analyzing: # Analyst Revision Prompt

Please revise your analysis based on the reviewer feedback.

ORIGINAL IDEA: Virtual interior design using AR

PREVIOUS ANALYSIS FILE: analyses/virtual-interior-design-using-ar/iterations/iteration_1.md
REVIEWER FEEDBACK FILE: analyses/virtual-interior-design-using-ar/reviewer_feedback.json
```

### The Code Problem

In `src/core/pipeline.py` lines 142-156:

```python
else:
    # Refined analysis based on feedback
    # Load revision prompt template and format it
    revision_template = load_prompt("revision.md", Path("config/prompts/agents/analyst"))
    analyst_input = revision_template.format(
        idea=idea,
        current_analysis_file=current_analysis_file,
        latest_feedback_file=latest_feedback_file
    )
```

The pipeline is passing the revision instructions as the user input, when it should be:

- Passing the original idea as input
- Using a different system prompt for revision mode
- OR passing the feedback in a structured way the analyst understands

### Why This Causes Problems

1. The analyst treats revision instructions as a business idea
2. It tries to use Read/Write tools (which it has access to)
3. This creates a long conversation instead of a single analysis
4. The test appears to "hang" but is actually having a conversation

## RECOMMENDED SOLUTION

### Design Philosophy Issue

The current design conflates two concepts:

1. **User Input**: What the user/system is asking for (the business idea)
2. **Agent Instructions**: How to process that input (analyze vs. revise)

The revision.md template is trying to change BOTH, which breaks the agent's expected input format.

### Option 1: Keep Simple, Use Original Idea (RECOMMENDED)

**Implementation**:

```python
# In pipeline.py, lines 142-156
else:
    # For revisions, pass the original idea with feedback context
    analyst_input = idea  # Keep using the original idea
    
    # Pass feedback and previous analysis via kwargs
    kwargs['revision_mode'] = True
    kwargs['previous_analysis'] = current_analysis_file
    kwargs['reviewer_feedback'] = latest_feedback_file
```

**Why this works**:

- Analyst always receives a business idea as input
- Revision logic handled internally by the analyst
- No confusion about what to analyze

### Option 2: Use Different System Prompts

**Implementation**:

- Create `analyst_revision_v3.md` system prompt
- Switch prompts based on iteration:

```python
if iteration_count == 1:
    prompt_version = "v3"
else:
    prompt_version = "revision_v3"
```

**Why this might not work well**:

- Requires analyst to support dynamic prompt switching
- More complex to maintain

### Option 3: Embed Feedback in User Input (NOT RECOMMENDED)

**Implementation**:

```python
else:
    # Embed feedback directly in the idea description
    analyst_input = f"{idea}\n\n[Previous iteration feedback: {feedback_summary}]"
```

**Why to avoid**:

- Mixes concerns
- Can confuse the analyst about what to analyze

### Immediate Fix

For now, to make test 6 work:

```python
# In pipeline.py line 141-156
if iteration_count == 1:
    analyst_input = idea
else:
    # TEMPORARY FIX: Just pass the original idea again
    # TODO: Implement proper revision handling
    analyst_input = idea
    
    # The analyst won't see the feedback yet, but at least
    # it will generate a valid analysis instead of having
    # a conversation with itself
```

This will at least let the test complete properly while a proper revision mechanism is designed.

## Verification Steps

1. Apply the immediate fix to pipeline.py
2. Run test 6 with longer timeout:

```bash
export TEST_HARNESS_RUN=1
python src/cli.py "Virtual interior design using AR" --no-websearch --with-review --max-iterations 2 --debug
```

2. Add print statement at very start of cli.py:

```python
print(f"CLI STARTING: {sys.argv}", file=sys.stderr, flush=True)
```

3. Check for existing analyses directory conflicts:

```bash
ls -la analyses/virtual-interior-design-using-ar*/
```

4. Monitor process execution:

```bash
strace -f -e trace=open,write python src/cli.py "Virtual interior design using AR" --no-websearch --with-review --max-iterations 2
```
