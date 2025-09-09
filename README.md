# Business Idea Evaluator

AI-powered business idea evaluation system using Claude SDK.

## Overview

Transforms one-liner business ideas into comprehensive market analyses through a multi-agent pipeline:

1. **Analyst** - Expands ideas into full analyses with web research
2. **Reviewer** - Provides structured feedback for quality improvement  
3. **FactChecker** - Verifies citations with veto power
4. **Judge** (Phase 3) - Grades on 7 criteria
5. **Synthesizer** (Phase 4) - Comparative reports

## Setup

```bash
# Install dependencies (using uv)
uv pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=your-key-here
```

## Usage

```bash
# Basic analysis
.venv/bin/python -m src.cli "AI-powered fitness app for seniors"

# With review loop
.venv/bin/python -m src.cli "Your idea" --with-review

# With fact-checking (parallel verification)
.venv/bin/python -m src.cli "Your idea" --with-review --with-fact-check

# Without web tools (faster)
.venv/bin/python -m src.cli "Your idea" --no-web-tools
```

### Key Flags

- `--with-review`: Enable reviewer feedback loop
- `--with-fact-check`: Add parallel fact-checker with veto power
- `--no-web-tools`: Disable WebSearch/WebFetch
- `--max-iterations N`: Set iterations (default: 3)
- `--debug`: Detailed logging

## Output Structure

```text
analyses/
└── {idea-slug}/
    ├── analysis.md              # Final analysis
    ├── metadata.json           # Run metadata
    └── iterations/             # All iterations
        ├── iteration_N.md
        ├── reviewer_feedback_iteration_N.json
        └── fact_check_iteration_N.json
```

## Architecture

- **Pipeline**: Orchestrates multi-agent workflow with mode routing
- **Agents**: Type-safe generics `BaseAgent[TConfig, TContext]`
- **Templates**: Structure (templates) separated from behavior (prompts)
- **Parallel Execution**: Reviewer + FactChecker run concurrently
- **Field Standards**: `iteration_recommendation` (approve/revise)

## Status

**✅ Complete**: Analyst, Reviewer, FactChecker agents  
**✅ Tests**: 107 tests, 81% coverage  
**🚧 Phase 3**: Judge agent (grading)  
**📅 Phase 4**: Synthesizer (comparative reports)

## Testing

```bash
# Run tests with coverage
.venv/bin/python -m pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Quick run
pytest tests/unit/ -q
```

## Performance

- **Analysis**: 2-5 minutes with web research
- **Tests**: ~20s for full suite
- **Iterations**: Max 3 by default

## Documentation

- `system-architecture.md` - Technical architecture (840 lines)
- `requirements.md` - Business requirements
- `tests/README.md` - Testing philosophy
- `session-logs/` - Development history
