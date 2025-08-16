# Expert Recommendations Summary

## Critical Issues to Fix Immediately (P0)

### 1. ~~Wrong SDK for Agent Communication~~ (DESIGN DECISION - KEEPING ClaudeSDKClient)

**Note**: After review, we're intentionally keeping `ClaudeSDKClient` for simplicity
**Rationale**: The file-based workflow (queries → deterministic file writes/reads) works well and keeps implementation simpler
**Status**: No change needed - continue with current approach

### 2. Silent Iteration 2 Failures  

**Issue**: Pipeline silently falls back to iteration 1 feedback when iteration 2 files missing
**Impact**: Users get incorrect results without knowing pipeline failed
**Fix**: Add explicit validation and logging for feedback file operations

### 3. Memory Leak in Message Processing

**Issue**: `result_text` list in MessageProcessor grows unbounded
**Impact**: Long-running analyses consume excessive memory
**Fix**: Implement rolling buffer with size limits

## High Priority Issues (P1)

### 4. Race Condition in Signal Handling

**Issue**: Signal handler modifies shared state without synchronization
**Impact**: Interrupts can cause crashes or undefined behavior
**Fix**: Use thread-safe operations, handle cleanup in main async context

### 5. God Method Needs Refactoring

**Issue**: `run_analyst_reviewer_loop` is 200+ lines with poor separation
**Impact**: Extremely difficult to debug and maintain
**Fix**: Extract iteration logic, create dedicated file management class, implement state machine

### 6. Inadequate Error Context

**Issue**: Generic exception handling loses critical debugging information
**Impact**: Can't determine which agent failed or why
**Fix**: Custom exception hierarchy with operation context

## Medium Priority Improvements (P2)

### 7. Missing JSON Schema Validation

**Issue**: No validation of reviewer feedback structure
**Impact**: Malformed feedback can cause silent failures
**Fix**: Implement structured output with ResponseSchema

### 8. Path Traversal Security Risk

**Issue**: Vulnerable path validation in reviewer using string comparison
**Impact**: Potential security vulnerability
**Fix**: Use proper path resolution and validation

### 9. No Integration Tests

**Issue**: All tests use mocks, missing real-world failure modes
**Impact**: Bugs only discovered in production
**Fix**: Create test fixtures with real Claude SDK

### 10. Incorrect Permission Mode

**Issue**: Using 'default' permission mode which doesn't exist
**Impact**: May cause unexpected SDK behavior
**Fix**: Use 'allow' for automated workflows

## Recommended Implementation Order

### Phase 1: Critical Fixes (1-2 days)

1. Fix silent iteration 2 failures (MOST CRITICAL)
2. Fix memory leak in MessageProcessor
3. Implement proper error boundaries
4. Fix signal handling race conditions

### Phase 2: Refactoring & Resilience (2-3 days)

1. Refactor god method into manageable components
2. Add JSON schema validation
3. Fix signal handling race conditions
4. Add correlation IDs for tracing

### Phase 3: Testing & Optimization (2-3 days)

1. Create real integration tests
2. Implement prompt caching
3. Add circuit breakers
4. Optimize token usage with context management

## Key SDK Best Practices to Adopt

1. **Continue with ClaudeSDKClient**: Keep current file-based approach for simplicity
2. **Enable prompt caching**: Reduce token usage for repeated system prompts
3. **Implement structured outputs**: Use ResponseSchema instead of parsing JSON
4. **Add context window management**: Track and limit context size proactively
5. **Batch tool calls**: Use parallel execution for multiple operations

## Quick Wins (Can do immediately)

- Fix permission mode: Change 'default' to 'allow'
- Add checkpoint files for debugging failed runs
- Implement correlation IDs for request tracing
- Add buffer size limits to prevent memory leaks
- Log warnings when falling back to previous iteration

## Code Quality Metrics to Track

- Error recovery rate
- Average response time per agent
- Memory usage over time
- Token usage per analysis
- Iteration success rate

This prioritized list provides a clear roadmap for improving the codebase based on both expert assessments.
