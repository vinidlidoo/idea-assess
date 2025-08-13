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
python src/analyze.py "Your business idea here"
```

Example:

```bash
python src/analyze.py "AI-powered fitness app for seniors with mobility limitations"
```

### Debug Mode

To enable detailed message logging:

```bash
python src/analyze.py "Your idea" --debug
```

Debug logs are saved to `logs/debug_YYYYMMDD_HHMMSS.json`

## Important Notes

### WebSearch Performance

- WebSearch operations via SDK take 30-120 seconds each
- This is normal behavior - the script will wait patiently
- Run directly in terminal (not through other tools) to avoid timeouts
- Total analysis may take 3-5 minutes depending on searches performed

### Output

Analyses are saved to:

- `analyses/{idea-slug}/analysis_{timestamp}.md`
- Latest analysis is symlinked to `analysis.md`

## Project Structure

```
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
