---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(date:*), Bash(git log:*), Bash(/Users/vincent/dotfiles/utils/claude-sessions.sh:*)
description: Tasks to wrap up the current session using session logs
---
# Tasks to wrap up a session

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`
- Current timestamp: !`date '+%Y-%m-%d %H:%M %Z'`
- Latest Claude Code session IDs: !`/Users/vincent/dotfiles/utils/claude-sessions.sh -Users-vincent-Projects-recursive-experiments-idea-assess -n 5`

## Your task

Based on the above:

1. Delete any test files that were created for troubleshooting and which can be discarded. Log files can stay.

2. Update or create session log in `session-logs/` directory:
   - If session log doesn't exist yet: copy from `SESSION_TEMPLATE.md`
   - If it already exists: update it with final session details
   - Name format: `YYYY-MM-DD-brief-description.md`
   - Fill in all sections based on work completed this session
   - Use actual timestamps from bash `date` command
   - Set end time and ensure all work is documented
   - Make sure the correct Claude Code session ID is entered. Do not change if entered.
   - Mark all commit fields as "end of session" since commit happens at close

3. Update TODO.md with any nice-to-have or papercut tasks that came up during the session

4. Update the project's CLAUDE.md file:
   - Update "Current Phase & Focus" section with latest session reference
   - Update "Immediate Focus" with next priority
   - Keep it minimal - detailed history goes in session logs
   - Do NOT add implementation details or decisions (those go in session log)
   - Add lessons learned from working in the project with this particular user, which would help things go smoother next time

5. Read @requirements.md, @implementation-plan.md, and @system-architecture.md, and update as appropriate to reflect the project's latest state. Also trim and simplify content where it makes sense.

6. Review all changes and create a single git commit:
   - Add all necessary files (check if cwd is a sub-directory)
   - Include session log in the commit
   - Suggest a commit message and ask for user confirmation before committing

7. Final check:
   - Confirm session log captures all important decisions and work
   - Verify CLAUDE.md points to the new session log
   - Ensure handoff notes are clear for next session
