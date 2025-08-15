# Project-level TODO List

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

- [ ] __Break up god method__ - Refactor `run_analyst_reviewer_loop` (200+ lines)
- [ ] __Add JSON schema validation__ - Validate reviewer feedback structure
- [ ] __Use Path objects__ - Replace string paths with Path objects throughout (discuss with user why it's needed first)

### P3 - Nice to Have (Future)

- [ ] __Add performance monitoring__ - Track operation durations and resource usage
- [ ] __Create CLI documentation__ - Document all commands and options
- [ ] __Add configuration guide__ - Document all config options
- [ ] __Define error codes__ - Create consistent error code system
- [ ] __Consider merging FeedbackProcessor__ - Evaluate if it belongs in ReviewerAgent
- [ ] __Add progress indicators__ - Show progress during long operations
- [ ] __Implement stream buffering__ - More efficient message processing
- [ ] __Add health checks__ - Verify system dependencies before running
- [ ] __Create docker support__ - Containerize for consistent environments
- [ ] __Add CI/CD pipeline__ - Automated testing and deployment

### Testing TODOs

- [x] __Create comprehensive test script__ - ✅ COMPLETED 2025-08-15
  - Created test_locally.sh with 8 test scenarios
  - Successfully tested Level 1 (basic functionality)
- [x] __Run Level 2 tests__ - ✅ COMPLETED 2025-08-15
  - All reviewer tests passing after bug fixes
- [ ] __Run Level 3 tests__ - Full features with WebSearch
- [ ] __Fix failing unit tests__ - 7 tests need mock setup fixes
- [ ] __Add missing unit tests__:
  - [ ] Slug generation
  - [ ] Constants usage
  - [ ] Message processor parsing
  - [ ] Debug logger functionality
- [ ] __Add edge case tests__:
  - [ ] Empty idea input
  - [ ] Very long idea input (>500 chars)
  - [ ] Special characters in idea
  - [ ] Unicode in idea text
  - [ ] Concurrent pipeline runs
  - [ ] File permission errors
  - [ ] Network failures during WebSearch

### Documentation TODOs

- [x] __Create prompt documentation__ - ✅ COMPLETED 2025-08-15
  - Created comprehensive README.md in config/prompts/
- [ ] __Document AgentResult structure__ - Define all fields and their meanings
- [ ] __Document pipeline return values__ - Specify what each method returns
- [ ] __Create main README__ - Basic usage instructions and examples
- [ ] __Add inline code comments__ - Explain complex logic sections
- [ ] __Document SDK workarounds__ - Explain why file-based approach is used
- [ ] __Create architecture diagram__ - Visual representation of agent flow

### Refactoring TODOs

- [x] __Extract ALL inline prompts to separate files__ - ✅ COMPLETED 2025-08-15
  - Moved to config/prompts/agents/ with organized structure
- [x] __Reorganize prompts directory__ - ✅ COMPLETED 2025-08-15
  - Created agents/, versions/, archive/ structure
- [x] __Repository cleanup__ - ✅ COMPLETED 2025-08-15
  - Archived old analyses, research docs, removed unused code
- [x] __Remove unused dependencies__ - ✅ COMPLETED 2025-08-15
  - Removed async_file_operations, unused timeout constants
- [ ] __Standardize error handling__ pattern across all agents
- [ ] __Extract common agent logic__ to BaseAgent where appropriate
