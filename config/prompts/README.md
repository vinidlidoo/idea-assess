# Prompt Templates

This directory contains all prompt templates for the Business Idea Evaluator agents.

**Note**: After template decoupling (2025-08-26), prompts now focus solely on principles and approach. Document structure and formatting are handled by templates in `config/templates/`.

## Directory Structure

```text
config/prompts/
├── agents/              # Active agent prompts (principles-focused)
│   ├── analyst/
│   │   ├── system.md    # Analyst principles (73 lines, no structure)
│   │   └── user/        # User prompts for different workflows
│   │       ├── initial.md       # Initial analysis
│   │       ├── revision.md      # Revision workflow (iteration 2+)
│   │       └── constraints.md   # Consolidated resource constraints
│   ├── reviewer/
│   │   ├── system.md    # Reviewer principles (89 lines, no structure)
│   │   └── user/
│   │       └── review.md        # Review instructions
│   ├── judge/          # Phase 3 (future)
│   │   └── system.md
│   └── synthesizer/    # Phase 4 (future)
│       └── system.md
├── shared/             # Shared components
│   └── file_edit_rules.md  # Common file editing rules
├── versions/           # Historical versions (for rollback)
│   ├── analyst/
│   │   ├── v1.md
│   │   ├── v2.md
│   │   └── v3.md
│   └── reviewer/
│       └── v1.md
└── experimental/       # Experimental prompts (testing)
    └── analyst/
        └── concise.md
```

## How Prompts Work After Refactoring

### 1. Default Behavior

- Each agent has a `system.md` file that is loaded by default
- The `prompt_version` in config is currently not used (always loads system.md)
- User prompts are loaded based on workflow needs

### 2. Overriding Prompts

Prompts can be overridden via:

- **CLI flags**: `--analyst-prompt v2` or `--reviewer-prompt strict`
- **Direct config modification**: `analyst_config.prompt_version = "v2"`
- **Context system_prompt**: Set `context.system_prompt = "custom/path.md"`

### 3. Include System

System prompts can include shared components using `{{include:path}}`:

```markdown
{{include:shared/file_edit_rules.md}}
```

## Current Active Prompts

- **Analyst**: `agents/analyst/system.md` (v3 content with includes)
- **Reviewer**: `agents/reviewer/system.md` (v1 content with includes)
- **Judge**: Not implemented (Phase 3)
- **Synthesizer**: Not implemented (Phase 4)

## File Organization Rules

1. **system.md** - Primary prompt for each agent (loaded by default)
2. **user/*.md** - User prompts for specific workflows
3. **shared/*.md** - Reusable components (included via {{include}})
4. **versions/*.md** - Historical versions for reference/rollback
5. **experimental/*.md** - Test prompts not in production

## Making Changes

1. **Edit `system.md`** for agent-specific changes
2. **Edit `shared/*.md`** for cross-agent changes
3. **Test thoroughly** before deploying
4. **Archive old versions** to `versions/` before major changes

## Cleanup Notes (Post-Refactoring)

### Removed/Deprecated

- `main.md` files - No longer used, system.md is the standard
- `archive/` directory - Old experiments moved to versions or deleted
- Complex prompt registry - Simplified to direct file loading

### Simplified

- No more prompt_registry.py mapping
- Direct path resolution in agent_base.py
- Cleaner separation between system and user prompts

## Best Practices

1. **One Source of Truth**: Each agent has one `system.md`
2. **Explicit Includes**: Use `{{include}}` for shared components
3. **Version in Filename**: Historical versions as `v1.md`, `v2.md` etc
4. **Clear Workflow Separation**: User prompts organized by workflow
5. **Document Changes**: Update this README when structure changes
