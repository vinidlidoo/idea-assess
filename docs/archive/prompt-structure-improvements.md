# Prompt Structure Improvements

## Current Issues

### 1. Inconsistent File Naming

- Analyst has `main.md`, `revision.md`, and `partials/` folder
- Reviewer has `main.md` and `instructions.md` (should be in partials/)
- No clear naming convention for system vs user prompts

### 2. Duplicated Content

- Tool usage rules repeated in both agents
- Resource constraints logic duplicated
- File operation instructions repeated

### 3. Missing Standardization

- No shared location for common instructions
- Inconsistent structure between agents

## Proposed New Structure

```text
config/prompts/
├── shared/                           # NEW: Common components
│   └── file_edit_rules.md           # Read-before-Edit rules only
│
├── agents/
│   ├── analyst/
│   │   ├── system.md                # Main system prompt (renamed from main.md)
│   │   └── user/                    # User prompts folder (renamed from partials/)
│   │       ├── initial.md           # Initial analysis prompt
│   │       ├── revision.md          # Revision prompt
│   │       ├── websearch_instruction.md
│   │       ├── websearch_disabled.md
│   │       └── constraints.md      # Agent-specific constraints (aligned naming)
│   │
│   └── reviewer/
│       ├── system.md                # Main system prompt
│       └── user/                    # User prompts folder
│           └── review.md            # Review instructions (moved from instructions.md)
```

## Common Segments to Extract

### 1. File Edit Rules (`shared/file_edit_rules.md`)

<!-- Simplified: Only the Read-then-Edit rule that both agents need -->
```markdown
## CRITICAL: File Editing Rules

**YOU MUST ALWAYS READ A FILE BEFORE EDITING IT**

1. When instructed to edit a file, FIRST use the Read tool on that exact file
2. THEN use the Edit tool to replace its content
3. This applies even to empty template files - they must be read first
4. The Edit tool will fail if you haven't read the file first
```

### 2. Agent-Specific Constraints (NOT shared)

<!-- Each agent keeps its own constraints since they differ -->
<!-- FEEDBACK: we should probably align the file names though -->
<!-- RESOLVED: Both will use 'constraints.md' for consistency -->
- Analyst: `agents/analyst/user/constraints.md` with max_turns, max_searches
- Reviewer: `agents/reviewer/user/constraints.md` with max_review_iterations
- These are NOT shared because they have different parameters
- **File naming aligned**: Both use `constraints.md` for consistency

## Current Implementation Analysis

### How Prompts Are Currently Loaded

#### 1. File Loading Mechanism (`src/utils/file_operations.py`)

```python
@lru_cache(maxsize=10)
def load_prompt(prompt_file: str, prompts_dir: Path) -> str:
    """Simple file loader with LRU caching."""
    prompt_path = prompts_dir / prompt_file
    with open(prompt_path, "r") as f:
        return f.read()
```

#### 2. Analyst Loading Pattern (`src/agents/analyst.py`)

```python
# Loads multiple prompt fragments
system_prompt = load_prompt(self.get_prompt_path(), self.config.prompts_dir)
websearch_template = load_prompt("agents/analyst/partials/websearch_instruction.md", ...)
resource_template = load_prompt("agents/analyst/partials/resource_constraints.md", ...)
user_template = load_prompt("agents/analyst/partials/user_instruction.md", ...)

# Formats and assembles them
user_prompt = user_template.format(
    idea=input_data,
    resource_note=resource_note,
    websearch_instruction=websearch_note,
    output_file=str(output_file)
)
```

#### 3. Reviewer Loading Pattern (`src/agents/reviewer.py`)

```python
# Similar pattern but simpler
system_prompt = load_prompt(self.get_prompt_path(), self.config.prompts_dir)
review_template = load_prompt("agents/reviewer/instructions.md", ...)
user_prompt = review_template.format(...)
```

#### 4. BaseAgent Support (`src/core/agent_base.py`)

```python
def get_prompt_path(self) -> str:
    """Dynamically resolves prompt paths based on agent name and variant."""
    agent_type = self.agent_name.lower()
    variant = getattr(self.config, "prompt_variant", "main")
    # Returns: 'agents/analyst/main.md'
```

### Impact on Current Code

#### Changes Required in `analyst.py`

1. **System prompt loading**: Change path from `main.md` to `system.md`
2. **Partial loading**: Update paths from `partials/` to `user/`
3. **Include processing**: System prompt will need include processing

#### Changes Required in `reviewer.py`

1. **System prompt loading**: Change path from `main.md` to `system.md`
2. **Instructions loading**: Move from `instructions.md` to `user/review.md`
3. **Include processing**: System prompt will need include processing

#### Changes Required in `agent_base.py`

1. **Update get_prompt_path()**: Change default from `main.md` to `system.md`
2. **Add prompt assembly method**: Optional method for building complete prompts

#### Changes Required in `file_operations.py`

1. **Enhanced load_prompt()**: Add include processing capability
2. **Cache invalidation**: Handle included files in cache

## Implementation Plan

### Phase 1: Create Simple Include Mechanism

<!-- Simplified: Just basic file inclusion, no parameters -->
**New function in `src/utils/file_operations.py`:**

<!-- FEEDBACK: Let's make sure we have good unit tests here to make sure these functions work -->
<!-- RESOLVED: Added comprehensive unit test requirements below -->
```python
import re

def load_prompt_with_includes(prompt_file: str, prompts_dir: Path) -> str:
    """
    Load a prompt with simple include support.
    
    Supports: {{include:shared/file_edit_rules.md}}
    """
    content = load_prompt(prompt_file, prompts_dir)
    
    # Simple regex for includes
    def replace_include(match):
        include_path = match.group(1)
        return load_prompt(include_path, prompts_dir)
    
    # Replace all {{include:path}} with file contents
    content = re.sub(r'\{\{include:([^}]+)\}\}', replace_include, content)
    return content
```

**Required Unit Tests:**

```python
# tests/test_prompt_loading.py

def test_load_prompt_with_single_include():
    """Test that a single include is replaced correctly."""
    # Given a prompt with {{include:shared/file_edit_rules.md}}
    # Should replace with contents of that file
    
def test_load_prompt_with_multiple_includes():
    """Test multiple includes in same file."""
    # Should replace all includes in order
    
def test_load_prompt_with_nested_includes():
    """Test that included files can have their own includes."""
    # Should recursively process includes
    
def test_load_prompt_with_missing_include():
    """Test graceful handling of missing include files."""
    # Should raise clear error with file path
    
def test_load_prompt_with_no_includes():
    """Test that prompts without includes work normally."""
    # Should return content unchanged
```

### Phase 2: Update BaseAgent with Variant Support

<!-- FEEDBACK: ah, I understand now. we should keep the capability to test multiple variants. they should be rename to system_v1, etc or something like that. bring that back in. -->
<!-- RESOLVED: Restored variant support with clearer naming -->
**Updated method in `src/core/agent_base.py`:**

```python
def get_prompt_path(self) -> str:
    """
    Get the system prompt path with variant support for A/B testing.
    
    Variants:
    - "system" (default): agents/{agent}/system.md
    - "system_v1", "system_v2", etc: agents/{agent}/system_v1.md
    - "experiment_foo": agents/{agent}/experiment_foo.md
    """
    agent_type = self.agent_name.lower()
    variant = getattr(self.config, "prompt_variant", "system")
    
    if variant == "system":
        # Default production prompt
        return str(Path("agents") / agent_type / "system.md")
    else:
        # A/B testing variants (system_v1.md, experiment_foo.md, etc)
        return str(Path("agents") / agent_type / f"{variant}.md")

def load_system_prompt(self) -> str:
    """Load the system prompt with includes (works for all variants)."""
    from ..utils.file_operations import load_prompt_with_includes
    return load_prompt_with_includes(
        self.get_prompt_path(), 
        self.config.prompts_dir
    )
```

This allows testing different prompt versions by setting `prompt_variant` in config:

- `prompt_variant: "system"` → uses `system.md` (default)
- `prompt_variant: "system_v1"` → uses `system_v1.md` (for A/B testing)
- `prompt_variant: "experiment_refactor"` → uses `experiment_refactor.md`

### Phase 3: Create Shared Components

**Step 1: Create directory structure:**

```bash
mkdir -p config/prompts/shared
mkdir -p config/prompts/agents/analyst/user
mkdir -p config/prompts/agents/reviewer/user
```

**Step 2: Create the single shared file:**

- `shared/file_edit_rules.md` - The Read-before-Edit rule that both agents need

**Step 3: Update agent prompts to use includes:**

<!-- FEEDBACK: I like this concept of having these includes coming from the shared folder. that's smart. -->
```markdown
<!-- In agents/analyst/system.md -->
{{include:shared/file_edit_rules.md}}

# Analyst Agent System Prompt (v3 - YC-Inspired Direct Analysis)

You are a Business Analyst Agent...
[Rest of original content without duplicated rules]
```

### Phase 4: Update Agent Implementations

**Analyst changes (minimal):**

```python
# In analyst.py - only 3 changes needed:
# 1. Use load_prompt_with_includes for system prompt
system_prompt = load_prompt_with_includes(
    self.get_prompt_path(),  # Will return "agents/analyst/system.md"
    self.config.prompts_dir
)

# 2. Update paths from partials/ to user/
websearch_template = load_prompt("agents/analyst/user/websearch_instruction.md", ...)
resource_template = load_prompt("agents/analyst/user/constraints.md", ...)  # Renamed file
user_template = load_prompt("agents/analyst/user/initial.md", ...)
```

**Reviewer changes (even simpler):**

```python
# In reviewer.py - only 2 changes:
# 1. Use load_prompt_with_includes for system prompt
system_prompt = load_prompt_with_includes(
    self.get_prompt_path(),  # Will return "agents/reviewer/system.md"
    self.config.prompts_dir
)

# 2. Update instruction path
review_template = load_prompt("agents/reviewer/user/review.md", ...)
```

### Phase 5: Migration Strategy

1. **Backward Compatibility Phase:**
   - Keep old files temporarily
   - Add deprecation warnings
   - Support both old and new paths

2. **Testing Phase:**
   - Test include mechanism with unit tests
   - Verify prompt assembly produces identical output
   - Run integration tests with both agents

3. **Cleanup Phase:**
   - Remove old prompt files
   - Update documentation
   - Remove compatibility code

## Benefits

1. **Maintainability**: Single source of truth for common rules
2. **Consistency**: All agents follow same patterns
3. **Clarity**: Clear separation of system vs user prompts
4. **Extensibility**: Easy to add new agents with standard structure
5. **Efficiency**: Reduced duplication and easier updates

## Migration Steps

1. Create shared directory and files
2. Update one agent at a time
3. Test each agent after migration
4. Update documentation
5. Remove old duplicated content
