# Implementation Plan: Analyst Tool Enhancements (Simplified)

## Date: 2025-08-26

## Author: Claude (AI Assistant)

## Status: Final Simplified Version

---

## Executive Summary

This simplified plan implements three analyst enhancements with minimal complexity:

1. **WebFetch Integration** - Deeper investigation of search results
2. **TodoWrite Integration** - Task organization (always available)
3. **Thinking Mode** - Improved analytical reasoning

Key principle: Keep all prompt text in the prompts folder, pass simple variables, avoid conditional complexity.

---

## Simplified Approach

### Core Design Principles

1. **All prompt text stays in prompts folder** - No long strings in Python
2. **TodoWrite is always available** - Part of base toolkit
3. **Simple variable substitution** - Just pass what's needed
4. **Single tools.md file** - Contains all instructions, handles all cases

### What We're Changing

1. **Rename**: `constraints.md` → `tools.md`
2. **Update CLI flag**: `--no-websearch` → `--no-web-tools`
3. **Add tools**: WebFetch and TodoWrite to default config
4. **Pass simple variables**: Just max_turns, max_websearches, and web_tools_enabled

---

## Implementation Steps

### Step 1: Update Default Tools Configuration

```python
# src/core/config.py - Line 61
# CHANGE FROM:
allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch"])

# CHANGE TO:
allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"])
```

### Step 2: Rename and Update References

```bash
# Rename the file
mv config/prompts/agents/analyst/user/constraints.md config/prompts/agents/analyst/user/tools.md
```

```markdown
# config/prompts/agents/analyst/user/initial.md - Line 5
# CHANGE FROM:
{{include:agents/analyst/user/constraints.md}}
# CHANGE TO:
{{include:agents/analyst/user/tools.md}}

# config/prompts/agents/analyst/user/revision.md - Line 5  
# CHANGE FROM:
{{include:agents/analyst/user/constraints.md}}
# CHANGE TO:
{{include:agents/analyst/user/tools.md}}
```

### Step 3: Update CLI Flag

```python
# src/cli.py - Line 44-49
# CHANGE FROM:
parser.add_argument(
    "--no-websearch",
    "-n",
    action="store_true",
    help="Disable WebSearch tool for faster analysis (uses existing knowledge only)",
)

# CHANGE TO:
parser.add_argument(
    "--no-web-tools",
    "-n", 
    action="store_true",
    help="Disable WebSearch and WebFetch tools (uses existing knowledge only)",
)

# Line 80 - Update variable name
# CHANGE FROM:
no_websearch: bool = args.no_websearch
# CHANGE TO:
no_web_tools: bool = args.no_web_tools

# Line 110 - Update logic to preserve TodoWrite
# CHANGE FROM:
if no_websearch:
    analyst_config.allowed_tools = []  # No external tools
    
# CHANGE TO:
if no_web_tools:
    # Remove only web tools, keep TodoWrite
    analyst_config.allowed_tools = ["TodoWrite"]
```

### Step 4: Simplify analyst.py Variable Passing

```python
# src/agents/analyst.py - Lines 88-92 
# Simplify to just pass a flag for web tools status
web_tools_enabled = "WebSearch" in allowed_tools
# Then update the user prompt format calls (lines 109 and 123):

```python
# Lines 109 (revision) and 123 (initial) - Simplified parameters
user_prompt = template.format(
    idea=input_data,
    max_turns=self.config.max_turns,
    max_websearches=self.config.max_websearches,
    web_tools_enabled="yes" if web_tools_enabled else "no",
    output_file=str(output_file),
    # ... other parameters for revision case
)
```

### Step 5: Create the New tools.md File

Create a single, self-contained tools.md that handles all cases:

```markdown
# config/prompts/agents/analyst/user/tools.md - Complete replacement

# Research Tools & Guidelines

## Available Resources

- Maximum turns: {max_turns}
- Web tools enabled: {web_tools_enabled}
- Maximum web searches (if enabled): {max_websearches}

## Research Tools

{% if web_tools_enabled == "yes" %}
### WebSearch & WebFetch

You have access to web research tools:

- **WebSearch**: Find relevant sources (max {max_websearches} searches)
- **WebFetch**: Extract detailed information from promising URLs
  - Focus on sources with specific data, case studies, or technical details
  - Ask targeted questions: "Extract pricing information", "Find market size metrics", etc.
  - Use your judgment on how many sources to deep-dive

{% else %}
Web tools are disabled. Use your existing knowledge for this analysis.
{% endif %}

### TodoWrite (Task Organization)

The TodoWrite tool helps organize complex analyses:

- **Use for**: Multi-faceted ideas with many research threads
- **Skip for**: Simple, straightforward business ideas  
- **Keep it light**: 5-8 tasks maximum, focused on research areas
- **Update as you go**: Mark tasks complete as you gather data

This is optional - use when it helps your organization.

## Analytical Reasoning

For strategic decisions and trade-offs:

- **Work through complexities** step-by-step before reaching conclusions
- **Consider multiple perspectives** on competitive positioning
- **Evaluate evidence carefully** when assessing market timing
- **Think critically** about true defensibility and moats

Take time to reason through complexities internally before writing conclusions.
(This is analytical thinking, distinct from task tracking with TodoWrite)

## Efficiency Guidelines

- Complete the analysis in a single comprehensive response if possible
- Prioritize quality of sources over quantity
- Focus research on the most critical unknowns
```

**Note**: This uses simple template conditionals that are supported by our load_prompt_with_includes function.

### Step 6: Update file_edit_rules.md

```markdown
# config/prompts/shared/file_edit_rules.md - Add after line 20

## Research Workflow

1. **Read the template first** - Use Read tool to understand structure
2. **Plan** (optional): Use TodoWrite for complex ideas needing organization  
3. **Research** (if web tools enabled): Use WebSearch to find sources
4. **Deep Dive** (if web tools enabled): Use WebFetch for detailed extraction
5. **Synthesize**: Complete all research before editing
6. **Execute**: Use ONE Edit operation on the template

Remember: ALWAYS READ before EDIT.
```

---

<!-- FEEDBACK: I like this even better. -->
## Wait, Even Simpler

Actually, we might not even need template conditionals. Let me reconsider with an even simpler approach:

```markdown
# config/prompts/agents/analyst/user/tools.md - Ultra-simple version

# Research Tools & Guidelines

## Available Resources

- Maximum turns: {max_turns}
- Web search limit: {max_websearches} searches
- Web tools status: {web_tools_status}

## Research Tools

### Web Research
{web_tools_instruction}

### Task Organization (TodoWrite)

TodoWrite helps organize complex analyses:
- Use for multi-faceted ideas with many research threads
- Skip for simple, straightforward business ideas  
- Keep it light: 5-8 tasks maximum
- This is optional - use when helpful

## Analytical Reasoning

For strategic decisions:
- Work through complexities step-by-step
- Consider multiple perspectives  
- Evaluate evidence carefully
- Think critically about defensibility

Take time to reason internally before writing conclusions.

## Efficiency Guidelines

- Complete the analysis in one comprehensive response if possible
- Prioritize quality over quantity
- Focus on critical unknowns
```

And in analyst.py, just set simple strings:

```python
# src/agents/analyst.py - Lines 88-95
if "WebSearch" in allowed_tools:
    web_tools_status = "enabled"
    web_tools_instruction = (
        f"Use WebSearch (max {self.config.max_websearches}) to find sources. "
        f"Use WebFetch to deep-dive promising URLs for detailed data."
    )
else:
    web_tools_status = "disabled" 
    web_tools_instruction = "Web tools disabled. Use your existing knowledge."
```

---

## Testing Plan

```bash
# Simple test
python -m src.cli "AI fitness app"

# Complex test with review  
python -m src.cli "Blockchain supply chain" -r

# No web tools test
python -m src.cli "Packaging solution" --no-web-tools
```

---

## Summary

This simplified plan:

1. **Adds three tools** to default config (WebFetch, TodoWrite always available)
2. **Renames one file** (constraints.md → tools.md)  
3. **Updates one CLI flag** (--no-websearch → --no-web-tools)
4. **Passes simple variables** (no complex conditionals)
5. **Keeps all text in prompts folder** (no long strings in Python)

Total changes: ~6 files, ~50 lines of code

---

*End of Simplified Implementation Plan*
