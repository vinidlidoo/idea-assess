# CLAUDE.md - Project Context for Business Idea Evaluator

## Purpose of This File

This file contains **stable project context** that rarely changes. For detailed work history and specific implementation decisions, see session logs.

## Project Overview

Building an AI-powered business idea evaluation system using Claude SDK and MCP tools. The system takes one-liner business ideas and produces comprehensive market analyses with comparative rankings.

## Current Phase & Focus

**Phase:** Phase 2 - COMPLETE (implementation finished, citation accuracy fixed)
**Latest Session:** `session-logs/2025-08-27-citation-accuracy-phase2-polish.md`
**Immediate Focus:** FactChecker agent implementation (parallel citation verification)
**Status:** Two-phase workflow with verification, 90% citation accuracy achieved
**Note:** Next: Add dedicated FactChecker agent before Phase 3 Judge implementation

## Key Documents

### Core Requirements

- **requirements.md** - Complete requirements specification (READ FIRST)

### Session History

- **session-logs/** - Detailed work logs per session
- Latest: `2025-08-26-prompt-standardization.md`
- Key sessions:
  - `2025-08-26-prompt-standardization.md` - Prompt standardization, tools in system prompts, observability
  - `2025-08-26-citation-accuracy-improvements.md` - Citation accuracy 2.5x improvement, fact-checker spec
  - `2025-08-26-template-implementation.md` - Implemented template decoupling, fixed turn efficiency
  - `2025-08-21-utils-cleanup-complete.md` - Utils cleanup, removed 75% dead code, fixed critical bugs
  - `2025-08-20-prompt-refactor-iteration-fixes.md` - Fixed iteration numbering, implemented prompt includes
  - `2025-08-19-agent-deep-dive-qa.md` - Aligned agents, fixed websearch bug, removed dead code
  - `2025-08-19-runanalytics-complete.md` - Completed RunAnalytics implementation
  - `2025-08-19-reviewer-schema-fix.md` - Fixed reviewer feedback schema mismatch
  - `2025-08-18-phase3-judge-architecture.md` - Q&A session, completed Phase 2 logger refactoring
  - `2025-08-17-phase3-judge-prep.md` - Completed logger transition, removed all compatibility methods
  - `2025-08-17-logger-refactor-complete.md` - Unified 3 logger classes into 1, added SDK error awareness
  - `2025-08-16-phase3-judge-implementation.md` - Type safety improvements, zero errors achieved
- **implementation-plan.md** - Phased implementation strategy (Phase 1 ✅, Phase 2 mostly complete)

### Archive

- **archive/initial-planning/** - Original planning documents

## Critical Workflow Understanding

The system workflow is:

1. **Input**: One-liner idea (e.g., "AI-powered fitness app")
2. **Analyze**: Analyst agent expands to full document
3. **Review**: Reviewer agent improves quality
4. **Grade**: Judge agent evaluates (A-D grades)
5. **Summarize**: Synthesizer agent creates comparative report

## Four Distinct Agents

- **Analyst**: Research + write full analysis from one-liner
- **Reviewer**: Feedback to improve analysis quality
- **Judge**: Grade based on 7 evaluation criteria
- **Synthesizer**: Generate comparative summary reports

## Technical Constraints

- Python CLI using Claude SDK
- Python package management via `uv`
- API key from console.anthropic.com (pay-as-you-go)
- MCP protocol for external tools
- Git for version control
- 1.5 week timeline (10 days total)
- Sequential processing (P0), parallel later (P1)

## Current File Structure

```bash
idea-assess/
├── src/                     # ✅ Modularized architecture
│   ├── core/               # BaseAgent, config, message processor
│   ├── agents/             # AnalystAgent (+ future agents)
│   ├── utils/              # Utilities extracted from monolith
│   ├── cli.py             # Modern CLI implementation
│   └── analyze.py         # Thin wrapper for compatibility
├── ideas/
│   └── pending.txt          # Queue of ideas
├── analyses/
│   └── {idea-slug}/
│       ├── analysis.md      # Full analysis
│       ├── evaluation.json  # Grades (Phase 3)
│       └── research.md      # Supporting data (Future)
├── reports/
│   └── summary-{timestamp}.md  # (Phase 4)
├── config/
│   ├── prompts/            # Agent prompts (simplified, principles-focused)
│   └── templates/          # File templates with structure
└── logs/
    └── debug_{timestamp}.json  # Debug logs
```

## CLI Commands

- `analyze "<idea>"` - Convert one-liner to analysis
- `grade <slug>` - Evaluate an analysis
- `generate-summary` - Create comparative report

## Development Timeline

- **Days 1-2**: Phase 1 - Analyst-only prototype ✅ COMPLETE
  - Analyst v1, v2, v3 prompts developed
  - Architecture refactored to modular design
  - BaseAgent interface implemented
  - Ready for multi-agent system
- **Days 3-4**: Phase 2 - Add Reviewer feedback loop ✅ COMPLETE
  - Template decoupling system implemented
  - Prompts simplified to focus on principles
  - File operations consolidated
- **Days 5-6**: Phase 3 - Add Judge evaluation
- **Days 7-8**: Phase 4 - Add Synthesizer, full pipeline
- **Days 9-10**: Phase 5 - Polish, documentation, testing

## Important Notes

- User prefers aggressive timelines
- Emphasis on learning Claude SDK features
- Word limits enforce clarity
- Evidence-based reasoning is critical
- Each agent must have clear, unique role

## Owner Preferences

- Direct, concise communication
- Focus on P0 features first
- Git-based version control essential
- Letter grades (A-D) not numeric scores
- Narrative quality > raw data
- Aggressive timelines preferred
- Emphasis on learning Claude SDK features

## Session Workflow

1. **Start**: Read this file + latest session log
2. **Work**: Track progress in todos, make changes
3. **End**: Create new session log from template
4. **Update**: Update "Current Phase & Focus" section here

---

*CLAUDE.md is for stable context. Session logs are for detailed history.*

## Added via memorize command

- always activate the virtual environment before running python files
- use `fd` not `find`, `ripgrep` not `grep`, `uv` not `pip`, `zoxide` not ``
- all files in session-logs/ should begin with creation date in the YYYY-MM-DD format

## Python Environment - CRITICAL

**Virtual Environment Location**: `.venv` (not `venv`)
**Python Command**: `.venv/bin/python` (not `python` or `python3`)
**Package Manager**: `uv pip install` (not `pip` or `pip3`)
**Package Name**: `claude-code-sdk` (not `claude-code-sdk-python`)
**CLI Execution**: `.venv/bin/python -m src.cli` (not `python src/cli.py`)
**CLI Flags**:

- `--no-web-tools` (not `--no-websearch`)
- `--analyst-prompt` expects relative path from prompts dir

## Lessons Learned Working with This User

- **Start simple, iterate** - User prefers minimal working solutions over complex perfect ones
- **Show don't tell** - User wants to see actual test results, not just descriptions
- **Challenge assumptions** - Simplifications like "WebSearch/WebFetch always together" save complexity
- **Direct feedback style** - User will say "you're not getting it" to redirect approach
- **Leverage existing utilities** - Don't reinvent wheels, use load_prompt_with_includes etc.
- **Aggressive timelines** - User pushes for rapid iteration and simplification
- **Test in background** - Use `run_in_background: true` for long-running tests
- **Verify results** - User wants to see WebFetch verification of claims, not just trust
- **Explicit > implicit** - Agent needs clear "you MUST do X" rather than suggestions
