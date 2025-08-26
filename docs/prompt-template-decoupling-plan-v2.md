# Prompt-Template Decoupling: Simplified Implementation Plan

## Executive Summary

This document outlines the simplified implementation plan for decoupling system prompts from file editing templates. The pipeline will create files with starter templates (plain markdown/JSON) instead of empty files, allowing agents to focus on content generation rather than document structure.

## Key Changes from Original Design

1. **No Jinja2 dependency** - Use plain markdown/JSON files
2. **Simple file copying** - No template engine needed
3. **Direct metadata append** - Pipeline adds metadata after agent completion
4. **Minimal code changes** - Simpler implementation with same benefits

## Current State Analysis

### Problem Statement

Currently, the pipeline creates empty files that agents must structure and fill:

```python
# pipeline.py lines 176-178 (Analyst)
analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
if not analysis_file.exists():
    _ = analysis_file.write_text("")  # Empty file

# pipeline.py lines 216-218 (Reviewer)
feedback_file = self.iterations_dir / f"reviewer_feedback_iteration_{self.iteration_count}.json"
if not feedback_file.exists():
    _ = feedback_file.write_text("{}")  # Empty JSON
```

### Agent Prompts Reference Empty Files

- `analyst/user/initial.md` line 10: "The file {output_file} has been created for you"
- `reviewer/user/review.md` line 17: "This file already exists with empty JSON: {{}}"

## Proposed Solution

### Architecture

```text
config/
├── prompts/           # Agent prompts (unchanged)
│   └── agents/
└── templates/         # NEW: File starter templates (mirrors prompts structure)
    ├── agents/
    │   ├── analyst/
    │   │   └── analysis.md         # Analysis document template
    │   └── reviewer/
    │       └── feedback.json        # Feedback JSON template
    └── shared/
        └── metadata.md              # Reusable metadata template
```

### Template Examples

#### Analyst Template (`config/templates/agents/analyst/analysis.md`)

```markdown
# [Company Name]: [One-line Description]

## What We Do

[TODO: 50 words - Company name and dead-simple explanation]

## The Problem

[TODO: 150 words - Specific acute pain with examples]

## The Solution

[TODO: 150 words - 10x improvement with metrics]

## Market Size

[TODO: 100 words - TAM with bottom-up calculation]

## Business Model

[TODO: 100 words - Unit economics and path to $100M]

## Why Now?

[TODO: 100 words - What changed to make this possible]

## Competition & Moat

[TODO: 150 words - Competitors and unfair advantage]

## Key Risks & Mitigation

[TODO: 100 words - Top 3 existential risks]

## Milestones

[TODO: 50 words - 30/90/180/365 day targets]

## References

[TODO: Add numbered citations]
```

#### Reviewer Template (`config/templates/agents/reviewer/feedback.json`)

```json
{
  "overall_assessment": "[TODO: Brief 2-3 sentence assessment]",
  "strengths": [],
  "critical_issues": [],
  "improvements": [],
  "minor_suggestions": [],
  "iteration_recommendation": "reject",
  "iteration_reason": "[TODO: Explanation for recommendation]"
}
```

### Implementation Details

#### 1. Template Operations Module (`src/utils/template_operations.py`)

```python
from pathlib import Path
from typing import Optional
from functools import lru_cache

@lru_cache(maxsize=32)
def load_template(template_path: Path) -> str:
    """Load and cache a template file."""
    return template_path.read_text()

def create_file_from_template(
    template_path: Path,
    output_path: Path
) -> None:
    """Create a file from a template."""
    template_content = load_template(template_path)
    output_path.write_text(template_content)

def append_metadata_to_analysis(
    analysis_file: Path,
    idea: str,
    slug: str,
    iteration: int,
    websearch_count: int = 0
) -> None:
    """Append metadata comment to completed analysis."""
    from datetime import datetime
    
    metadata = f"""
---
<!-- Analysis Metadata - Auto-generated, Do Not Edit -->
<!-- 
Idea Input: "{idea}"
Idea Slug: {slug}
Iteration: {iteration}
Timestamp: {datetime.now().isoformat()}
Websearches Used: {websearch_count}
-->
"""
    
    with open(analysis_file, 'a') as f:
        f.write(metadata)
```

#### 2. Pipeline Changes (`src/core/pipeline.py`)

```python
# Add to imports
from src.utils.template_operations import create_file_from_template, append_metadata_to_analysis

# Update _run_analyst method (around line 176)
async def _run_analyst(self, analyst: AnalystAgent) -> bool:
    """Run analyst for current iteration. Returns True on success."""
    # Create analysis file from template
    analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
    if not analysis_file.exists():
        template_path = self.system_config.template_dir / "agents" / "analyst" / "analysis.md"
        create_file_from_template(template_path, analysis_file)
        logger.debug(f"Created analysis file from template: {analysis_file}")
    
    # ... rest of method unchanged ...
    
    # After Success, before returning True:
    if self.analytics:
        append_metadata_to_analysis(
            analysis_file,
            self.idea,
            self.slug,
            self.iteration_count,
            self.analytics.websearch_count if self.analytics else 0
        )

# Update _run_reviewer method (around line 216)
async def _run_reviewer(self, reviewer: ReviewerAgent) -> bool:
    """Run reviewer and process feedback. Returns True if should continue."""
    # Create feedback file from template
    feedback_file = self.iterations_dir / f"reviewer_feedback_iteration_{self.iteration_count}.json"
    if not feedback_file.exists():
        template_path = self.system_config.template_dir / "agents" / "reviewer" / "feedback.json"
        create_file_from_template(template_path, feedback_file)
        logger.debug(f"Created feedback file from template: {feedback_file}")
```

#### 3. Config Update (`src/core/config.py`)

```python
@dataclass
class SystemConfig:
    """System-wide configuration."""
    # ... existing fields ...
    template_dir: Path = Path("config/templates")  # NEW field
```

#### 4. Prompt Updates

All prompt files that reference file creation or empty files need updating:

**Files to Update:**

1. **`agents/analyst/system.md`** (line 9)
   - Keep `{{include:shared/file_edit_rules.md}}` as-is
   - May need to add note about template structure in instructions

2. **`agents/analyst/user/initial.md`** (lines 10-14)
   - Update to reference template structure instead of empty file

3. **`agents/analyst/user/revision.md`** (line 33)
   - Update to mention template is pre-filled for revision

4. **`agents/reviewer/system.md`**
   - Keep `{{include:shared/file_edit_rules.md}}` as-is
   - Update task description if needed

5. **`agents/reviewer/user/review.md`** (lines 17, 19)
   - Update to reference template structure instead of empty JSON

6. **`shared/file_edit_rules.md`** (line 8)
   - Update to mention "template files" instead of "empty template files"

**Example Updates:**

**analyst/user/initial.md:**

```markdown
IMPORTANT: The file {output_file} has been created with a template structure.

1. First, use the Read tool to read the file and see the template
2. Then, use the Edit tool to replace each [TODO] section with your analysis
Do NOT use the Write tool - the file already exists with template content.
```

**analyst/user/revision.md:**

```markdown
Write your complete revised analysis to the file: {output_file}

IMPORTANT: The revision file has been created with a template structure.
1. First, use the Read tool to read the template
2. Then, use the Edit tool to replace the [TODO] sections with your revised analysis
```

**reviewer/user/review.md:**

```markdown
3. THIRD: Use the Read tool to read the feedback file at: {feedback_file}
   (This file already exists with a JSON template structure)

4. FOURTH: Use the Edit tool on {feedback_file} to replace the [TODO] sections with your feedback
```

**shared/file_edit_rules.md:**

```markdown
3. NEVER attempt to Edit without Reading first - it will fail
4. This applies to ALL files, including pre-filled template files
```

## Implementation Plan

### Phase 1: Infrastructure (30 minutes)

1. Create directory structure (mirroring prompts/):
   - `config/templates/agents/analyst/`
   - `config/templates/agents/reviewer/`
   - `config/templates/shared/`

2. Create template files:
   - `config/templates/agents/analyst/analysis.md`
   - `config/templates/agents/reviewer/feedback.json`

3. Add template operations:
   - Create `src/utils/template_operations.py`
   - Simple functions, no Jinja2

### Phase 2: Pipeline Integration (45 minutes)

1. Update `SystemConfig` to include `template_dir`
2. Modify `_run_analyst` to use template
3. Modify `_run_reviewer` to use template
4. Add metadata append functionality

### Phase 3: Prompt Updates (30 minutes)

1. Update `agents/analyst/user/initial.md`
2. Update `agents/analyst/user/revision.md`
3. Update `agents/reviewer/user/review.md`
4. Update `shared/file_edit_rules.md`
5. Remove all references to empty files

### Phase 4: Testing (45 minutes)

1. Test with `test_locally.sh`
2. Verify agents understand templates
3. Check metadata is appended correctly
4. Ensure no regression in quality

## Benefits

1. **Cleaner Architecture**: Structure separate from content
2. **Better Agent Experience**: Agents see clear structure immediately
3. **Easier Maintenance**: Templates can be updated independently
4. **No New Dependencies**: Plain files, no template engine
5. **Simpler Implementation**: ~100 lines of code vs ~300 with Jinja2

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Agents confused by pre-filled templates | Clear [TODO] markers and updated prompts |
| Template changes break agents | Test thoroughly before deployment |
| Metadata interferes with analysis | Append as HTML comment at end |

## Success Criteria

1. Agents successfully fill in template sections
2. No degradation in output quality
3. Metadata correctly appended
4. All tests pass

## Timeline

- **Total Estimate**: 2.5 hours (vs 8 hours for Jinja2 approach)
- Much simpler implementation
- Lower maintenance burden
- Easier to understand and debug

## Next Steps

1. Create template directory and files
2. Implement simple template operations
3. Update pipeline to use templates
4. Update prompts to reference templates
5. Test end-to-end with test_locally.sh

---

*Updated: 2025-08-26*  
*Simplified from original Jinja2-based design*
