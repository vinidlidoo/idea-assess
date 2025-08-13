# WebSearch Timeout Investigation

## Problem Description

When using claude-code-sdk to run our analyzer script, WebSearch operations show progressively longer delays and eventually timeout:

- First WebSearch: ~33 seconds to complete
- Second WebSearch: ~52 seconds to complete  
- Third WebSearch: Times out (never completes)

## Evidence Collected

### 1. Session File Analysis

WebSearch durations vary significantly across sessions:

```json
Session d21f053b: 32.7s, 51.8s (timeout on 3rd)
Session ae03985d: 31.8s, 43.3s, 24.7s (completed!)
Session 1a9b97ee: 48.1s, 50.2s (timeout on 3rd)
Session 1dff2580: 112.6s (timeout on 2nd)
Session 93d9797f: 48.1s (single search)
```

**Key finding**: Some sessions complete 3+ searches, others timeout on 2nd

### 2. Debug Log Timing

From `debug_20250812_181629.json`:

- Message flow stops after second WebSearch UserMessage at 96.7s
- Our 120s timeout triggers while waiting for next AssistantMessage

### 3. GitHub Issues Found

While searching, I found these related issues:

- #1608: "Persistent API Timeout During Search Request"
- #2728: "Constantly seeing 'API Error (Request timed out...)'"
- #2489: "Timeout waiting after 1000ms in claude-code CLI"

However, these seem to be about API timeouts, not the progressive delay pattern we're seeing.

## Key Observations

1. **Claude Code CLI works fine with multiple WebSearches in an interactive session**, but SDK-initiated sessions experience variable, often extreme delays

2. **WebSearch durations are highly inconsistent**:
   - Sometimes 30-50s per search
   - Sometimes 112s+ for a single search
   - Some sessions complete 3+ searches, others timeout on the 2nd

3. **Not a simple progressive delay pattern** - it's more erratic

This suggests the issue is NOT a general WebSearch bug but something specific to:

1. How the SDK spawns the CLI subprocess
2. How the SDK communicates with the CLI
3. Session state accumulation in SDK-initiated sessions
4. Differences in how the CLI handles interactive vs programmatic usage

## Potential Causes

### Theory 1: Subprocess Buffer Issues

The SDK uses subprocess pipes for communication. WebSearch results are large and might be causing buffer issues that get progressively worse.

### Theory 2: Session State Accumulation  

Each SDK run creates a new session file. There are 35+ session files accumulated. Maybe state from these sessions is affecting performance.

### Theory 3: Different CLI Modes

The CLI might behave differently when launched programmatically vs interactively. The SDK uses `--output-format stream-json` and `--input-format stream-json` flags.

### Theory 4: Async/Await Handling

The SDK's async message handling might not be properly consuming messages, causing a backlog that slows down subsequent operations.

## What We DON'T Know

1. Why does the delay increase progressively?
2. Why does it work fine in interactive Claude Code but not via SDK?
3. Is this specific to our environment or a general SDK issue?
4. Why does the third WebSearch never complete?

## Next Steps for Investigation

1. **Test with minimal reproduction case**: Create simplest possible script that just does 3 WebSearches
2. **Compare CLI flags**: Run CLI manually with same flags SDK uses
3. **Monitor system resources**: Check if memory/CPU usage increases during searches
4. **Test session cleanup**: Try deleting old session files and testing again
5. **Check subprocess communication**: Log raw stdin/stdout to see if messages are getting stuck

## Resolution

**The timeout was caused by Claude Code's Bash tool timeout, not the script itself.**

Key findings:

- analyze.py has no inherent timeout - it will wait as long as needed
- WebSearch via SDK is slow (30-120s per search) but DOES complete
- The timeouts we observed were from running the script through Claude Code's Bash tool
- When run directly in terminal, the script completes successfully

## Final Implementation

The analyze.py script now:

- Has NO timeout restrictions (will wait for WebSearch to complete)
- Includes `--debug` flag for detailed message logging to `logs/`
- Properly handles WebSearch delays by simply waiting
- Works correctly when run directly: `python src/analyze.py "idea" --debug`

## Questions for Further Investigation

1. Does the issue occur with other tools or just WebSearch?
2. Does it happen with all models (Opus, Sonnet, Haiku)?
3. Is there a correlation with the size of WebSearch results?
4. Could this be related to token limits or context window management?

---

*Note: This is NOT a confirmed Claude Code bug, but rather an issue specific to SDK-CLI interaction that needs further investigation.*
