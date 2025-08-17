# Logger Redesign Discussion

## Current State Analysis

### What We Have Now

- **BaseStructuredLogger** (408 lines) - Creates 4 files per run:
  - `summary.md` - Human-readable timeline
  - `events.jsonl` - Structured events  
  - `metrics.json` - Final metrics
  - `debug.log` - Python logging output
  - Plus: archive management, complex formatting
  
- **StructuredLogger** (74 lines) - Thin wrapper, barely extends base

- **ConsoleLogger** (170 lines) - Separate implementation for test output

### Problems

1. Too many files created per run
2. Duplicate EventData TypedDict definitions  
3. Complex type unions (`StructuredLogger | ConsoleLogger`)
4. Overly complex for simple logging needs
5. Archive management feels premature

## Proposed Simplified Requirements

### Core Principle

Keep it simple - only log what's actually useful for debugging and analysis.

### Two Output Modes

1. **Console + Log File** (Always Active)
   - Everything printed to stderr also goes to a `.log` file
   - Simple text format, timestamps included
   - One file per run: `logs/YYYYMMDD_HHMMSS_<slug>.log`

2. **Debug Message Capture** (When debug_mode=True)
   - Full SDK messages saved to `.jsonl` file  
   - One file per run: `logs/YYYYMMDD_HHMMSS_<slug>_messages.jsonl`
   - Already implemented in MessageProcessor._log_message_details()

### What We're Removing

- ❌ `summary.md` - Redundant with console/.log output
- ❌ `metrics.json` - Can extract from events if needed
- ❌ `events.jsonl` - Most events just duplicate console output
- ❌ Archive management - Let filesystem handle it
- ❌ LoggingContext manager - Overengineered
- ❌ Milestone tracking - Just use regular log messages
- ❌ Complex time formatting - Keep it simple

### Simplified Logger Interface

```python
class Logger:
    """Simple logger that writes to console and file."""
    
    def __init__(self, 
                 run_id: str,
                 slug: str,
                 console_output: bool = True):
        """
        Args:
            run_id: Timestamp for this run
            slug: Idea slug or test name
            console_output: Whether to also print to stderr
        """
        self.log_file = Path(f"logs/{run_id}_{slug}.log")
        self.console_output = console_output
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        # Format: [2025-08-17 09:23:45] [ANALYST] INFO: Message here
        
    def log_error(self, error: str, traceback: str | None = None):
        """Log an error with optional traceback."""
        
    def finalize(self):
        """Close file handles if needed."""
```

### Usage Patterns

```python
# In AnalystAgent
logger = Logger(run_id, slug, console_output=not quiet_mode)
logger.log("[ANALYST] Starting analysis", "INFO")
logger.log(f"[ANALYST] WebSearch: {query}", "INFO")
logger.log("[ANALYST] Analysis complete", "INFO")

# In MessageProcessor (separate concern)
if debug_mode:
    # Write SDK messages to separate JSONL file
    with open(f"logs/{run_id}_{slug}_messages.jsonl", "a") as f:
        f.write(json.dumps(serialized_message) + "\n")
```

### Key Decisions

1. **Single Logger class** - No inheritance, no protocols, just one simple class
2. **Text-based logging** - Easier to tail, grep, read
3. **Separate debug messages** - MessageProcessor handles SDK message logging independently
4. **No structured events** - If we need metrics, parse the log file
5. **Test mode** - Just sets `console_output=False` or redirects stderr

## Questions to Resolve

1. **Do we need log levels?** (INFO, WARNING, ERROR, DEBUG)
   - Pro: Standard practice, easy filtering
   - Con: Adds complexity
   - Alternative: Just prefix messages with [ERROR], [WARNING] etc.

A: Yes, log levels are needed.

2. **Should we keep ANY structured logging?**
   - Current: Complex event tracking with data dictionaries
   - Proposed: Just formatted text messages
   - Middle ground: Keep simple key=value pairs in log messages?

A: formatted text msgs is enough

3. **How to handle test output?**
   - Option A: Test harness sets console_output=False
   - Option B: Test harness redirects stderr
   - Option C: Test harness uses a different log directory

A: Need more information here to make a decision

4. **File organization?**
   - Current: `logs/runs/TIMESTAMP_slug/` with multiple files
   - Proposed: `logs/TIMESTAMP_slug.log` flat structure
   - Alternative: `logs/YYYY-MM-DD/TIMESTAMP_slug.log` daily folders?

A: need to separate runs from tests using logs/runs and logs/tests like we're doing right now. timestamp_slug is good. with test number prefix when running the tests (like we're doing right now)

5. **What about the existing log_event() calls?**
   - We have many calls like `logger.log_event("analysis_start", "Analyst", {...})`
   - Option A: Convert to simple log() calls
   - Option B: Keep log_event() but simplify to just format and print
   - Option C: Remove most of them, keep only essential ones

A: Option C. Need help to understand the benefits of log_event() over log(). pls explain

## Implementation Plan

### Phase 1: Create and Test New Logger

1. [x] Create `src/utils/logger.py` with the new Logger class
2. [x] Add unit tests for Logger in `tests/unit/test_logger.py`
3. [x] Run tests to ensure Logger works correctly (22/22 pass)

### Phase 2: Update Core Components

4. [x] Update `src/core/message_processor.py` to use new Logger
   - [x] Remove TYPE_CHECKING imports for old loggers
   - [x] Update constructor to accept Logger instead of union types
   - [x] Keep log_event calls for now (compatibility)
   - [x] Fixed SDK message logging to write to separate JSONL file
5. [x] Run existing message_processor tests to ensure compatibility (9/9 pass)

### Phase 3: Update Agents

6. [ ] Update `src/agents/analyst.py` to use new Logger
   - [ ] Replace StructuredLogger with Logger
   - [ ] Replace ConsoleLogger with Logger  
   - [ ] Convert log_event calls to log() calls
   - [ ] Remove redundant logging
7. [ ] Update `src/agents/reviewer.py` to use new Logger (if it exists)
8. [ ] Update `src/core/agent_base.py` if needed
9. [ ] Run agent tests to ensure everything works

### Phase 4: Update Pipeline and CLI

10. [ ] Update `src/pipeline.py` to use new Logger
11. [ ] Update `src/cli.py` if it uses logging
12. [ ] Test the full pipeline with a real analysis

### Phase 5: Cleanup

13. [ ] Remove `src/utils/base_logger.py`
14. [ ] Remove `src/utils/improved_logging.py`
15. [ ] Remove `src/utils/console_logger.py`
16. [ ] Remove prototype files (`logger_prototype.py`, `logger_v2_prototype.py`)
17. [ ] Update any remaining imports throughout the codebase
18. [ ] Run all tests to ensure nothing broke

### Phase 6: Integration Testing

19. [ ] Run a full analysis with debug mode to test message logging
20. [ ] Run test harness to ensure test logging works
21. [ ] Verify log files are created in correct directories
22. [ ] Check that SDK errors are properly captured

### Key Considerations

- **SDK Integration**: Ensure we properly handle SDK message types (UserMessage, AssistantMessage, SystemMessage, ResultMessage)
- **SDK Error Types**: Import and handle specific errors from `claude_code_sdk._errors`:
  - `CLINotFoundError` - Claude Code not installed
  - `CLIConnectionError` - Can't connect to Claude Code
  - `ProcessError` - CLI process failed (has exit_code and stderr)
  - `CLIJSONDecodeError` - Malformed JSON response
  - `MessageParseError` - Invalid message structure
- **Backwards Compatibility**: Keep log_event() temporarily to avoid breaking everything at once
- **Test Coverage**: Run tests after each phase to catch issues early
- **Error Handling**: Use exc_info=True for proper traceback logging
- **File Organization**: Maintain logs/runs/ and logs/tests/ structure

### SDK Error Handling Strategy

```python
from claude_code_sdk._errors import (
    CLINotFoundError,
    CLIConnectionError, 
    ProcessError,
    CLIJSONDecodeError,
    MessageParseError
)

try:
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            # process message
            
except CLINotFoundError as e:
    logger.error("Claude Code is not installed. Please install it first.", "Analyst")
    # Fail fast - no point retrying
    
except CLIConnectionError as e:
    logger.error(f"Cannot connect to Claude Code: {e}", "Analyst")
    # Could retry with exponential backoff
    
except ProcessError as e:
    logger.error(f"Claude Code process failed (exit code {e.exit_code})", "Analyst")
    if e.stderr:
        logger.debug(f"Process stderr: {e.stderr}", "Analyst")
    
except (CLIJSONDecodeError, MessageParseError) as e:
    logger.error(f"Invalid response from Claude Code: {e}", "Analyst")
    # Log the problematic data for debugging
    
except Exception as e:
    # Generic fallback for unexpected errors
    logger.error("Unexpected error", "Analyst", exc_info=True)
```

## Vincent's Input Needed

- Which questions above need decisions?
- Any critical logging features I'm missing?
- Preferences on file organization?
- Should we prototype the new Logger first before changing everything?
