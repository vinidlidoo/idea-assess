# Experimental Prompts

This folder contains experimental system prompts for testing and A/B comparisons.

## Structure

```text
experimental/
├── analyst/       # Experimental analyst prompts
├── reviewer/      # Experimental reviewer prompts  
└── judge/         # Experimental judge prompts
```

## Usage

Use CLI flags to override the default system prompts:

```bash
# Use experimental analyst prompt
python -m src.cli "AI fitness app" --analyst-prompt experimental/analyst/yc_style

# Use experimental reviewer prompt
python -m src.cli "AI fitness app" --with-review --reviewer-prompt experimental/reviewer/strict
```

## Creating New Experimental Prompts

1. Create a new `.md` file in the appropriate agent folder
2. Use the file-based prompt format (agents must use Read/Edit tools)
3. Include the file edit rules: `{{include:shared/file_edit_rules.md}}`
4. Test with the CLI override flag

## Naming Convention

- Use descriptive names: `yc_style.md`, `academic.md`, `concise.md`
- Avoid version numbers (use git for versioning)
- Keep names short but meaningful

## Notes

- All prompts must be file-based (no direct output)
- Experimental prompts are not guaranteed to be stable
- Use git to track changes and iterations

