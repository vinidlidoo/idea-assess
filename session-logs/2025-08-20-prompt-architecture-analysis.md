# Prompt Architecture Analysis

**Date**: 2025-08-20
**Context**: Investigating how prompt variants should work with the config system

## The Problem

The CLI is directly modifying config objects instead of using the context override pattern:

- Line 97-100: Modifying `config.analyst.prompt_variant`
- Line 112-114: Modifying `config.analyst.default_tools`

But the config.py design intends for:

- Configs to be immutable after startup
- Contexts to provide runtime overrides via `prompt_version_override` and `tools_override`

## Current Architecture Issues

### 1. Two Different Prompt Systems

**File-Based System (Current Default)**

- `config/prompts/agents/analyst/system.md` - Uses file editing
- Includes `{{include:shared/file_edit_rules.md}}`
- Expects agents to Read/Edit files

**Direct Output System (v1, v2, v3)**

- `config/prompts/versions/analyst/analyst_v3.md` - Direct text output
- Has "CRITICAL: Do NOT use any file tools"
- Outputs analysis as plain text

These are **fundamentally incompatible** approaches!

### 2. Config Modification Anti-Pattern

**Current (Wrong)**:

```python
# CLI modifies config directly
config.analyst.prompt_variant = "v3"
config.analyst.default_tools = []
```

**Should Be**:

```python
# Create context with overrides
analyst_context = AnalystContext(
    prompt_version_override="v3",
    tools_override=[]  # Explicit empty list, not None
)
```

### 3. The Pipeline Problem

The pipeline creates contexts but doesn't pass through the overrides:

```python
# Current in pipeline.py
analyst_context = AnalystContext(
    idea_slug=self.slug,
    output_dir=self.output_dir,
    iteration=self.iteration_count,
)
# Missing: prompt_version_override and tools_override!
```

## The Deeper Issue

The v3 prompt (and v1, v2) are from an **earlier architecture** where:

- Agents output text directly
- No file editing was involved
- The pipeline captured stdout

But the **current architecture** assumes:

- Pipeline pre-creates files
- Agents edit those files
- File-based communication between agents

## How Prompts Are Loaded

Looking for where prompts are actually loaded...

1. **BaseAgent** has `load_system_prompt()` method
2. This likely uses `prompt_variant` or `prompt_version_override`
3. Need to check how it resolves the actual file path

## Proposed Solutions

### Option 1: Support Both Modes (Complex)

- Detect if prompt is file-based or direct-output
- Pipeline handles differently based on mode
- Agents have different process flows

### Option 2: Migrate Everything to File-Based (Recommended)

- Convert v1, v2, v3 prompts to use file editing
- Consistent architecture throughout
- Keep historical versions in archive/

### Option 3: Fix the Override Pattern (Minimum)

- Stop modifying config in CLI
- Pass overrides through pipeline to context
- Let agents handle the prompt selection

## Immediate Fix Needed

1. **CLI** should create override values, not modify config
2. **Pipeline** should pass overrides to context creation
3. **Agents** should use context overrides if present

## Critical Questions

1. Do we want to support both file-based and direct-output modes?
2. Should v1/v2/v3 prompts be converted to file-based?
3. How should the prompt file resolution work?

## Next Steps

1. Check how BaseAgent.load_system_prompt() works
2. Decide on architecture (dual-mode vs single-mode)
3. Implement proper override pattern
4. Test with different prompt variants

---

*This is a fundamental architectural issue that needs resolution before proceeding*

## Proposed Solution: CLI-Based Prompt Override System

**Date**: 2025-08-20
**Updated**: After research and alignment with user requirements

### Requirements

1. Support experimental prompts in a separate folder structure
2. Allow CLI to override any agent's prompt with custom system prompts
3. Keep existing versions (v1, v2, v3) for historical reference
4. Maintain clear separation between stable and experimental prompts

### Current Prompt Resolution Logic

Based on agent_base.py analysis:

```python
def get_prompt_path() -> str:
    # Currently uses config.prompt_variant (legacy approach)
    # This entire variant system needs to be removed
    variant = self.config.prompt_variant  
```

**Problems**:

1. Uses legacy "variant" nomenclature that should be removed
2. Only checks config, ignoring context overrides
3. Inconsistent naming (prompt vs system_prompt)

### Proposed Architecture

#### 1. Folder Structure

<!-- FEEDBACK: This is good. I like it.  -->
```text
config/prompts/
├── agents/                    # Stable, production prompts
│   ├── analyst/
│   │   ├── system.md          # Default production prompt
│   │   └── user/              # User messages
│   ├── reviewer/
│   │   └── system.md
│   └── judge/
│       └── system.md
├── experimental/              # NEW: Experimental prompts
│   ├── analyst/
│   │   ├── yc_style.md       # Example: YC-inspired variant
│   │   ├── academic.md       # Example: Academic style
│   │   └── concise.md        # Example: Ultra-concise
│   ├── reviewer/
│   │   └── strict.md         # Example: Stricter review
│   └── README.md             # Document experimental prompts
├── versions/                  # Historical (kept for reference)
│   └── analyst/
│       ├── analyst_v1.md     # Old, not relevant
│       ├── analyst_v2.md     # Old, not relevant
│       └── analyst_v3.md     # Old, not relevant
└── shared/                    # Shared includes
    └── file_edit_rules.md
```

#### 2. CLI Interface

```bash
# Use default prompt
python -m src.cli "AI fitness app"

# Use experimental prompt
python -m src.cli "AI fitness app" --analyst-prompt experimental/yc_style

# Override multiple agents
python -m src.cli "AI fitness app" \
  --analyst-prompt experimental/concise \
  --reviewer-prompt experimental/strict

# Use custom path (advanced users)
python -m src.cli "AI fitness app" --analyst-prompt-file /path/to/custom.md
```

#### 3. Implementation Changes

##### 3.1 Update BaseAgent to Use System Prompt Overrides

```python
# In agent_base.py
def get_system_prompt_path(self, context: TContext | None = None) -> str:
    """Get system prompt path with context override support."""
    
    agent_type = self.agent_name.lower()
    
    # Check context override first
    if context and hasattr(context, 'system_prompt_override'):
        override = context.system_prompt_override
        if override:
            if override.startswith("experimental/"):
                # Experimental prompt: experimental/analyst/yc_style
                return f"{override}.md"
            elif "/" in override:
                # Full path provided
                return override
            else:
                # Relative to agent folder
                return f"agents/{agent_type}/{override}.md"
    
    # Default: use standard system prompt
    return f"agents/{agent_type}/system.md"

def load_system_prompt(self, context: TContext | None = None) -> str:
    """Load system prompt with context override support."""
    return load_prompt_with_includes(
        self.get_system_prompt_path(context), 
        self.config.prompts_dir
    )
```

##### 3.2 Update CLI Argument Parsing

```python
# In cli.py
parser.add_argument(
    "--analyst-prompt",
    help="Override analyst system prompt (e.g., 'experimental/yc_style')"
)

parser.add_argument(
    "--reviewer-prompt", 
    help="Override reviewer system prompt"
)

parser.add_argument(
    "--judge-prompt",
    help="Override judge system prompt (Phase 3)"
)

# Advanced: direct file paths
parser.add_argument(
    "--analyst-prompt-file",
    help="Path to custom analyst system prompt file"
)
```

##### 3.3 Pass Context Through Agents

```python
# In analyst.py process() method
async def process(self, context: AnalystContext) -> AgentResult:
    # Load prompt with context
    system_prompt = self.load_system_prompt(context)  # Pass context!
    
    # Rest of processing...
```

#### 4. Update Context Classes

```python
# In config.py
@dataclass
class BaseContext:
    """Base context with common fields for all agent operations."""
    
    # Runtime state
    output_dir: Path | None = None
    revision_context: RevisionContext | None = None
    
    # System prompt override (replacing old prompt_version_override)
    system_prompt_override: str | None = None
    """Custom system prompt for this operation (None = use default)"""
    
    # Tool overrides remain the same
    tools_override: list[str] | None = None
    
    # Analytics tracking
    run_analytics: RunAnalytics | None = None
```

#### 5. Migration Path

1. **Phase 1**: Remove all variant/prompt_variant references from codebase
2. **Phase 2**: Update BaseAgent with get_system_prompt_path() method
3. **Phase 3**: Update config.py BaseContext with system_prompt_override
4. **Phase 4**: Add CLI arguments for system prompt overrides  
5. **Phase 5**: Create experimental/ folder structure
6. **Phase 6**: Document experimental prompt creation guide

### Benefits

1. **Clean Separation**: Stable vs experimental prompts
2. **Easy Testing**: CLI flags for quick A/B testing
3. **Simplified Code**: Removed legacy variant system
4. **Consistent Naming**: system_prompt throughout codebase
5. **No Config Mutation**: Uses proper context override pattern
6. **File-Based Only**: Single consistent approach for all prompts

### Example Usage Scenarios

```bash
# Production run (uses agents/analyst/system.md)
python -m src.cli "B2B marketplace"

# Test YC-style analysis  
python -m src.cli "B2B marketplace" --analyst-prompt experimental/yc_style

# Test stricter review
python -m src.cli "B2B marketplace" --with-review --reviewer-prompt experimental/strict

# Use custom prompt from file
python -m src.cli "B2B marketplace" --analyst-prompt-file ~/my-prompts/custom.md
```

### Implementation Checklist

- [ ] Remove all prompt_variant references from config.py
- [ ] Remove prompt_variant from AnalystConfig and ReviewerConfig
- [ ] Update BaseAgent.get_prompt_path() to get_system_prompt_path()
- [ ] Add system_prompt_override to BaseContext
- [ ] Update CLI with --analyst-prompt, --reviewer-prompt arguments
- [ ] Update pipeline to pass system_prompt_override to contexts
- [ ] Create experimental/ folder structure
- [ ] Convert v1/v2/v3 prompts to file-based format
- [ ] Update agents to pass context to load_system_prompt()
- [ ] Test with experimental prompts

### Notes

- All prompts must be file-based (use Read/Edit tools)
- No support for direct-output prompts
- Legacy variant system completely removed
- Consistent system_prompt naming throughout
