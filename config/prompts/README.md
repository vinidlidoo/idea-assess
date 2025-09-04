# Agent Prompts

Agent prompts focus on principles and behavior. Document structure is handled by templates in `config/templates/`.

## Structure

```text
agents/           # Agent-specific prompts
  analyst/        # system.md, tools_system.md, user/, snippets/
  reviewer/       # system.md, tools_system.md, user/
  factchecker/    # system.md, user/
experimental/     # Alternative prompt versions
shared/           # Shared components
versions/         # Historical versions
```

## Usage

- Default: Each agent loads its `system.md`
- Override: `--analyst-prompt experimental/analyst/concise.md`
- Includes: Supports `{{include:path}}` for shared components

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
