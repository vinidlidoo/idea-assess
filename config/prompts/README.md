# Prompt Templates

This directory contains all prompt templates for the Business Idea Evaluator agents.

## Directory Structure

```text
config/prompts/
├── shared/              # Shared components (NEW)
│   └── file_edit_rules.md  # Common Read-before-Edit rules
├── agents/              # Active agent prompts
│   ├── analyst/
│   │   ├── system.md    # Primary system prompt (with includes)
│   │   ├── main.md      # Legacy, kept for compatibility
│   │   └── user/        # User prompts (renamed from partials/)
│   │       ├── initial.md       # Initial analysis
│   │       ├── revision.md      # Revision workflow
│   │       ├── constraints.md   # Resource constraints
│   │       ├── websearch_instruction.md
│   │       └── websearch_disabled.md
│   ├── reviewer/
│   │   ├── system.md    # Primary system prompt (with includes)
│   │   ├── main.md      # Legacy, kept for compatibility
│   │   └── user/
│   │       └── review.md        # Review instructions
│   ├── judge/
│   │   └── main.md
│   └── synthesizer/
│       └── main.md
├── versions/            # Historical versions for reference
│   ├── analyst/
│   │   ├── v1.md
│   │   ├── v2.md
│   │   └── v3.md
│   └── reviewer/
│       ├── v1.md
│       └── v1_simple.md
└── archive/             # Deprecated/experimental prompts
```

## Current Active Prompts

- **Analyst**: `agents/analyst/system.md` (v3 with includes)
- **Reviewer**: `agents/reviewer/system.md` (v1 with includes)
- **Judge**: `agents/judge/main.md` (Phase 3)
- **Synthesizer**: `agents/synthesizer/main.md` (Phase 4)

## Naming Conventions

- `main.md` - Primary prompt for each agent
- `{workflow}.md` - Specific workflow prompts (e.g., revision.md)
- `partials/*.md` - Reusable prompt components
- `v{n}.md` - Version numbers for historical prompts

## How Prompts Are Loaded

The system uses a prompt registry (`src/core/prompt_registry.py`) to map old filenames to new locations, ensuring backwards compatibility while maintaining the new organization.

```python
# Example usage
from src.core.file_operations import load_prompt

# Loads from config/prompts/agents/analyst/main.md
prompt = load_prompt("analyst_main.md")

# With custom path
prompt = load_prompt("revision.md", Path("config/prompts/agents/analyst"))
```

## Making Changes

1. **Edit prompts** in the `agents/` directory for active changes
2. **Test thoroughly** before deploying
3. **Keep historical versions** in `versions/` for rollback capability
4. **Document significant changes** in commit messages

## Prompt Versioning

When creating a new version:

1. Copy current `main.md` to `versions/{agent}/v{n}.md`
2. Update `main.md` with new version
3. Update `prompt_registry.py` if filenames change
4. Test the system end-to-end

## Best Practices

1. **Active vs Versioned**: Keep current prompts in `agents/`, historical in `versions/`
2. **Modular Components**: Use `partials/` for reusable prompt segments
3. **Clear Purpose**: Group by agent type for clarity
4. **Version Control**: Move old versions to `versions/` instead of deleting
5. **Documentation**: Each prompt should have a header comment explaining its purpose
