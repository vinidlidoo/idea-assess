# Phased Implementation Plan

## Overview

This plan follows a "start small, validate, iterate" approach. Each phase builds on the previous one, with clear validation criteria before moving forward.

## Phase 1: Analyst-Only Prototype (Days 1-2) ✅ COMPLETE

### Goals

- Get a single agent working end-to-end ✅
- Validate claude-code-sdk integration ✅
- Test prompt engineering with real ideas ✅
- Establish file I/O patterns ✅

### Phase 1 Deliverables

1. **Minimal CLI** (`analyze.py`) ✅
   - Single command: `python analyze.py "AI fitness app"`
   - Argparse implementation complete
   - Direct stdout/file output working

2. **Basic Analyst Agent** ✅
   - Three prompt versions created (`analyst_v1.md`, `v2`, `v3`)
   - Produces 900-1200 word analyses with YC-style focus
   - Structure validated across multiple test ideas

3. **Test Harness** ✅
   - Tested with 10+ diverse ideas
   - Output format validated
   - WebSearch integration working (30-120s per search)

### Phase 1 Validation Criteria

- [x] Can process 5 different ideas without errors
- [x] Output follows expected markdown structure
- [x] WebSearch tool actually retrieves relevant data
- [x] Files saved to correct locations
- [x] Analysis makes logical sense (manual review)

### Phase 1 Architecture Refactoring (2025-08-14) ✅

- **Modularized monolithic code** into clean architecture:
  - `src/utils/` - Text processing, debug logging, file operations
  - `src/core/` - BaseAgent interface, config, message processor
  - `src/agents/` - AnalystAgent implementation
- **Validated by code review**: Architecture ready for Phase 2

### What We're NOT Doing Yet

- No reviewer feedback loop
- No grading or evaluation
- No comparative reports
- No error recovery
- No parallel processing

## Phase 2: Add Reviewer Feedback Loop (Days 3-4)

### Phase 2 Goals

- Implement iterative improvement cycle
- Test Analyst-Reviewer interaction
- Refine feedback format
- Validate iteration stopping logic

### Phase 2 Deliverables

1. **Reviewer Agent**
   - Focused prompt (`prompts/reviewer_v1.md`)
   - JSON feedback format
   - Clear, actionable suggestions

2. **Iteration Controller**
   - Max 3 iterations
   - Tracks version history (v1, v2, v3)
   - Implements stopping conditions

3. **Enhanced Analyst**
   - Accepts and incorporates feedback
   - Shows clear improvements between versions

### Phase 2 Validation Criteria

- [ ] Reviewer provides specific, actionable feedback
- [ ] Analyst successfully incorporates feedback
- [ ] Quality improves across iterations (manual check)
- [ ] Iteration stops at appropriate point
- [ ] All versions properly saved

### Test Cases

1. Weak initial analysis → Should iterate 2-3 times
2. Strong initial analysis → Should iterate 1-2 times
3. Edge case handling (empty feedback, conflicting suggestions)

## Phase 3: Add Judge Evaluation (Days 5-6)

### Phase 3 Goals

- Implement grading system
- Validate evaluation criteria
- Test grade consistency
- Build evaluation pipeline

### Phase 3 Deliverables

1. **Judge Agent**
   - Comprehensive prompt (`prompts/judge_v1.md`)
   - 7 criteria evaluation
   - Letter grades (A-D) with justification

2. **Evaluation Storage**
   - JSON format for grades
   - Detailed justifications
   - Executive summary

3. **Basic CLI Extension**
   - `grade` command
   - Can evaluate existing analyses
   - Batch processing capability

### Phase 3 Validation Criteria

- [ ] Grades are consistent across similar ideas
- [ ] Justifications are evidence-based
- [ ] All 7 criteria properly evaluated
- [ ] JSON format is parseable
- [ ] Executive summary is useful

### Test Matrix

- 10 diverse ideas
- Manual review of grades
- Check for grade inflation/deflation
- Verify criteria independence

## Phase 4: Add Synthesizer for Reports (Days 7-8)

### Phase 4 Goals

- Generate comparative reports
- Compute overall rankings
- Create executive-friendly output
- Complete full pipeline

### Phase 4 Deliverables

1. **Synthesizer Agent**
   - Report generation prompt
   - Ranking algorithm
   - Comparative analysis

2. **Full CLI with Click**
   - All commands integrated
   - Proper error handling
   - Progress indicators

3. **Report Generation**
   - Summary reports with rankings
   - Detailed comparisons
   - Visual formatting (tables)

### Phase 4 Validation Criteria

- [ ] Reports accurately reflect evaluations
- [ ] Rankings are logical and justified
- [ ] Comparisons highlight key differences
- [ ] Format is professional and readable
- [ ] Full pipeline runs end-to-end

## Phase 5: Polish & Optimization (Days 9-10)

### Phase 5 Goals

- Error handling and recovery
- Performance optimization
- Documentation
- Testing suite

### Phase 5 Deliverables

1. **Robustness**
   - Retry logic for API failures
   - Graceful degradation
   - Better error messages

2. **Documentation**
   - README with examples
   - API documentation
   - Troubleshooting guide

3. **Testing**
   - Unit tests for core functions
   - Integration tests for pipeline
   - Performance benchmarks

### Phase 5 Validation Criteria

- [ ] Can handle 20+ ideas in batch
- [ ] Recovers from transient failures
- [ ] Clear documentation
- [ ] 80% test coverage
- [ ] Performance within acceptable limits

## Implementation Notes

### Directory Structure Evolution

**Phase 1 (Minimal)**:

```text
analyze.py
prompts/
  analyst_v1.md
output/
  {idea-slug}.md
```

**Phase 2 (With Reviewer)**:

```text
analyze.py
prompts/
  analyst_v1.md
  reviewer_v1.md
work/
  {idea-slug}/
    analysis_v1.md
    feedback_v1.json
    analysis_v2.md
    ...
```

**Current Structure (Post-Refactor)**:

```text
src/
  core/                 # ✅ IMPLEMENTED
    __init__.py
    agent_base.py       # BaseAgent interface
    config.py          # Configuration management
    message_processor.py # Message handling
  agents/              # ✅ PARTIALLY IMPLEMENTED
    __init__.py
    analyst.py         # ✅ Complete
    reviewer.py        # ⏳ Phase 2
    judge.py          # ⏳ Phase 3
    synthesizer.py    # ⏳ Phase 4
  utils/              # ✅ IMPLEMENTED
    __init__.py
    debug_logging.py
    file_operations.py
    text_processing.py
  cli.py             # ✅ IMPLEMENTED
  analyze.py         # ✅ Thin wrapper
config/
  prompts/
    analyst_v1.md    # ✅
    analyst_v2.md    # ✅
    analyst_v3.md    # ✅
    reviewer.md      # ⏳ Phase 2
    judge.md        # ⏳ Phase 3
    synthesizer.md  # ⏳ Phase 4
analyses/
  {idea-slug}/
    analysis.md
    evaluation.json  # ⏳ Phase 3
reports/
  summary_{timestamp}.md # ⏳ Phase 4
```

### Key Decisions to Make Early

1. **Prompt Management**: Version control strategy for prompts
2. **State Management**: How to track pipeline state between agents
3. **Error Recovery**: What failures to retry vs. fail fast
4. **Output Format**: Exact markdown structure for analyses
5. **WebSearch Fallback**: What if MCP search unavailable?

### Risk Mitigation

1. **WebSearch Unavailability**
   - Fallback: Use mock data for testing
   - Alternative: Implement basic web scraping

2. **Token Limits**
   - Start with shorter analyses (1000 words)
   - Implement chunking if needed

3. **Iteration Loops**
   - Hard stop at 3 iterations
   - Time-based cutoff as backup

4. **Grade Inflation**
   - Calibrate with known good/bad examples
   - Consider relative grading within batch

## Success Metrics

### Phase 1 Success

- Single agent works reliably
- Output quality is reasonable
- Development velocity established

### Phase 2 Success

- Feedback loop demonstrably improves quality
- Iteration count is appropriate
- System remains stable

### Phase 3 Success

- Grades are fair and consistent
- Evaluation adds clear value
- Pipeline remains manageable

### Phase 4 Success

- Reports provide actionable insights
- Full system works end-to-end
- User can evaluate multiple ideas efficiently

### Overall Success

- System processes 10+ ideas reliably
- Quality matches manual analysis
- Development completed within timeline
- Learning objectives achieved

## Next Steps

1. Review and refine this plan
2. Begin Phase 1 implementation
3. Create test ideas list
4. Draft initial Analyst prompt
5. Set up minimal project structure

---

*This is a living document. Update as we learn and adapt.*
