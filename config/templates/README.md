# File Templates

This directory contains structured file templates for agent outputs.

## Purpose

Templates provide the document structure with embedded TODO instructions, while prompts focus on principles and approach. This separation allows changing document structure without modifying agent prompts.

## Directory Structure

```text
config/templates/
└── agents/
    ├── analyst/
    │   └── analysis.md    # Analysis document template with TODOs
    └── reviewer/
        └── feedback.json  # Feedback JSON template with TODOs
```

## How Templates Work

1. **Pipeline creates files from templates** - When starting a task, the pipeline copies the appropriate template
2. **Agents read the template** - Agents see the structure with TODO instructions
3. **Agents replace TODOs** - In a single Edit operation, agents replace all content

## Template Design Principles

- **Self-documenting**: Each TODO section includes detailed instructions
- **Structure-focused**: Templates define WHAT goes where
- **Word counts included**: Each section specifies target length
- **Examples embedded**: TODOs include examples of expected content

## Example Template Structure

```markdown
## The Problem

[TODO: 150 words - Describe the specific acute pain your target customers face. Include:

- A real, urgent problem (not a nice-to-have)  
- Actual user quotes or scenarios that illustrate the pain
- Quantify the pain: hours wasted, dollars lost, opportunities missed
- Be specific about WHO experiences this problem and WHEN

Example: "Small restaurant owners waste 3-4 hours weekly on inventory management..."]
```

## Adding New Templates

1. Create template file in appropriate agent directory
2. Use clear TODO markers with instructions
3. Include word counts and examples
4. Keep structure consistent with existing templates

## Benefits

- **Maintainability**: Change structure without touching prompts
- **Clarity**: Agents see exactly what's expected
- **Consistency**: All analyses follow the same structure
- **Efficiency**: Agents complete tasks in fewer turns

