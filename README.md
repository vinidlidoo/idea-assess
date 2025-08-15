# Business Idea Evaluator

AI-powered business idea evaluation system using Claude SDK and MCP tools.

## Setup

1. **Install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Claude Code CLI:**
   - Ensure you're logged into Claude Code: `claude login`
   - The SDK uses your Claude Code authentication

## Usage

### Basic Analysis

```bash
python src/cli.py "Your business idea here"
```

Example:

```bash
python src/cli.py "AI-powered fitness app for seniors with mobility limitations"
```

### With Review Feedback

```bash
python src/cli.py "Your idea" --with-review --max-iterations 2
```

### Debug Mode

To enable detailed logging:

```bash
python src/cli.py "Your idea" --debug
```

Logs are saved to `logs/runs/` with structured format (summary.md, events.jsonl, metrics.json)

## Important Notes

### WebSearch Performance

- WebSearch operations via SDK take 30-120 seconds each
- This is normal behavior - the script will wait patiently
- Run directly in terminal (not through other tools) to avoid timeouts
- Total analysis may take 3-5 minutes depending on searches performed
- Disable with `--no-websearch` for faster testing

### Logging

- Production logs: `logs/runs/` - Organized by run with structured format
- Test logs: `logs/tests/` - Test harness output with structured logs
- Archive: `logs/archive/` - Old logs (auto-archived after 10 runs)
- Each run creates: summary.md, events.jsonl, metrics.json, debug.log

### Output

Analyses are saved to:

- `analyses/{idea-slug}/analysis_{timestamp}.md`
- Latest analysis is symlinked to `analysis.md`

## Project Structure

```text
idea-assess/
├── src/
│   └── analyze.py          # Main analyzer script
├── config/
│   └── prompts/           # Agent prompt templates
├── analyses/              # Generated analyses
├── logs/                  # Debug logs (with --debug flag)
└── test_ideas.txt         # Sample ideas for testing
```

## Development

See `docs/` for detailed documentation about the architecture and implementation.

### Key Files

- `requirements.md` - Full project requirements
- `implementation-plan.md` - Phased development plan
- `docs/websearch-timeout-investigation.md` - WebSearch performance analysis

## Phase 1 Status: ✅ Complete

- Working Analyst agent with WebSearch
- Debug logging capability
- Proper handling of slow WebSearch operations
