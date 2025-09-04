# Implementation Plan

## Current Status

**Phase 2.5**: Extending core functionality  
**Completed**: Analyst, Reviewer, FactChecker agents  
**Next**: Additional Phase 2.5 features, then Judge (Phase 3)

## ✅ Phase 1: Analyst Agent (COMPLETE)

### Phase 1 Deliverables

- Single agent with WebSearch integration
- Modular architecture (`src/core`, `src/agents`, `src/utils`)
- 1000+ word analyses with market research
- CLI with argparse

### Phase 1 Components

- `src/agents/analyst.py` - Core analysis agent
- `config/prompts/agents/analyst/` - System and user prompts
- `config/templates/agents/analyst/` - Document templates

## ✅ Phase 2: Reviewer Feedback (COMPLETE)

### Phase 2 Deliverables

- Iterative refinement with max 3 iterations
- JSON feedback with structured recommendations
- File-based agent communication
- Template-prompt separation

### Phase 2 Components

- `src/agents/reviewer.py` - Review agent
- Feedback format: `iteration_recommendation` field
- Pipeline modes: `ANALYZE_AND_REVIEW`

## ✅ Phase 2.5: Core Extensions (PARTIAL)

### Completed Features

#### FactChecker Agent ✅

- Parallel citation verification
- Veto power over iterations
- WebFetch-based verification
- Runs alongside Reviewer

#### Test Infrastructure ✅

- 107 unit tests, 81% coverage
- ~20s execution time
- Strategic mocking at boundaries
- Field standardization complete

#### Documentation ✅

- system-architecture.md (840 lines)
- All READMEs updated
- Test philosophy documented

### In Progress / Planned

- [ ] **Iteration Resumption**: Resume analyst-reviewer loop from previous checkpoint when re-running same idea slug instead of starting over

- [ ] **Human-in-the-Loop Feedback**: Allow human feedback insertion into review cycle via `human_feedback.md` file

- [ ] **Enhanced Reviewer**: Give reviewer agent WebSearch/WebFetch capabilities to verify claims and improve feedback quality

- [ ] **Batch Processing**: Process multiple ideas concurrently from `ideas/pending.txt` input file

- [ ] **Cost Analytics**: Track and display total API token costs per analysis in metadata and analysis footer

## 🚧 Phase 3: Judge Evaluation

### Phase 3 Goals

- Letter grades (A-D) on 7 criteria
- Evidence-based scoring
- Structured evaluation storage

### Planned Implementation

1. **Judge Agent** (`src/agents/judge.py`)
   - Evaluation prompt with criteria
   - Grade calculation logic
   - JSON output format

2. **CLI Extension**
   - `--with-judge` flag
   - Batch grading capability

3. **Output**
   - `evaluation.json` with grades
   - Detailed justifications
   - Executive summary

### Validation Criteria

- [ ] Consistent grading across similar ideas
- [ ] Evidence-based justifications
- [ ] All 7 criteria evaluated
- [ ] Clear grade rationale

## 📅 Phase 4: Synthesizer Reports

### Phase 4 Goals

- Comparative analysis across multiple ideas
- Executive-friendly summaries
- Ranking algorithms

### Planned Components

1. **Synthesizer Agent** (`src/agents/synthesizer.py`)
2. **Report Generation** (`reports/summary_{timestamp}.md`)
3. **Batch Processing Support**

## 📅 Phase 5: Polish & Scale

### Phase 5 Goals

- Production readiness
- Performance optimization
- Comprehensive documentation

### Focus Areas

- Error recovery and retry logic
- Parallel processing for multiple ideas
- API rate limiting and cost tracking
- Advanced prompt engineering

## Current Architecture

```text
src/
├── core/           # BaseAgent, config, pipeline, types
├── agents/         # analyst, reviewer, fact_checker
├── utils/          # file_ops, logging, validation
└── cli.py          # Main interface

config/
├── prompts/        # Agent prompts (behavior)
└── templates/      # Document templates (structure)

analyses/
└── {idea-slug}/
    ├── analysis.md (symlink)
    └── iterations/
```

## Pipeline Modes

1. `ANALYZE` - Analyst only
2. `ANALYZE_AND_REVIEW` - With reviewer loop
3. `ANALYZE_REVIEW_WITH_FACT_CHECK` - Parallel verification
4. `ANALYZE_REVIEW_AND_JUDGE` - With grading (Phase 3)
5. `FULL_EVALUATION` - All agents (Phase 4)

## Key Design Decisions

- **Type Safety**: Generics for agents `BaseAgent[TConfig, TContext]`
- **Field Standards**: `iteration_recommendation` (approve/revise)
- **Template Pattern**: Structure (templates) vs behavior (prompts)
- **Parallel Execution**: Reviewer + FactChecker concurrency
- **File-based Communication**: Reliability over speed

## Success Metrics

### System Performance

- Analysis time: 2-5 minutes
- Test execution: ~20s
- Code coverage: >80%

### Quality Metrics

- Iteration improvement rate
- Citation accuracy
- Grade consistency (Phase 3)

## Next Immediate Steps

1. Define additional Phase 2.5 features
2. Implement selected features
3. Validate with real-world testing
4. Begin Phase 3 planning

---

_Living document - updated as implementation progresses_
