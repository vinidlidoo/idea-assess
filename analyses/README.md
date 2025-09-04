# Analyses Directory

Output directory for business idea analyses.

## Structure

```text
analyses/
└── {idea-slug}/
    ├── analysis.md              # Final analysis (symlink to latest)
    ├── metadata.json           # Run metadata and statistics
    └── iterations/             # All iteration files
        ├── iteration_N.md
        ├── reviewer_feedback_iteration_N.json
        └── fact_check_iteration_N.json
```

## Key Files

- **analysis.md**: Symlink to the latest iteration
- **metadata.json**: Word count, iterations, timestamps
- **iterations/**: Complete history of all iterations

## Usage Examples

```bash
# Simple analysis
.venv/bin/python -m src.cli "Your idea"
# Creates: analyses/your-idea/

# With review loop
.venv/bin/python -m src.cli "Your idea" --with-review
# Creates additional reviewer feedback files

# With fact-checking
.venv/bin/python -m src.cli "Your idea" --with-review --with-fact-check
# Creates parallel fact-check results
```

## Iteration Workflow

1. Pipeline creates file from template with TODOs
2. Agent replaces TODOs with actual content
3. Reviewer/FactChecker provide feedback
4. If revision needed, process repeats
5. Symlink updated to point to latest iteration
