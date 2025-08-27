# Implementation Plan: Analyst Tool Enhancements (Revised)

## Date: 2025-08-26

## Author: Claude (AI Assistant)

## Status: Revised Based on Feedback

---

## Executive Summary

This revised plan simplifies the implementation of three enhancements to the Analyst agent:

1. **WebFetch Integration** - Enable deeper investigation of WebSearch results
2. **TodoWrite Integration** - Help analysts organize research tasks
3. **Thinking Mode** - Enable deliberative reasoning for complex analysis

Key changes from v1: Consolidated tool instructions in one place, simplified CLI flags, removed hard limits, and properly researched thinking mode implementation.

---

## Core Changes

### 1. Rename and Repurpose constraints.md

**Current**: `config/prompts/agents/analyst/user/constraints.md`
**New**: `config/prompts/agents/analyst/user/tools.md`

This file will become the central location for all tool-related instructions.

### 2. Update CLI Flag

**Current**: `--no-websearch`
**New**: `--no-web-tools`

This flag will disable both WebSearch and WebFetch for consistency.

---

## Enhancement 1: WebFetch Tool Integration

### Implementation

#### 1.1 Update Tool Configuration

```python
# src/core/config.py - Line 61
allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch", "WebFetch"])
```

#### 1.2 Rename and Update Tools File

```bash
# Rename the file
mv config/prompts/agents/analyst/user/constraints.md config/prompts/agents/analyst/user/tools.md
```

<!-- FEEDBACK: this is indeed a task, but the wrong example. we need to update old references to constraints.md right? -->
Update references in analyst.py and prompt files:

```python
# src/agents/analyst.py - Line 101
revision_template = load_prompt_with_includes(
    "agents/analyst/user/revision.md", self.config.prompts_dir
)
```

#### 1.3 Add WebFetch Instructions to Tools File

```markdown
# config/prompts/agents/analyst/user/tools.md - Replace existing content

# Research Tools & Guidelines

<!-- FEEDBACK: I think we should have both websearch and webfetch instructions conditional to it being enabled or not. right now in this example it's not what's happening. -->
## Available Tools

- Maximum turns: {max_turns}
- {websearch_instruction}

## WebFetch for Deep Research

When you find promising search results, use WebFetch to extract detailed information:

1. Focus on sources with specific data, case studies, or technical details
2. Ask targeted questions when fetching:
   - "Extract all pricing information and business model details"
   - "Find specific metrics about market size and growth"
   - "Identify key competitors mentioned and their limitations"
3. Use your judgment on how many sources to fetch based on the complexity of the idea

## Efficiency Guidelines

- Complete the analysis in a single comprehensive response if possible
- Prioritize quality of sources over quantity
- Focus research on the most critical unknowns
```

<!-- FEEDBACK: yep, that's accurate -->
#### 1.4 Update User Prompts to Reference tools.md

```markdown
# config/prompts/agents/analyst/user/initial.md - Line 5
{{include:agents/analyst/user/tools.md}}

# config/prompts/agents/analyst/user/revision.md - Line 8 (update similarly)
{{include:agents/analyst/user/tools.md}}
```

#### 1.5 Update CLI for New Flag

```python
# src/cli.py - Line 45 (rename argument)
parser.add_argument(
    "--no-web-tools",
    "-n",
    action="store_true",
    help="Disable WebSearch and WebFetch tools (uses existing knowledge only)",
)

# Line 80 (update variable name)
no_web_tools: bool = args.no_web_tools

<!-- FEEDBACK: This isn't accurate as we should still enable TodoWrite even when web tools aren't enabled. -->
# Line 110 (update logic)
if no_web_tools:
    analyst_config.allowed_tools = []  # No web tools
```

---

## Enhancement 2: TodoWrite Tool Integration

### Implementation

#### 2.1 Update Tool Configuration

```python
# src/core/config.py - Line 61
allowed_tools: list[str] = field(
    default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"]
)
```

#### 2.2 Add TodoWrite Instructions to Tools File

```markdown
# config/prompts/agents/analyst/user/tools.md - Add new section

## Research Organization (Optional)

The TodoWrite tool can help organize complex analyses:

1. **When to Use**: For multi-faceted ideas with many research threads
2. **How to Use**: Create a simple task list to track your research progress
3. **Keep it Lightweight**: 5-8 tasks maximum, update as you go

Example workflow:
- Use TodoWrite to plan research areas (optional)
- Execute research with WebSearch/WebFetch
- Mark tasks complete as you gather data
- Synthesize findings into the analysis
```

#### 2.3 Update Research Workflow in file_edit_rules.md

```markdown
# config/prompts/shared/file_edit_rules.md - Add after line 20

<!-- FEEDBACK: need to account for the case where web tools aren't available in this prompt -->
## Research Workflow (When Multiple Tools Available)

1. **Plan** (optional): Use TodoWrite if the idea is complex
2. **Research**: Use WebSearch to find sources
3. **Deep Dive**: Use WebFetch for detailed extraction
4. **Synthesize**: Complete your research before editing
5. **Execute**: Use ONE Edit operation on the template
```

---

## Enhancement 3: Thinking Mode Integration

### Background

Claude's thinking mode is activated naturally when the model needs to work through complex problems. We don't use `<thinking>` tags in prompts, but rather encourage step-by-step reasoning through our instructions.

### Implementation

#### 3.1 Add Reasoning Encouragement to Tools File

```markdown
# config/prompts/agents/analyst/user/tools.md - Add new section

<!-- FEEDBACK: This prompt snippets feels a bit overlapping with TodoWrite instructions. Make the distinctin clearer. -->
## Strategic Reasoning

For complex analytical challenges:

1. **Think step-by-step** through trade-offs and strategic decisions
2. **Consider multiple angles** before settling on conclusions
3. **Work through uncertainties** systematically

Key decision points that benefit from careful reasoning:
- Evaluating competitive defensibility
- Assessing market timing ("why now?")
- Identifying the true 10x improvement
- Weighing different business model options
- Determining critical risks

Take time to reason through these complexities internally before writing your conclusions.
```

<!-- FEEDBACK: Let's not do that yet. -->
#### 3.2 Optional: Add Reasoning Hints to Template

```markdown
# config/templates/agents/analyst/analysis.md - Update Competition & Moat TODO

[TODO: 150 words - Analyze the competitive landscape honestly. 

Consider carefully: What's the real defensibility? Why won't incumbents copy this immediately?

Include:
... (rest of existing instructions)]
```

---

## Implementation Order

### Phase 1: Core Changes (15 mins)

1. Rename constraints.md to tools.md
2. Update references in analyst.py and prompts
3. Update CLI flag from --no-websearch to --no-web-tools

### Phase 2: WebFetch (15 mins)

1. Add WebFetch to allowed_tools
2. Add WebFetch instructions to tools.md
3. Test with test_locally.sh

### Phase 3: TodoWrite (20 mins)

1. Add TodoWrite to allowed_tools
2. Add TodoWrite instructions to tools.md
3. Update workflow guidance
4. Test with test_locally.sh

### Phase 4: Thinking Mode (10 mins)

1. Add reasoning encouragement to tools.md
2. Optionally update template hints
3. Test and observe behavior

---

## Testing Plan

Simple and straightforward:

```bash
# Test with web tools
./test_locally.sh "AI-powered fitness app for seniors"

# Test without web tools
python -m src.cli "Sustainable packaging solution" --no-web-tools -r

# Test with review cycle
python -m src.cli "B2B marketplace for construction" -r

# Check logs for:
# - WebFetch usage patterns
# - TodoWrite task creation (if used)
# - Quality of reasoning in output
```

---

## Key Differences from v1

1. **Consolidated Instructions**: All tool guidance in one file (tools.md)
2. **Clearer CLI Flag**: --no-web-tools instead of --no-websearch
3. **No Hard Limits**: Agent decides how many times to use each tool
4. **Proper Thinking Mode**: Encourages reasoning, not `<thinking>` tags
5. **Simpler Testing**: Just use test_locally.sh

---

## Files to Modify Summary

1. `src/core/config.py` - Add tools to allowed_tools
2. `config/prompts/agents/analyst/user/constraints.md` → Rename to `tools.md`
3. `config/prompts/agents/analyst/user/tools.md` - Add all tool instructions
4. `config/prompts/agents/analyst/user/initial.md` - Update include path
5. `config/prompts/agents/analyst/user/revision.md` - Update include path
6. `config/prompts/shared/file_edit_rules.md` - Add workflow guidance
7. `src/cli.py` - Rename flag to --no-web-tools
8. `config/templates/agents/analyst/analysis.md` - Optional reasoning hints

---

## Success Metrics

- WebFetch is used appropriately when sources need deeper investigation
- TodoWrite appears for complex ideas but not simple ones
- Analysis quality improves with better evidence and reasoning
- Turn count remains reasonable (under max_turns)
- test_locally.sh passes without errors

---

*End of Revised Implementation Plan*
