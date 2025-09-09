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

# Set API key (alternatively, directly login to Claude Code)
export ANTHROPIC_API_KEY=your-key-here

# Activate virtual environment
source .venv/bin/activate
```

## Usage

```bash
# Basic analysis
python -m src.cli "AI-powered fitness app for seniors"

# With review loop
python -m src.cli "Your idea" --with-review

# With review and fact-checking (parallel verification)
python -m src.cli "Your idea" --with-review-and-fact-check

# Without web tools (faster)
python -m src.cli "Your idea" --no-web-tools

# Batch processing of files in ideas/
python -m src.cli --batch --max-concurrent 3
```

### Key Flags

- `--with-review` (`-r`): Enable reviewer feedback loop
- `--with-review-and-fact-check` (`-rf`): Enable both reviewer and fact-checker (parallel)
- `--no-web-tools` (`-n`): Disable WebSearch/WebFetch
- `--max-iterations N` (`-m`): Set review iterations (default: 3)
- `--batch` (`-b`): Process multiple ideas from `ideas/pending.md`
- `--debug`: Detailed logging

## Output Structure

```text
analyses/
└── {idea-slug}/
    ├── analysis.md              # Final analysis (copy of latest iteration)
    └── iterations/             # All iterations
        ├── iteration_N.md
        ├── reviewer_feedback_iteration_N.json
        └── fact_check_iteration_N.json

logs/
├── runs/                       # Individual pipeline runs
│   └── {timestamp}_{slug}/
│       ├── run_analytics.json
│       └── messages.jsonl
└── batch/                      # Batch processing logs
    └── {timestamp}_batch/
```

## Pipeline Modes

The system supports different analysis modes:

1. **Basic Analysis** (default)
   - Input → Analyst → Output
   - Single pass, no review

2. **With Review** (`--with-review`)
   - Input → Analyst → Reviewer → [Approve/Revise]
   - Iterative improvement based on feedback
   - Defaults to 3 iterations (configurable)

3. **With Review and Fact-Check** (`--with-review-and-fact-check`)
   - Input → Analyst → [Parallel: Reviewer + FactChecker] → [Both Approve/Either Rejects]
   - Reviewer and FactChecker run in parallel
   - Either agent can force revision (veto power)
   - Ensures both quality and accuracy

## Architecture

- **Pipeline**: Orchestrates multi-agent workflow with mode routing
- **Agents**: Type-safe generics `BaseAgent[TConfig, TContext]`
- **Templates**: Structure (templates) separated from behavior (prompts)
- **Parallel Execution**: Reviewer + FactChecker run concurrently
- **Field Standards**: `iteration_recommendation` (approve/revise)

## Status

**✅ Complete**: Analyst, Reviewer, FactChecker agents  
**✅ Tests**: 134 tests, 80% coverage  
**✅ Batch**: Concurrent processing of 2-5 ideas  
**🚧 Phase 3**: Judge agent (grading)  
**📅 Phase 4**: Synthesizer (comparative reports)

## Testing

```bash
# Run tests with coverage
python -m pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Quick run
pytest tests/unit/ -q
```

## Performance

- **Analysis**: 5-10 minutes per iteration
- Feedback: 10-15 minutes per iteration

## Documentation

- `system-architecture.md` - Technical architecture (840 lines)
- `requirements.md` - Business requirements
- `tests/README.md` - Testing philosophy
