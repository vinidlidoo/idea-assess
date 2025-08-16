# Business Idea Evaluator

AI-powered business idea evaluation system using Claude SDK and MCP tools.

## Overview

This system transforms one-liner business ideas into comprehensive market analyses through a multi-agent pipeline:

1. **Analyst Agent** - Expands ideas into full business analyses with market research
2. **Reviewer Agent** - Provides feedback and quality improvements
3. **Judge Agent** (Coming Soon) - Grades analyses on 7 evaluation criteria
4. **Synthesizer Agent** (Coming Soon) - Creates comparative reports across multiple ideas

## Setup

1. **Install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

2. **Configure API Key:**
   - Get API key from [console.anthropic.com](https://console.anthropic.com)
   - Set environment variable: `export ANTHROPIC_API_KEY=your-key-here`

## Usage

### Basic Analysis

```bash
python src/cli.py analyze "Your business idea here"
```

Example:

```bash
python src/cli.py analyze "AI-powered fitness app for seniors"
```

### With Reviewer Feedback Loop

```bash
python src/cli.py analyze "Your idea" --with-review --max-iterations 3
```

### Debug Mode

Enable detailed logging:

```bash
python src/cli.py analyze "Your idea" --debug
```

### Disable WebSearch (Faster Testing)

```bash
python src/cli.py analyze "Your idea" --no-websearch
```

## Output Structure

```text
analyses/
└── {idea-slug}/
    ├── analysis.md              # Final analysis
    ├── reviewer_feedback.json   # Latest feedback
    ├── metadata.json           # Run metadata
    └── iterations/             # Iteration history
        ├── iteration_1.md
        ├── iteration_2.md
        └── reviewer_feedback_iteration_1.json
```

## Architecture

### Core Components

- **Pipeline** (`src/core/pipeline.py`) - Orchestrates agent workflow
- **BaseAgent** (`src/core/agent_base.py`) - Abstract base for all agents
- **Message Processor** - Handles streaming responses with memory management
- **Archive Manager** - Maintains analysis history with automatic rotation

### Agents

- **AnalystAgent** (`src/agents/analyst.py`) - Market research and analysis
- **ReviewerAgent** (`src/agents/reviewer.py`) - Quality assessment and feedback
- **Judge** (Phase 3) - Grading and evaluation
- **Synthesizer** (Phase 4) - Comparative reporting

### Key Features

- **File-based communication** between agents for reliability
- **Iterative refinement** with configurable max iterations
- **Structured logging** with JSON events and metrics
- **Automatic archiving** of previous analyses
- **WebSearch integration** for real-time market data

## Development Status

### ✅ Phase 1: Analyst Agent (Complete)

- Single-agent analysis with WebSearch
- Basic file output structure

### ✅ Phase 2: Reviewer Feedback Loop (Complete)

- Multi-iteration refinement
- File-based agent communication
- Comprehensive test coverage
- All critical bugs fixed

### 🚧 Phase 3: Judge Evaluation (Next)

- Letter grade assessment (A-D)
- 7 evaluation criteria
- Structured scoring

### 📅 Phase 4: Synthesizer Reports (Planned)

- Comparative analysis across ideas
- Batch processing support

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html
```

## Performance Notes

- **WebSearch**: 30-120 seconds per search (normal SDK behavior)
- **Full Analysis**: 2-5 minutes depending on iterations
- **Memory**: Efficient streaming with rolling buffer implementation
- **Concurrency**: Single-threaded for reliability

## Documentation

- `requirements.md` - Complete project requirements
- `implementation-plan.md` - Phased development roadmap
- `CLAUDE.md` - Project context and conventions
- `session-logs/` - Detailed development history
- `TODO.md` - Current task tracking

## Contributing

See session logs for development patterns and conventions. Key principles:

1. File-based communication between agents
2. Comprehensive error handling
3. Structured logging for debugging
4. Test coverage for new features

## License

[License information if applicable]
