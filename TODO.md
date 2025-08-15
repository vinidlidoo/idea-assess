# Project-level TODO List

## Features & Enhancements

- [ ] Add the capability to feed a list of ideas in a text file into the system, starting with the Analyze.py file.
- [x] ReFactor Analyze.py to reduce its length and offload utilities and other functions to different files. Prepare the repo for adding the next agent to the mix (COMPLETED 2025-08-14)
- [x] Update the startsession hook to also clean up the logs folder
- [x] Debug why reviewer agent receives UserMessages in response stream (RESOLVED: SDK designed for human interaction)
- [x] Investigate if reviewer prompt complexity causes JSON generation issues (RESOLVED: File-based approach works)  
- [x] Test reviewer with non-alcohol business ideas to rule out content policy issues (TESTED: Works with education platform)
- [x] Clean up old reviewer implementations (COMPLETED 2025-08-14)
- [x] Clean up old pipeline.py (COMPLETED 2025-08-14)
- [x] Update imports in __init__.py files after cleanup (COMPLETED 2025-08-14)
- [ ] Consider future migration to Anthropic API for cleaner agent communication
- [x] Fix critical FeedbackProcessor import bug ✅ COMPLETED 2025-08-14

## Remaining Items from Code Review Assessment

*Reference: @session-logs/code-review-assessment-2025-08-14.md*

### P2 - Medium Priority (Not Yet Completed)

- [ ] __Implement connection pooling__ - Reuse SDK client instances
- [ ] __Break up god method__ - Refactor `run_analyst_reviewer_loop` (200+ lines)
- [ ] __Add JSON schema validation__ - Validate reviewer feedback structure
- [ ] __Use Path objects__ - Replace string paths with Path objects throughout

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

- [ ] __Fix failing tests__ - 7 tests need mock setup fixes
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

- [ ] __Document AgentResult structure__ - Define all fields and their meanings
- [ ] __Document pipeline return values__ - Specify what each method returns
- [ ] __Create README__ - Basic usage instructions and examples
- [ ] __Add inline code comments__ - Explain complex logic sections
- [ ] __Document SDK workarounds__ - Explain why file-based approach is used
- [ ] __Create architecture diagram__ - Visual representation of agent flow

### Refactoring TODOs

- [ ] __Extract ALL inline prompts to separate files__ - Move inline prompts to config/prompts/ for better maintainability:
  - Analyst revision prompt in pipeline.py:109-124
  - Reviewer instructions in reviewer.py:121-134
  - Analyst user prompt in analyst.py:171-176
  - Resource constraints note in analyst.py:164-169
- [ ] __Standardize error handling__ pattern across all agents
- [ ] __Extract common agent logic__ to BaseAgent where appropriate
