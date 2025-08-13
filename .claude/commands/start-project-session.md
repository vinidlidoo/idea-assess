---
allowed-tools: Bash(date:*), Bash(/Users/vincent/dotfiles/utils/claude-sessions.sh:*), Bash(tree:*), Bash(echo:*), TodoWrite
description: Start a new project work session with session logging
---

# Start a new project work session

## Context

- Current timestamp: !`date '+%Y-%m-%d %H:%M %Z'`
- Latest session log: @!`ls -t session-logs/*.md 2>/dev/null | grep -v TEMPLATE | head -1`
- Current git status: !`git status --short`
- Current branch: !`git branch --show-current`
- Current project file tree: !`tree -L 3`
- Project overview: @requirements.md, @implementation-plan.md
- Latest Claude Code session IDs: !`/Users/vincent/dotfiles/utils/claude-sessions.sh -Users-vincent-Projects-recursive-experiments-idea-assess -n 5`
- Session objective: !`echo "${ARGUMENTS:-No specific objective provided}"`

## Your task

1. Read the project's CLAUDE.md file to understand:
   - Current phase and immediate focus
   - Project overview and constraints
   - Latest session reference

2. Read the latest session log (if exists) to understand:
   - What was completed last time
   - Handoff notes and next priorities
   - Any open questions or blockers

3. Create a new session log in `session-logs/`:
   - Copy from `session-logs/SESSION_TEMPLATE.md`
   - Name format: `YYYY-MM-DD-descriptive-title.md`
   - Fill in Start Time using bash `date` command
   - Add current Claude Code session ID
   - Set Previous Session reference
   - Define clear objectives based on handoff notes
     - If this slash command includes an objective passed as an argument, prioritize it for the session.

4. Use TodoWrite to create initial task list:
   - Based on objectives from session log
   - Break down into specific, actionable items
   - Prioritize based on CLAUDE.md immediate focus

5. Provide brief session plan summary:
   - Main goals for this session
   - Any risks or dependencies to watch for
   - Expected deliverables
   - Ask user for input and don't start until they said to

Note: Keep the session log open for updates throughout the session. You'll finalize it when closing the session.
