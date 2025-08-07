# CLAUDE.md - Project Context for Business Idea Evaluator

## Project Overview

Building an AI-powered business idea evaluation system using Claude SDK and MCP tools. The system takes one-liner business ideas and produces comprehensive market analyses with comparative rankings.

## Current Status

✅ **Requirements Phase Complete** (2025-08-07)

- Finalized comprehensive requirements document
- Clarified workflow and agent responsibilities
- Defined P0 (MVP) and P1 (future) features

## Key Documents

1. **requirements.md** - Complete requirements specification (READ THIS FIRST)
2. **starter-qa.md** - Q&A that led to requirements refinement
3. **starter-convo-transcript.txt** - Original ideation conversation
4. **work-plan.md** - Initial rough plan (superseded by requirements.md)

## Next Steps

### Immediate Priority: Technical Design Phase

1. **Research Claude SDK capabilities**:
   - Agent patterns and sub-agents
   - MCP protocol integration
   - Hooks and slash commands
   - Review latest Anthropic docs

2. **Design agent architecture**:
   - Define agent interfaces and communication
   - Prompt engineering for each agent
   - Error handling and retry logic

3. **Create implementation plan**:
   - Break down into specific tasks
   - Set up project structure
   - Begin Phase 1 implementation

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

## Questions to Resolve in Design Phase

1. How to structure agent prompts for consistency?
2. Best approach for web search via MCP?
3. How to handle partial failures in pipeline?
4. Optimal checkpoint/resume implementation?

## Owner Preferences

- Direct, concise communication
- Focus on P0 features first
- Git-based version control essential
- Letter grades (A-D) not numeric scores
- Narrative quality > raw data

---

*Last updated: 2025-08-07*
*Phase: Requirements Complete → Design Next*
