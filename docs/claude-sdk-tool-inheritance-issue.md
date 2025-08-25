# Claude SDK Tool Inheritance Issue Analysis

**Date:** 2025-08-25  
**Issue:** Analyst agent shows all parent session tools in system message despite `allowed_tools` restriction  
**Status:** Root cause identified, workarounds available  

## Executive Summary

When running the idea-assess pipeline inside a Claude Code session, the analyst agent's system message shows ALL tools from the parent Claude Code session (20+ tools) instead of just the specified tools (e.g., only `["WebSearch"]`). This occurs because the Claude SDK subprocess inherits the entire parent environment.

## The Problem

### Observed Behavior

- **Expected:** Analyst with `allowed_tools=["WebSearch"]` should only show WebSearch in system message
- **Actual:** System message shows all parent session tools: Task, Bash, Glob, Grep, LS, WebSearch, MCP tools, etc.

### Test Case

Running test #7 from `test_locally.sh`:

```bash
# Test 7: websearch_debug
python -m src.cli "AI-powered fitness app for seniors" --debug
```

## Root Cause Analysis

### 1. Environment Inheritance

The Claude SDK's `SubprocessCLITransport` spawns a subprocess that inherits the entire parent environment:

```python
# In subprocess_cli.py connect() method:
self._process = await anyio.open_process(
    cmd,
    stdin=PIPE,
    stdout=PIPE,
    stderr=self._stderr_file,
    cwd=self._cwd,
    env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "sdk-py"},  # <-- Inherits everything
)
```

### 2. Command Construction

The SDK correctly passes the `--allowedTools` flag:

```python
if self._options.allowed_tools:
    cmd.extend(["--allowedTools", ",".join(self._options.allowed_tools)])
```

### 3. The Disconnect

- The `--allowedTools` flag IS being passed to the CLI
- BUT the subprocess inherits the parent Claude Code session context via environment
- The system message generation uses the inherited context, not the restricted list
- Tool restriction might work at execution time, but the system message is misleading

## Code Flow

```text
1. CLI sets: analyst_config.allowed_tools = ["WebSearch"]
2. Pipeline creates AnalystContext (no tools specified, relies on config)
3. Analyst gets tools from config: allowed_tools = ["WebSearch"]
4. ClaudeCodeOptions created with allowed_tools=["WebSearch"]
5. SDK spawns subprocess with --allowedTools WebSearch
6. Subprocess inherits parent env with all tools available
7. System message shows all inherited tools (bug)
```

## Evidence

### From messages.jsonl

```json
{
  "tools": [
    "Task", "Bash", "Glob", "Grep", "LS", "ExitPlanMode", 
    "Read", "Edit", "MultiEdit", "Write", "NotebookEdit", 
    "WebFetch", "TodoWrite", "WebSearch", "BashOutput", 
    "KillBash", "mcp__context7__resolve-library-id", 
    "mcp__context7__get-library-docs"
  ]
}
```

### From debug logs

```text
Analyst options: allowed_tools=['WebSearch'], max_turns=20
```

## Impact

1. **Confusing logs:** System message doesn't reflect actual restrictions
2. **Unclear security boundary:** Hard to verify if tools are actually restricted
3. **Debugging difficulty:** Can't trust system message for tool availability

## Potential Solutions

### Solution 1: Clean Environment (Recommended)

Create subprocess with minimal environment instead of inheriting all:

```python
clean_env = {
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", ""),
    "USER": os.environ.get("USER", ""),
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
    # Only essential vars
}
# Pass clean_env instead of {**os.environ, ...}
```

### Solution 2: SDK Flag

Check if SDK supports isolation flag:

```python
options = ClaudeCodeOptions(
    allowed_tools=allowed_tools,
    extra_args={"isolated": None}  # Hypothetical
)
```

### Solution 3: Verify Execution Restriction

Test if restriction works at execution time despite system message:

```python
# Try to use unauthorized tool - should fail
await client.query("Run bash command: ls")  # Should fail if only WebSearch allowed
```

## Workarounds

### Current Workaround

Accept that system message is misleading but trust that execution-time restriction works. Add logging to verify:

```python
logger.debug(f"Analyst configured with tools: {allowed_tools}")
logger.warning("System message may show all inherited tools - ignore this")
```

### Testing Outside Claude Code

Run tests in regular terminal (not inside Claude Code) to avoid inheritance:

```bash
# In regular terminal, not Claude Code
./test_locally.sh
```

## Related Code Locations

- **Tool configuration:** `src/agents/analyst.py:62-66`
- **Options creation:** `src/agents/analyst.py:144-150`
- **SDK subprocess:** `claude_code_sdk/_internal/transport/subprocess_cli.py:connect()`
- **CLI configuration:** `src/cli.py:111` (sets `allowed_tools = []` for no-websearch)
- **Default config:** `src/core/config.py:54` (default `["WebSearch"]`)

## TODO Items

This confirms the existing TODO item:
> "The allowed-tools Claude Code Options field doesn't seem to work as expected"

## Recommendations

1. **Short term:** Document this as a known issue, add warning in logs
2. **Medium term:** Test if execution-time restriction works despite system message
3. **Long term:** File bug report with Claude SDK team for proper fix

## Test Commands

```bash
# Test with WebSearch (default)
python -m src.cli "AI fitness app" --debug

# Test without WebSearch  
python -m src.cli "AI fitness app" --no-websearch --debug

# Check logs
grep "allowed_tools" logs/runs/*/debug.log
grep '"tools":' logs/runs/*/messages.jsonl
```

## Conclusion

This is a legitimate bug in the Claude SDK's handling of nested sessions. The SDK correctly passes the `--allowedTools` flag, but the subprocess inherits the parent session's full tool context through environment variables. The system message incorrectly reflects the inherited tools rather than the restricted set.

The actual tool restriction might still work at execution time (needs testing), but the system message is misleading and makes debugging difficult.
