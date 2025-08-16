# Project-level TODO List

## Critical Issues (P0) - From Expert Assessment

*Reference: @session-logs/expert-recommendations-summary.md*

- [x] **Fix silent iteration 2 failures** - ✅ COMPLETED 2025-08-15 - Added proper file naming and error logging
- [x] **Fix memory leak in MessageProcessor** - ✅ COMPLETED 2025-08-15 - Implemented rolling buffer with size limits
- [x] **Fix race condition in signal handling** - ✅ COMPLETED 2025-08-15 - Now only uses thread-safe event
- [x] **Fix path traversal vulnerability** - ✅ COMPLETED 2025-08-15 - Uses proper path resolution validation

## High Priority (P1) - Core Functionality

- [ ] **Refactor god method** - Break up `run_analyst_reviewer_loop` (200+ lines)
- [ ] **Implement proper error boundaries** - Add custom exception hierarchy with context
- [x] **Add JSON schema validation** - ✅ COMPLETED 2025-08-15 - Validates and auto-fixes feedback
- [ ] **Fix incorrect permission mode** - Change 'default' to 'allow' in SDK calls
- [ ] **Add correlation IDs** - For request tracing across agents

## Features & Enhancements

- [x] ~~Implement and integrate the improved logging system~~ ✅ COMPLETED 2025-08-15
- [ ] Fix the awkward prompt registry file mapping in src/core/prompt_registry.py
- [ ] Implement batch processing mode for multiple ideas
- [ ] Add progress indicators for long operations
- [ ] Add utility to feed a list of ideas from a text file into the system
- [ ] Consider adding timeout handling for virtual interior design tests (consistently timeout)

## Remaining Items from Code Review Assessment

*Reference: @session-logs/code-review-assessment-2025-08-14.md*

### P2 - Medium Priority (Not Yet Completed)

- [ ] **Use Path objects** - Replace string paths with Path objects throughout (discuss with user why it's needed first)

### P3 - Nice to Have (Future)

- [ ] **Add performance monitoring** - Track operation durations and resource usage
- [ ] **Create CLI documentation** - Document all commands and options
- [ ] **Add configuration guide** - Document all config options
- [ ] **Define error codes** - Create consistent error code system
- [ ] **Consider merging FeedbackProcessor** - Evaluate if it belongs in ReviewerAgent
- [ ] **Implement stream buffering** - More efficient message processing
- [ ] **Add health checks** - Verify system dependencies before running
- [ ] **Create docker support** - Containerize for consistent environments
- [ ] **Add CI/CD pipeline** - Automated testing and deployment
- [ ] **Implement prompt caching** - Reduce token usage for repeated system prompts
- [ ] **Add circuit breakers** - For resilience in agent communication
- [ ] **Optimize token usage** - Context window management

### Testing TODOs

- [x] **Create comprehensive test script** - ✅ COMPLETED 2025-08-15
  - Created test_locally.sh with 8 test scenarios
  - Successfully tested Level 1 (basic functionality)
- [x] **Run Level 2 tests** - ✅ COMPLETED 2025-08-15
  - All reviewer tests passing after bug fixes
- [ ] **Create real integration tests** - Test with actual Claude SDK (not mocks)
- [ ] **Run Level 3 tests** - Full features with WebSearch
- [ ] **Fix failing unit tests** - 7 tests need mock setup fixes
- [ ] **Add missing unit tests**:
  - [ ] Slug generation
  - [ ] Constants usage
  - [ ] Message processor parsing (especially memory leak fix)
  - [ ] Debug logger functionality
  - [ ] Signal handler synchronization
- [ ] **Add edge case tests**:
  - [ ] Empty idea input
  - [ ] Very long idea input (>500 chars)
  - [ ] Special characters in idea
  - [ ] Unicode in idea text
  - [ ] Concurrent pipeline runs
  - [ ] File permission errors
  - [ ] Network failures during WebSearch
  - [ ] Iteration 2 file missing scenarios
  - [ ] Corrupted JSON feedback files

### Documentation TODOs

- [x] **Create prompt documentation** - ✅ COMPLETED 2025-08-15
  - Created comprehensive README.md in config/prompts/
- [ ] **Document AgentResult structure** - Define all fields and their meanings
- [ ] **Document pipeline return values** - Specify what each method returns
- [ ] **Create main README** - Basic usage instructions and examples
- [ ] **Add inline code comments** - Explain complex logic sections
- [ ] **Document SDK workarounds** - Explain why file-based approach is used
- [ ] **Create architecture diagram** - Visual representation of agent flow

### Refactoring TODOs

- [x] **Extract ALL inline prompts to separate files** - ✅ COMPLETED 2025-08-15
  - Moved to config/prompts/agents/ with organized structure
- [x] **Reorganize prompts directory** - ✅ COMPLETED 2025-08-15
  - Created agents/, versions/, archive/ structure
- [x] **Repository cleanup** - ✅ COMPLETED 2025-08-15
  - Archived old analyses, research docs, removed unused code
- [x] **Remove unused dependencies** - ✅ COMPLETED 2025-08-15
  - Removed async_file_operations, unused timeout constants
- [ ] **Standardize error handling** pattern across all agents
- [ ] **Extract common agent logic** to BaseAgent where appropriate
