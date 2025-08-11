# CLAUDE.md - Project Context for Business Idea Evaluator

## Purpose of This File

This file contains **stable project context** that rarely changes. For detailed work history and specific implementation decisions, see session logs.

## Project Overview

Building an AI-powered business idea evaluation system using Claude SDK and MCP tools. The system takes one-liner business ideas and produces comprehensive market analyses with comparative rankings.

## Current Phase & Focus

**Phase:** Technical Design - Awaiting Review  
**Latest Session:** `session-logs/2025-01-11-claude-sdk-research.md`  
**Immediate Focus:** Get user feedback on architecture design before implementation

## Key Documents

### Core Requirements

- **requirements.md** - Complete requirements specification (READ FIRST)

### Session History

- **session-logs/** - Detailed work logs per session
- Latest: `2025-01-08-archiving-and-setup.md`

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
- MCP protocol for external tools
- Git for version control
- 1.5 week timeline (10 days total)
- Sequential processing (P0), parallel later (P1)

## File Structure

```bash
idea-assess/
├── ideas/
│   └── pending.txt          # Queue of ideas
├── analyses/
│   └── {idea-slug}/
│       ├── analysis.md      # Full analysis
│       ├── evaluation.json  # Grades
│       └── research.md      # Supporting data
├── reports/
│   └── summary-{timestamp}.md
├── config/
│   └── prompts/            # Agent prompts
└── logs/
```

## CLI Commands

- `analyze "<idea>"` - Convert one-liner to analysis
- `grade <slug>` - Evaluate an analysis
- `generate-summary` - Create comparative report

## Development Timeline

- **Days 1-3**: Foundation (SDK setup, CLI, MCP tools)
- **Days 4-7**: Core agents implementation
- **Days 8-10**: Integration, testing, polish

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
