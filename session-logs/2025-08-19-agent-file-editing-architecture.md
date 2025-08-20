# Agent File Editing Architecture Analysis & Plan

## Current State Analysis

### How File Handling Works Today

1. **Pipeline Creates Files**:
   - Pipeline creates directories and manages all file I/O
   - Pipeline writes analysis content to `analysis.md` and `iterations/iteration_{n}.md`
   - Pipeline writes feedback to `reviewer_feedback.json`

2. **Agents Return Strings**:
   - AnalystAgent returns analysis content as a string in `AgentResult.content`
   - ReviewerAgent reads analysis file, creates feedback file, returns file path as string
   - No agents have `permission_mode="acceptEdits"` currently

3. **File Flow**:

   ```text
   Pipeline → Creates dirs → Analyst (returns string) → Pipeline writes file
   → Reviewer (reads file, writes feedback) → Pipeline reads feedback
   ```

### Problems with Current Architecture

1. **Inconsistent Patterns**:
   - Analyst returns content as string (pipeline writes)
   - Reviewer writes its own file (but can't without acceptEdits)
   - Mixed responsibility for file I/O

2. **Permission Mode Issue**:
   - Reviewer tries to write files but doesn't have `permission_mode="acceptEdits"`
   - This likely causes silent failures or SDK workarounds

3. **Future Agent Problems**:
   - Judge will need to write evaluation.json
   - Synthesizer will need to write reports
   - Current pattern won't scale

## Desired Architecture

### New File Handling Pattern

1. **Pipeline Creates Initial Structure**:
   - Creates directories and empty/template files
   - Provides file paths to agents via context

2. **Agents Edit Files Directly**:
   - All agents have `permission_mode="acceptEdits"`
   - Agents use Write/Edit tools to modify files
   - AgentResult returns file paths, not content

3. **Consistent Flow**:

   ```text
   Pipeline → Creates template files → Analyst (edits analysis.md) → Returns path
   → Reviewer (reads analysis, writes feedback.json) → Returns path
   → Judge (reads both, writes evaluation.json) → Returns path
   → Synthesizer (reads all, writes report.md) → Returns path
   ```

## Implementation Plan

### Phase 1: Enable File Editing Permissions

#### 1.1 Update AnalystAgent

```python
# In analyst.py process() method:
options = ClaudeCodeOptions(
    system_prompt=system_prompt,
    max_turns=self.config.max_turns,
    allowed_tools=allowed_tools,
    permission_mode="acceptEdits",  # ADD THIS
)
```

#### 1.2 Update ReviewerAgent

```python
# In reviewer.py process() method:
options = ClaudeCodeOptions(
    system_prompt=system_prompt,
    max_turns=self.config.max_turns,
    allowed_tools=allowed_tools,
    permission_mode="acceptEdits",  # ADD THIS
)
```

### Phase 2: Refactor Analyst to Write Files

#### 2.1 Update Analyst Prompts

- Modify user instruction to specify file path to write to
- Pass `output_file` path in context
- Instruct agent to use Write tool

<!-- FEEDBACK: output_file already exists in BaseContext -->
#### 2.2 Update AnalystContext

```python
class AnalystContext(AgentContext):
    output_file: Path  # Add this field
    # ... existing fields
```

#### 2.3 Update Analyst Process Method

- Pass output file path in prompt
- Return file path in AgentResult.content, not the analysis text
- Let agent handle all file writing

### Phase 3: Update Pipeline

#### 3.1 Create Template Files

```python
# In pipeline, before calling analyst:
analysis_file = iterations_dir / f"iteration_{iteration_count}.md"
analysis_file.touch()  # Create empty file for agent to edit

# Pass in context:
analyst_context.output_file = analysis_file
```

#### 3.2 Update Result Handling

```python
# After analyst completes:
analyst_result = await analyst.process(idea, analyst_context)
if analyst_result.success:
    # analyst_result.content is now a file path, not content
    analysis_file = Path(analyst_result.content)
    # Copy to main analysis.md
    shutil.copy(analysis_file, analysis_dir / "analysis.md")
```

<!-- FEEDBACK: let's pause and talk when we get here -->
### Phase 4: Ensure Consistency

#### 4.1 Update BaseAgent

- Add standard file handling helpers
- Ensure all agents follow same pattern

#### 4.2 Create Agent Template

- Document the pattern for future agents (Judge, Synthesizer)
- Ensure consistent approach

## Migration Strategy

### Step 1: Add Permissions Only (Minimal Change)

- Add `permission_mode="acceptEdits"` to both agents
- Test that existing flow still works
- This enables file writing but doesn't change behavior yet

### Step 2: Update Reviewer First (Already Writes Files)

- Reviewer already tries to write files
- Just needs permission mode to work properly
- Minimal code changes needed

### Step 3: Refactor Analyst (Bigger Change)

- Update prompts to include file path
- Change from returning content to writing file
- Update pipeline to handle new pattern

### Step 4: Standardize Pattern

- Extract common patterns to BaseAgent
- Document for future agents
- Update tests

## Risks & Mitigations

### Risk 1: Breaking Changes

- **Risk**: Changing return types breaks existing code
- **Mitigation**: Do incremental changes, test at each step

### Risk 2: File Permission Issues

- **Risk**: Agents might not have OS permissions
- **Mitigation**: Test thoroughly, handle errors gracefully

### Risk 3: Prompt Changes Break Behavior

- **Risk**: Telling agents to write files changes output quality
- **Mitigation**: Test with multiple ideas, compare results

## Testing Plan

1. **Unit Tests**:
   - Mock file system for agent tests
   - Verify file paths returned correctly
   - Test error handling

2. **Integration Tests**:
   - Run full pipeline with test ideas
   - Verify files created in correct locations
   - Check content quality unchanged

3. **Manual Testing**:
   - Test with various ideas
   - Verify iteration flow works
   - Check all files created properly

## Next Steps

1. Start with Phase 1 (add permission_mode) - LOW RISK
2. Test existing functionality still works
3. Proceed with Phase 2-4 based on test results
4. Document changes for future development

## Files to Modify

### Immediate Changes (Phase 1)

- `src/agents/analyst.py` - Add permission_mode
- `src/agents/reviewer.py` - Add permission_mode

### Future Changes (Phase 2-4)

- `src/core/config.py` - Update contexts
- `src/core/pipeline.py` - Change file handling
- `config/prompts/agents/analyst/partials/user_instruction.md` - Add file path
- `config/prompts/agents/analyst/revision.md` - Add file path
- `config/prompts/agents/reviewer/instructions.md` - Verify file writing instructions

## Decision Points

1. **Should we change AgentResult.content type?**
   - Option A: Keep as string, store file path
   - Option B: Make it Path type
   - Option C: Add separate field for file_path
   - **Recommendation**: Option A for backward compatibility

2. **How to handle multiple output files?**
   - Some agents might create multiple files
   - **Recommendation**: Return primary file in content, list all in metadata

3. **Error handling for file operations?**
   - What if agent fails to write file?
   - **Recommendation**: Pipeline creates backup, checks file exists

## Summary

This refactoring will:

1. Give agents proper permissions to edit files
2. Standardize file handling across all agents
3. Prepare architecture for Judge and Synthesizer agents
4. Remove inconsistencies in current implementation

The key insight is that agents should be responsible for their own file I/O, with the pipeline only orchestrating and providing paths. This aligns with the ClaudeSDK's design where agents with `acceptEdits` permission can modify files directly.
