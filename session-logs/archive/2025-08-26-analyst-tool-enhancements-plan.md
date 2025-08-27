# Implementation Plan: Analyst Tool Enhancements

## Date: 2025-08-26

## Author: Claude (AI Assistant)

## Status: Draft for Review

---

## Executive Summary

This document outlines the implementation plan for three key enhancements to the Analyst agent:

1. **WebFetch Integration** - Enable deeper investigation of WebSearch results
2. **TodoWrite Integration** - Help analysts organize and track research tasks
3. **Thinking Mode** - Enable deliberative reasoning for complex analysis

These enhancements will improve analysis quality, research depth, and reasoning transparency without breaking existing functionality.

---

## Current State Analysis

### Existing Tool Architecture

1. **Tool Configuration Flow**:

   ```
   CLI → AnalystConfig.allowed_tools → AnalystContext.tools → ClaudeCodeOptions.allowed_tools
   ```

2. **Current Tool Support**:
   - Only `WebSearch` is configured for Analyst
   - Tools are passed via `allowed_tools` list in ClaudeCodeOptions
   - No explicit prompt instructions for tool usage beyond WebSearch

3. **Template-Prompt Decoupling**:
   - Templates contain structure (TODOs)
   - Prompts contain principles and approach
   - File operation rules in `shared/file_edit_rules.md`

### Key Files to Modify

1. **Configuration**: `src/core/config.py`
2. **Prompts**: `config/prompts/agents/analyst/system.md`
3. **User Messages**: `config/prompts/agents/analyst/user/constraints.md`
4. **Analyst Agent**: `src/agents/analyst.py`
5. **CLI**: `src/cli.py` (optional for flags)

---

<!-- FEEDBACK: One more thing to consider: we should rethink our no-websearch flag on the cli. for simplicity I think that flag should disable both WebSearch and WebFetch. we should probably rename it to preserve clarity of intent. -->
## Enhancement 1: WebFetch Tool Integration

### Objective

Allow the Analyst to dive deeper into search results by fetching and analyzing full web pages.

### Implementation Steps

#### 1.1 Update Tool Configuration

```python
# src/core/config.py - Line 61
allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch", "WebFetch"])
```

#### 1.2 Add WebFetch Instructions to System Prompt

<!-- FEEDBACK: I think WebFetch related content would be a better fit inside of analyst/user/constraints, no? -->
```markdown
# config/prompts/agents/analyst/system.md - Add new section after line 60

## Deep Dive Research with WebFetch

When you find promising search results:

1. Use WebFetch to extract detailed information from key sources
2. Focus on pages with specific data, case studies, or technical details
3. Ask targeted questions when fetching:
   - "Extract all pricing information and business model details"
   - "Find specific metrics about market size and growth"
   - "Identify key competitors mentioned and their limitations"
4. Limit WebFetch to most valuable sources to conserve turns
```

#### 1.3 Update Constraints to Include WebFetch Guidance

```markdown
<!-- FEEDBACK: don't want to add hard constraints on WebFetch for now. Let the agent decide how many times they want to use WebFetch for now. -->
# config/prompts/agents/analyst/user/constraints.md - Update line 6
- {websearch_instruction}
- Use WebFetch sparingly (2-3 times max) to deep-dive critical sources
```

#### 1.4 Update Websearch Instruction Building

<!-- FEEDBACK: I don't think this is needed. This feels duplicative. -->
```python
# src/agents/analyst.py - Lines 89-92
if use_websearch:
    websearch_instruction = (
        f"Use WebSearch efficiently (maximum {self.config.max_websearches} searches) "
        f"to gather the most critical data. "
        f"Use WebFetch to deep-dive into 2-3 key sources for detailed information."
    )
else:
    websearch_instruction = "WebSearch and WebFetch are disabled. Use your existing knowledge."
```

### Testing Approach

1. Run with a complex idea requiring detailed research
<!-- FEEDBACK: not needed -->
2. Verify WebFetch is called 1-3 times
3. Check that fetched content improves analysis depth
4. Monitor turn usage to ensure efficiency

---

## Enhancement 2: TodoWrite Tool Integration

### Objective

Help the Analyst organize research tasks and track progress systematically.

### Implementation Steps

#### 2.1 Update Tool Configuration

```python
# src/core/config.py - Line 61
allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"])
```

#### 2.2 Add TodoWrite Instructions to System Prompt

<!-- FEEDBACK: I think it'd be better to leverage constraints.md for all tool-related prompts. Maybe we'd need to rename the file for a clearer intent. Think about it. -->
```markdown
# config/prompts/agents/analyst/system.md - Add new section after WebFetch section

## Research Organization with TodoWrite

Use the TodoWrite tool to organize your analysis approach:

1. **Initial Planning** (optional but recommended for complex ideas):
   - Break down the analysis into research tasks
   - Track what sections need which type of data
   - Mark tasks as you complete them

2. **When to Use TodoWrite**:
   - Complex multi-faceted business ideas
   - When you need to track multiple research threads
   - To ensure all template sections get proper attention

3. **Keep it Simple**:
   - 5-8 tasks maximum
   - Focus on research and data gathering
   - Update status as you progress
```

#### 2.3 Add Research Workflow Guidance

```markdown
# config/prompts/shared/file_edit_rules.md - Add after line 20

## Research Workflow (When Multiple Tools Available)

1. **Plan** (optional): Use TodoWrite to organize research tasks
2. **Research**: Use WebSearch to do research across multiple sources
3. **Deep Dive**: Use WebFetch for detailed extraction
4. **Synthesize**: Complete your research before editing
5. **Execute**: Use ONE Edit operation on the template
```

### Testing Approach

<!-- FEEDBACK: I just want to run tests in ./test_locally.sh and see what happens -->
1. Test with simple idea (should skip TodoWrite)
2. Test with complex idea (should use TodoWrite)
3. Verify task tracking improves organization
4. Check that it doesn't add unnecessary overhead

---

## Enhancement 3: Thinking Mode Integration

### Objective

Enable the Analyst to use Claude's thinking mode for complex reasoning and trade-off analysis.

### Implementation Steps

#### 3.1 Add Thinking Instructions to System Prompt

<!-- FEEDBACK: Consider where to put that in light of previous comments  -->
```markdown
# config/prompts/agents/analyst/system.md - Add new section after TodoWrite section

## Strategic Thinking

<!-- FEEDBACK: Research the proper way to prompt Claude to think, and update your recommendations once you understand how to do it. -->
<thinking>
Use thinking blocks when you need to:

1. **Analyze Complex Trade-offs**:
   - Weighing different market entry strategies
   - Evaluating competitive positioning options
   - Considering various business model approaches

2. **Synthesize Conflicting Information**:
   - Reconciling different market size estimates
   - Evaluating contradictory competitor data
   - Assessing feasibility concerns

3. **Make Strategic Judgments**:
   - Determining the strongest value proposition angle
   - Identifying the most critical risk factors
   - Choosing which metrics matter most

Remember: Thinking blocks help you reason through complexity but don't count against your word limits.
</thinking>

Apply thinking deliberately for the hardest analytical challenges, not routine research.
```

<!-- FEEDBACK: Same than previous comment -->
#### 3.2 Add Thinking Triggers to Template Instructions

```markdown
# Could be added to config/templates/agents/analyst/analysis.md in specific TODOs
# For example, in Competition & Moat section:

[TODO: 150 words - Analyze the competitive landscape honestly. 

<thinking>Consider: What's the real defensibility here? Why won't incumbents crush this?</thinking>

Include:
...rest of existing TODO...]
```

### Testing Approach

1. Run analysis and check for ThinkingBlock messages in logs
2. Verify thinking improves reasoning quality
3. Ensure thinking is used strategically, not excessively
4. Check RunAnalytics captures thinking blocks correctly

---

## Implementation Order & Timeline

### Phase 1: WebFetch Integration (30 mins)

- Lowest risk, highest immediate value
- Simple configuration change
- Clear prompt additions
- Easy to test and validate

### Phase 2: Thinking Mode (20 mins)

- Medium complexity
- Prompt-only changes
- Natural fit with existing workflow
- Observable in message logs

### Phase 3: TodoWrite Integration (45 mins)

- Most complex behaviorally
- Requires careful prompt crafting
- Need to avoid overhead for simple ideas
- Most testing required

---

## Risk Mitigation

### 1. Turn Efficiency

**Risk**: New tools could increase turn usage
**Mitigation**:

- Set explicit limits (2-3 WebFetch, 5-8 todos)
- Make TodoWrite optional
- Test with turn monitoring

### 2. Backward Compatibility

**Risk**: Changes break existing analyses
**Mitigation**:

- All changes are additive
- Existing --no-websearch flag still works
- Test with old and new ideas

### 3. Complexity Creep

**Risk**: Prompts become too complex
**Mitigation**:

- Each tool section is self-contained
- Clear when to use each tool
- Start with minimal instructions, iterate

---

## Success Criteria

1. **WebFetch**: Analyst successfully extracts detailed info from 1-3 sources
2. **TodoWrite**: Complex analyses show better organization
3. **Thinking**: Logs show ThinkingBlock messages for strategic decisions
4. **Overall**: Analysis quality improves without significant turn increase

---

## Testing Plan

### Test Cases

1. **Simple Idea Test** ("AI fitness app")
   - Should use WebSearch + WebFetch
   - Should skip TodoWrite
   - Minimal thinking blocks

2. **Complex Idea Test** ("Blockchain supply chain for pharmaceuticals")
   - Should use all tools
   - TodoWrite for organization
   - Multiple thinking blocks for trade-offs

3. **No-WebSearch Test** (with --no-websearch flag)
   - Should work with knowledge only
   - Can still use TodoWrite and Thinking
   - Verify graceful degradation

### Validation Metrics

- Turn count: Should stay under max_turns (20)
- Tool usage: Appropriate for complexity
- Analysis quality: Depth and evidence improved
- Message logs: Capture new tool usage

---

## Alternative Approaches Considered

### 1. Separate Tool Profiles

Instead of adding all tools, create profiles:

- "research" profile: WebSearch + WebFetch
- "analytical" profile: TodoWrite + Thinking
- **Rejected**: Too complex, rigid

### 2. Dynamic Tool Addition

Add tools based on idea complexity detection:

- **Rejected**: Adds complexity, unpredictable

### 3. Prompt-Only Changes

Skip config changes, just update prompts:

- **Rejected**: Tools wouldn't actually be available

---

## Next Steps

1. **Review this plan** - Get user feedback
2. **Implement Phase 1** - WebFetch first
3. **Test and validate** - Use test cases above
4. **Iterate on prompts** - Refine based on results
5. **Document changes** - Update architecture docs

---

## Appendix: Code Snippets

### Complete Updated AnalystConfig

```python
@dataclass
class AnalystConfig(BaseAgentConfig):
    """Configuration specific to the Analyst agent."""
    
    # Analyst-specific settings
    max_websearches: int = 4
    min_words: int = 800
    
    # Enhanced tool suite for deeper analysis
    allowed_tools: list[str] = field(
        default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"]
    )
```

### CLI Flag for Tool Control (Optional)

```python
# Add to src/cli.py after line 49
parser.add_argument(
    "--basic-tools",
    action="store_true", 
    help="Use only WebSearch (disable WebFetch and TodoWrite)"
)

# After line 111
if basic_tools:
    analyst_config.allowed_tools = ["WebSearch"]
```

---

*End of Implementation Plan*
