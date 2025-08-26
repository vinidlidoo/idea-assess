# Prompt-Template Decoupling: Design & Implementation Plan

## Executive Summary

This document outlines the design and implementation plan for decoupling system prompts from file editing templates in the Business Idea Evaluator system. Currently, the pipeline creates empty files and agents are instructed via prompts to edit them. The new approach will have the pipeline create files with starter templates, removing file editing instructions from agent prompts.

## Current State Analysis

### Problem Statement

The current implementation has several issues:

1. **Tight Coupling**: File editing instructions are embedded in agent system prompts
2. **Empty Files**: Pipeline creates empty files (`""` or `{}`) that agents must fill
3. **Redundant Instructions**: Every prompt repeats the same Read→Edit workflow
4. **Maintenance Burden**: Changes to file structure require prompt updates
5. **Agent Complexity**: Agents need to understand file operations instead of focusing on content

### Current Implementation

#### Pipeline File Creation (pipeline.py)

```python
# Lines 176-178: Analyst file creation
analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
if not analysis_file.exists():
    _ = analysis_file.write_text("")  # Empty file

# Lines 216-218: Reviewer file creation  
feedback_file = self.iterations_dir / f"reviewer_feedback_iteration_{self.iteration_count}.json"
if not feedback_file.exists():
    _ = feedback_file.write_text("{}")  # Empty JSON
```

#### Prompt Instructions

- `shared/file_edit_rules.md`: Contains generic Read→Edit instructions
- `analyst/user/initial.md`: Tells agent about pre-created file
- `reviewer/user/review.md`: Detailed Read→Edit workflow

## Proposed Solution

### Design Principles

1. **Separation of Concerns**: Templates define structure, prompts define content generation
2. **Template-Driven**: Pipeline creates files with starter templates
3. **Clean Prompts**: Agent prompts focus on business logic, not file operations
4. **Flexible Templates**: Support both static and dynamic template variables
5. **Direct Migration**: No backward compatibility needed (project has no external users)

### Important Clarification: Why Agents Still Need File Editing

Even with templates, agents must still:

1. **Read** the pre-filled template file to see the structure
2. **Edit** the file to replace TODO sections with actual content

The key difference is:

- **Before**: Agents edit empty files and must create entire structure
- **After**: Agents edit pre-structured files and only fill in content

This means `file_edit_rules.md` remains necessary, but the cognitive load on agents is reduced since they're working with a clear structure rather than a blank canvas.

### Architecture

```text
config/
├── prompts/           # Agent system & user prompts (content generation)
│   └── agents/
│       ├── analyst/
│       └── reviewer/
└── templates/         # File starter templates (structure)
    ├── analyst/
    │   ├── analysis.md.j2         # Jinja2 template for analysis
    │   └── analysis_revision.md.j2 # Template for revisions
    └── reviewer/
        └── feedback.json.j2        # Template for feedback JSON
```

### Template Format Decision: Why Jinja2?

#### Options Considered

1. **Plain Markdown with Placeholders** (`analysis.md`)
   - Pros: Simple, no dependencies, easy to read
   - Cons: No logic support, manual string replacement needed
   - Example: `[IDEA_SLUG]` or `{{IDEA_SLUG}}`

2. **Python f-string Templates** (`analysis.py.tmpl`)
   - Pros: Native Python, no extra dependencies
   - Cons: Security risks with eval(), limited features
   - Example: `f"# {company_name}: {idea}"`

3. **Jinja2 Templates** (`analysis.md.j2`)
   - Pros: Industry standard, safe, powerful (loops, conditionals), familiar syntax
   - Cons: Extra dependency (already in most Python projects)
   - Example: `{{ company_name }}: {{ idea }}`

#### Recommendation: Jinja2

##### Should We Migrate Prompts to Jinja2?

**Current Prompt System Analysis:**

- Uses Python's `.format()` with named placeholders
- Simple variable substitution only (no conditionals/loops)
- Already has custom `{{include:path}}` syntax for includes
- Works well for current needs

**Recommendation: Keep prompts as-is, use Jinja2 for templates only**

Reasoning:

1. **Different purposes**: Prompts need simple substitution, templates need structure
2. **Existing investment**: Custom include system already works well
3. **Complexity trade-off**: Jinja2 for prompts adds complexity without clear benefit
4. **Migration cost**: Would require rewriting all prompts for minimal gain

**Future consideration**: If we need conditional prompts (e.g., different instructions based on iteration count), then consider Jinja2 migration.

We recommend Jinja2 for templates because:

- Safe template rendering (no code execution risks)
- Supports conditional sections (e.g., different templates for revisions)
- Compatible with future needs (loops for multiple risks, etc.)
- Well-documented and widely understood
- Minimal overhead (already common in Python ecosystem)

### Template Examples

#### Analysis Template (`config/templates/analyst/analysis.md.j2`)

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

#### Metadata Handling (Post-Processing)

After the agent completes the analysis, the pipeline will append metadata as a separate step:

```markdown
---
<!-- Analysis Metadata - Auto-generated, Do Not Edit -->
<!-- 
Idea Input: "{{ idea }}"
Idea Slug: {{ idea_slug }}
Iteration: {{ iteration }}
Timestamp: {{ timestamp }}
Websearches Used: {{ websearch_count }}
Analyst Model: {{ model }}
-->
```

This approach:

- Keeps the original idea input for reference
- Doesn't interfere with agent's content generation
- Provides traceability for debugging
- Can be added/updated by pipeline after agent completion

#### Feedback Template (`config/templates/reviewer/feedback.json.j2`)

```json
{
  "overall_assessment": "[TODO: Brief 2-3 sentence assessment]",
  "strengths": [],
  "critical_issues": [],
  "improvements": [],
  "minor_suggestions": [],
  "iteration_recommendation": "reject",
  "iteration_reason": "[TODO: Explanation for recommendation]",
  "metadata": {
    "iteration": {{ iteration }},
    "timestamp": "{{ timestamp }}",
    "analysis_file": "{{ analysis_file }}"
  }
}
```

## Implementation Plan

### Phase 1: Infrastructure Setup (2 hours)

1. **Create Template Directory Structure**
   - Add `config/templates/` directory
   - Create subdirectories for each agent
   - Add `.j2` template files

2. **Add Template Loading Utility**
   - Create `src/utils/template_operations.py`
   - Implement `load_template()` function
   - Support Jinja2 variable substitution
   - Add caching for performance

3. **Update Pipeline Base**
   - Add template operations to utils
   - Add metadata append functionality
   - Direct implementation without compatibility flag

### Phase 2: Analyst Agent Migration (2 hours)

1. **Create Analysis Templates**
   - Initial analysis template
   - Revision template (with feedback placeholders)
   - Support idea slug and metadata

2. **Update Pipeline for Analyst**
   - Replace empty file creation with template
   - No variables needed for initial template
   - Add metadata append step after agent completion
   - Test with existing prompts

3. **Update Analyst Prompts**
   - Keep `file_edit_rules.md` include (agents still need to Read then Edit)
   - Simplify user prompt to reference pre-filled template
   - Update instructions to mention replacing TODO sections instead of filling empty file

### Phase 3: Reviewer Agent Migration (1 hour)

1. **Create Feedback Template**
   - JSON structure with placeholders
   - Include metadata section
   - Support iteration tracking

2. **Update Pipeline for Reviewer**
   - Replace empty JSON with template
   - Pass context variables
   - Ensure schema compliance

3. **Update Reviewer Prompts**
   - Keep file operation instructions (Read→Edit workflow remains)
   - Update to mention pre-filled JSON structure
   - Focus on filling in TODO fields rather than creating from scratch

### Phase 4: Testing & Validation (2 hours)

1. **Unit Tests**
   - Template loading tests
   - Variable substitution tests
   - File creation tests

2. **Integration Tests**
   - Test through `./test_locally.sh` script
   - Verify agent compatibility with templates
   - Check output quality matches current standards

### Phase 5: Documentation & Cleanup (1 hour)

1. **Update Documentation**
   - Update system-architecture.md
   - Document template system
   - Document metadata post-processing

2. **Clean Up Old Code**
   - Remove redundant prompt sections
   - Archive old prompts
   - Update CLAUDE.md

## Technical Details

### Template Operations Module

```python
# src/utils/template_operations.py

from pathlib import Path
from typing import Any, Dict
from jinja2 import Template, Environment, FileSystemLoader
from functools import lru_cache

class TemplateManager:
    """Manages file templates for agent outputs."""
    
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    @lru_cache(maxsize=32)
    def load_template(self, template_path: str) -> Template:
        """Load and cache a template."""
        return self.env.get_template(template_path)
    
    def render_template(
        self, 
        template_path: str, 
        variables: Dict[str, Any]
    ) -> str:
        """Render a template with variables."""
        template = self.load_template(template_path)
        return template.render(**variables)
    
    def create_file_from_template(
        self,
        template_path: str,
        output_path: Path,
        variables: Dict[str, Any]
    ) -> None:
        """Create a file from a template."""
        content = self.render_template(template_path, variables)
        output_path.write_text(content)
```

### Pipeline Integration

```python
# Updated pipeline.py snippet

async def _run_analyst(self, analyst: AnalystAgent) -> bool:
    """Run analyst for current iteration."""
    
    # Create analysis file from template
    analysis_file = self.iterations_dir / f"iteration_{self.iteration_count}.md"
    if not analysis_file.exists():
        # Create from template (no variables needed for initial structure)
        self.template_manager.create_file_from_template(
            "analyst/analysis.md.j2",
            analysis_file,
            {}  # No variables in template itself
        )
    
    # After agent completes (in _save_analysis_iteration):
    def _append_metadata(self, analysis_file: Path) -> None:
        """Append metadata to completed analysis."""
        metadata = f"""\n---\n<!-- Analysis Metadata - Auto-generated -->\n<!-- 
Idea Input: "{self.idea}"
Idea Slug: {self.slug}
Iteration: {self.iteration_count}
Timestamp: {datetime.now().isoformat()}
Websearches Used: {self.analytics.websearch_count if self.analytics else 0}
-->\n"""
        with open(analysis_file, 'a') as f:
            f.write(metadata)
```

### Updated Prompt Example

```markdown
# Analyst Agent System Prompt (v4 - Template-Based)

You are a Business Analyst Agent that transforms one-liner business ideas into sharp, 
evidence-based analyses in the style of successful Y Combinator applications.

{{include:shared/file_edit_rules.md}}

## Your Task

The analysis file has been pre-created with a structured template. Your task is to:
1. Read the file to see the template structure
2. Edit the file to replace each [TODO] section with comprehensive content
3. Maintain the section headers and structure

Each section has a TODO marker indicating what content is needed and the target word count.

## Core Principles

1. **Brevity wins** - Every sentence must earn its place
2. **Data over narrative** - Specific numbers beat vague claims
3. **10x not 10%** - Focus on why this is radically better
[... rest of principles ...]

## Quality Standards

[... section-specific guidelines ...]

Replace each [TODO] section with appropriate content while maintaining the document structure.
```

## Migration Strategy

### Direct Implementation

```python
# config.py
@dataclass
class SystemConfig:
    template_dir: Path = Path("config/templates")
```

### Implementation Timeline

1. **Day 1**: Deploy infrastructure and templates
2. **Day 1-2**: Update both agents simultaneously
3. **Day 2**: Test with test_locally.sh
4. **Day 2-3**: Deploy and remove old code

## Benefits

1. **Cleaner Architecture**: Clear separation between structure and content
2. **Easier Maintenance**: Template changes don't require prompt updates
3. **Better Onboarding**: New agents can start with structured templates
4. **Improved Testing**: Can test templates independently
5. **Extensibility**: Easy to add new output formats

## Risks & Mitigations

### Risk 1: Agent Confusion

**Risk**: Agents might not understand pre-filled templates
**Mitigation**: Clear TODO markers and section headers

### Risk 2: Template Rigidity

**Risk**: Templates might constrain creative output
**Mitigation**: Templates provide structure, not content

### Risk 3: Breaking Changes

**Risk**: Breaking existing functionality during migration
**Mitigation**: Thorough testing with test_locally.sh before deployment

### Risk 4: Increased Complexity

**Risk**: Adding another layer of abstraction
**Mitigation**: Clear documentation and examples

## Success Metrics

1. **Reduced Prompt Size**: 30-40% reduction in prompt length
2. **Faster Development**: New agents onboard 50% faster
3. **Fewer Errors**: 90% reduction in file operation errors
4. **Cleaner Output**: More consistent document structure

## Timeline

- **Day 1**: Infrastructure and templates (3 hours)
- **Day 2**: Agent migration and testing (4 hours)
- **Day 3**: Documentation and cleanup (1 hour)

Total estimated effort: 8 hours

## Conclusion

This decoupling will significantly improve the system's maintainability and extensibility while reducing complexity in agent prompts. The template-based approach aligns with industry best practices and provides a cleaner separation of concerns.

## Next Steps

1. Review and approve this design
2. Create feature branch
3. Implement Phase 1 infrastructure
4. Test in development environment
5. Gradual production rollout

---

*Document created: 2025-08-25*
