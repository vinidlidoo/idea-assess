# CLAUDE.md - Project Context for Business Idea Evaluator

## Purpose of This File

This file contains **stable project context** that rarely changes. For detailed work history and specific implementation decisions, see session logs.

## Project Overview

Building an AI-powered business idea evaluation system using Claude SDK and MCP tools. The system takes one-liner business ideas and produces comprehensive market analyses with comparative rankings.

## Current Phase & Focus

**Phase:** Phase 2 - Complete with logger transition fully done  
**Latest Session:** `session-logs/2025-08-17-phase3-judge-prep.md`  
**Immediate Focus:** Q&A session on architecture, then Phase 3 Judge prep when requested
**Note:** Logger refactoring complete - all compatibility methods removed successfully

## Key Documents

### Core Requirements

- **requirements.md** - Complete requirements specification (READ FIRST)

### Session History

- **session-logs/** - Detailed work logs per session
- Latest: `2025-08-17-phase3-judge-prep.md`
- Key sessions:
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
│   └── prompts/            # Agent prompts (v1, v2, v3)
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
- **Days 3-4**: Phase 2 - Add Reviewer feedback loop ⏳ CURRENT
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
