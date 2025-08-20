# Agent Refactoring Plan: Analyst and Reviewer

## Architectural Context and Agent Roles

### System Overview

The idea-assess system implements a multi-agent pipeline for evaluating business ideas:

1. **Analyst Agent** - Transforms one-liner ideas into comprehensive analyses
2. **Reviewer Agent** - Provides feedback to improve analysis quality
3. **Judge Agent** (future) - Grades analyses based on evaluation criteria
4. **Synthesizer Agent** (future) - Creates comparative reports across ideas

### Current Agent Responsibilities

#### Analyst Agent (`src/agents/analyst.py`)

**Primary Role:** Research and content generation

- Takes a one-liner business idea as input
- Uses WebSearch to gather market data and competitive intelligence
- Generates a 1000-2500 word structured analysis document
- Handles revisions based on reviewer feedback
- Manages interrupt signals for graceful shutdown

**Key Interactions:**

- Reads feedback files when revising
- Writes analysis markdown files
- Integrates with RunAnalytics for tracking
- Uses Claude SDK for LLM interaction

#### Reviewer Agent (`src/agents/reviewer.py`)

**Primary Role:** Quality assurance and feedback

- Reads completed analyses from files
- Evaluates against quality criteria
- Generates structured JSON feedback
- Recommends accept/reject/conditional for iterations
- Validates feedback structure before saving

**Key Interactions:**

- Reads analysis files (security-validated paths)
- Writes feedback JSON files
- Uses FeedbackValidator for schema compliance
- Integrates with RunAnalytics for tracking

## Current Implementation Issues

### Analyst.py Problems

#### Structural Issues

1. **Unnecessary method separation** - `process()` just wraps `_analyze_idea()` without adding value
2. **Type conversion overhead** - Uses `AnalysisResult` from utils instead of `AgentResult` directly
3. **Complex context extraction** - Revision context handling is verbose and unclear

#### Code Quality Issues

1. **Inconsistent logging** - Mix of print statements and logger calls
2. **Mid-code imports** - `ResultMessage` imported at line 276
3. **Inline prompts** - WebSearch instructions hardcoded instead of in prompt files
4. **Redundant variables** - `tools_to_use`, `client = client_instance`

#### Design Issues

1. **Overly complex interrupt handling** - Could be simplified or moved to base class
2. **Poor progress tracking** - When RunAnalytics is None, tracking becomes useless
3. **Tight coupling** - Direct dependency on `AnalysisResult` type

### Reviewer.py Problems

#### Reviewer Structural Issues

1. **Misplaced utility class** - `FeedbackProcessor` at bottom might belong elsewhere
2. **Redundant validation** - Duplicate checks for feedback structure
3. **Complex metadata extraction** - Lines 256-271 repeat earlier logic

#### Reviewer Code Quality Issues

1. **Hardcoded permissions** - Tools and permission mode hardcoded
2. **Redundant comments** - Several comments add no value
3. **Long method** - `process()` method is 200+ lines

#### Reviewer Design Issues

1. **Two-phase return** - Returns file path as string, caller must read it
2. **Mixed responsibilities** - Validation, file I/O, and LLM interaction in one place

## Proposed Refactoring Changes

### Phase 1: Simplify Analyst Structure

1. **Merge `_analyze_idea()` into `process()`**
   - Eliminate unnecessary indirection
   - Reduce parameter passing
   - Simplify error handling flow

2. **Remove `AnalysisResult` dependency**
   - Return `AgentResult` directly
   - Move slug generation to process method
   - Eliminate type conversion overhead

3. **Clean up error handling**
   - Replace all print statements with logger
   - Move imports to top of file
   - Consolidate exception handling

### Phase 2: Streamline Reviewer Logic

1. **Extract validation logic**
   - Move path validation to utils or base class
   - Consolidate feedback validation
   - Reduce duplication

2. **Simplify metadata handling**
   - Create single metadata builder
   - Remove redundant calculations
   - Use dataclass for structure

3. **Consider extracting FeedbackProcessor**
   - Move to separate module if it grows
   - Or integrate into ReviewerAgent if small

### Phase 3: Extract Common Patterns to BaseAgent

1. **Interrupt handling**
   - Standard signal management
   - Thread-safe event handling
   - Graceful shutdown pattern

2. **SDK client management**
   - Common options setup
   - Standard message processing loop
   - ResultMessage handling

3. **RunAnalytics integration**
   - Standard tracking calls
   - Progress reporting
   - Statistics collection

### Phase 4: Align Agent Interfaces

1. **Standardize return patterns**
   - All agents return `AgentResult`
   - Consistent metadata structure
   - Clear success/failure signals

2. **Unified configuration approach**
   - Common config fields in base
   - Agent-specific extensions
   - Runtime context handling

## Design Principles for Refactoring

1. **Single Responsibility** - Each method should do one thing well
2. **DRY (Don't Repeat Yourself)** - Extract common patterns to base class
3. **Explicit over Implicit** - Clear method names and return types
4. **Fail Fast** - Validate early, clear error messages
5. **Composition over Inheritance** - Use utilities and helpers where appropriate

## Risk Mitigation

1. **Maintain backward compatibility** - Keep external interfaces stable
2. **Incremental changes** - Small, testable refactoring steps
3. **Comprehensive testing** - Update tests as we refactor
4. **Document changes** - Clear commit messages and comments

## Success Criteria

1. **Reduced code duplication** - Common patterns extracted
2. **Improved readability** - Clear, concise methods
3. **Better error handling** - Consistent, informative errors
4. **Maintained functionality** - All existing features work
5. **Easier testing** - Simpler methods are easier to test

## Questions for Consideration

1. Should interrupt handling be optional or always available?
2. Should we create an SDK client wrapper to standardize usage?
3. Should FeedbackProcessor be a separate service or part of Reviewer?
4. How much should we extract to BaseAgent vs. keeping agents independent?
5. Should we create agent-specific exception types?

---

## Final Synthesized Refactoring Plan

After reviewing both analyses and considering practical constraints, here's the actionable plan:

### Phase 1: Core Simplifications (2-3 hours)

- [x] Task 1.1: Organize imports - Move all imports to top of file ✅
- [x] Task 1.2: Merge `_analyze_idea()` into `process()` method ✅
- [x] Task 1.3: Remove AnalysisResult dependency, return AgentResult directly ✅
- [x] Task 1.4: Replace all print statements with logger calls ✅
- [x] Task 1.5: Extract websearch instruction to prompt file ✅
- [x] Task 1.6: Run tests to verify functionality preserved ✅

### Phase 2: Clean Up Code Smells (1 hour)

- [x] Task 2.1: Add clean revision_context property/method ✅
- [x] Task 2.2: Fix progress tracking when run_analytics is None ✅
- [x] Task 2.3: Remove redundant variables (tools_to_use, client assignment) ✅
- [x] Task 2.4: Run tests to verify no regressions ✅

### Phase 3: Deferred (wait for more agents)

- [ ] Extract common patterns to BaseAgent (after Judge/Synthesizer implemented)
- [ ] Standardize interrupt handling across all agents
- [ ] Create unified SDK client wrapper if needed

---

*Execution started: 2025-08-19 14:45 PDT*
