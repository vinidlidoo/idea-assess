# System Architecture - Business Idea Evaluator

**Version**: 2.6 (Batch Processing Complete)  
**Last Updated**: 2025-09-06  
**Status**: Production-Ready with Batch Processing Support  

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Components](#system-components)
4. [Agent System](#agent-system)
5. [Pipeline Architecture](#pipeline-architecture)
6. [Configuration System](#configuration-system)
7. [Context System](#context-system)
8. [Result Patterns](#result-patterns)
9. [Prompt System](#prompt-system)
10. [Logging and Analytics](#logging-and-analytics)
11. [Batch Processing](#batch-processing)
12. [File Structure](#file-structure)
13. [Data Flow](#data-flow)
14. [Extension Points](#extension-points)
15. [Design Decisions](#design-decisions)
16. [Performance Considerations](#performance-considerations)
17. [Error Handling](#error-handling)
18. [Testing Strategy](#testing-strategy)
19. [Future Enhancements](#future-enhancements-phase-34)
20. [Maintenance Notes](#maintenance-notes)

## Overview

The Business Idea Evaluator is an AI-powered system that transforms one-liner business ideas into comprehensive market analyses using Claude SDK. The system employs a multi-agent architecture with feedback loops to ensure high-quality output.

### Core Capabilities

- **Idea Analysis**: Convert one-liner ideas into 1000+ word market analyses
- **Iterative Refinement**: Reviewer feedback loop for quality improvement
- **Citation Verification**: FactChecker agent with parallel execution and veto power
- **Field Standardization**: Consistent field naming across all feedback systems
- **Web Research**: Integration with WebSearch and WebFetch for comprehensive market data
- **Task Organization**: TodoWrite tool for complex analysis planning
- **Flexible Prompting**: Configurable system prompts for different analysis styles
- **Comprehensive Logging**: Detailed analytics and debugging capabilities

### Technology Stack

- **Language**: Python 3.10+ (required for pattern matching)
- **AI Model**: Claude Opus 4.1 via Claude SDK
- **Package Management**: uv (modern Python package manager)
- **External Tools**: MCP protocol (not yet implemented)
- **Version Control**: Git

## Architecture Principles

### 1. Clean Separation of Concerns

Each component has a single, well-defined responsibility:

- **Config**: What the agent can do (capabilities, limits)
- **Context**: Where to read/write for this specific run
- **Result**: Simple success/error outcomes
- **Agent**: Business logic for processing

### 2. Direct Configuration Pattern

No complex override systems or defaults:

```python
# Direct modification - clear and simple
analyst_config.system_prompt = "experimental/analyst/concise.md"
analyst_config.allowed_tools = []
```

### 3. Explicit Over Implicit

- Explicit typed paths in contexts
- Clear inheritance hierarchies
- No hidden state or magic behaviors

### 4. Type Safety with Generics

Agents use generics for compile-time type checking:

```python
class BaseAgent(ABC, Generic[TConfig, TContext]):
    def __init__(self, config: TConfig): ...
    async def process(self, input_data: str, context: TContext) -> AgentResult: ...
```

### 5. Pattern Matching for Control Flow

Leverages Python 3.10+ pattern matching for clean result handling:

```python
match result:
    case Success():
        # Continue processing
    case Error(message=msg):
        logger.error(f"Failed: {msg}")
```

## System Components

### Core Layer (`src/core/`)

The foundation of the system, providing:

1. **config.py** - Configuration management
2. **agent_base.py** - Abstract agent interface
3. **pipeline.py** - Orchestration logic
4. **types.py** - Shared type definitions
5. **run_analytics.py** - Analytics and telemetry

### Agent Layer (`src/agents/`)

Concrete agent implementations:

1. **analyst.py** - Business idea analysis
2. **reviewer.py** - Quality review and feedback
3. **fact_checker.py** - Citation verification and accuracy checking
4. *(Future: judge.py - Evaluation and grading)*
5. *(Future: synthesizer.py - Comparative reports)*

### Interface Layer (`src/`)

User-facing interfaces:

1. **cli.py** - Command-line interface

### Utility Layer (`src/utils/`)

Supporting utilities:

1. **file_operations.py** - Prompt loading with includes, template operations
2. **text_processing.py** - Text manipulation (slugs, etc.)
3. **logger.py** - Structured logging system
4. **result_formatter.py** - Output formatting
5. **json_validator.py** - JSON schema validation

## Agent System

### Agent Hierarchy

```text
BaseAgent[TConfig, TContext] (Abstract)
    ├── AnalystAgent[AnalystConfig, AnalystContext]
    ├── ReviewerAgent[ReviewerConfig, ReviewerContext]
    ├── FactCheckerAgent[FactCheckerConfig, FactCheckContext]
    ├── (Phase 3) JudgeAgent[JudgeConfig, JudgeContext]
    └── (Phase 4) SynthesizerAgent[SynthesizerConfig, SynthesizerContext]
```

### AnalystAgent

**Purpose**: Transform business ideas into comprehensive analyses

**Key Responsibilities**:

- Generate initial market analysis from one-liner
- Incorporate reviewer feedback for revisions
- Manage web research when enabled
- Ensure minimum word count requirements

**Configuration**:

```python
@dataclass
class AnalystConfig(BaseAgentConfig):
    max_websearches: int = 10
    min_words: int = 3000
    allowed_tools: list[str] = ["WebSearch", "WebFetch", "TodoWrite"]
```

**Context**:

```python
@dataclass
class AnalystContext(BaseContext):
    analysis_output_path: Path  # Where to write analysis
    feedback_input_path: Path | None  # Previous feedback (if revision)
    idea_slug: str
    websearch_count: int = 0
```

### ReviewerAgent

**Purpose**: Evaluate analyses and provide structured feedback

**Key Responsibilities**:

- Review analysis quality
- Generate actionable feedback
- Recommend approval or revision
- Track iteration progress

**Configuration**:

```python
@dataclass
class ReviewerConfig(BaseAgentConfig):
    max_iterations: int = 3
    strictness: str = "normal"  # lenient, normal, strict
    allowed_tools: list[str] = []  # No external tools needed
```

**Context**:

```python
@dataclass
class ReviewerContext(BaseContext):
    analysis_input_path: Path  # Analysis to review
    feedback_output_path: Path  # Where to write feedback
```

### FactCheckerAgent

**Purpose**: Verify citations and claims in analyses

**Key Responsibilities**:

- Verify citations against source material
- Identify unsupported or questionable claims
- Provide veto power for iteration approval
- Run in parallel with ReviewerAgent

**Configuration**:

```python
@dataclass
class FactCheckerConfig(BaseAgentConfig):
    webfetch_per_iteration: int = 10  # WebFetch calls allowed per iteration
    
    # Default tools for fact-checking
    allowed_tools: list[str] = field(
        default_factory=lambda: ["WebFetch", "Edit", "TodoWrite"]
    )
```

**Context**:

```python
@dataclass
class FactCheckContext(BaseContext):
    analysis_input_path: Path  # Analysis to fact-check
    fact_check_output_path: Path  # Where to write results
    max_iterations: int = 3  # Shared with ReviewerConfig
```

## Pipeline Architecture

### Pipeline Modes

```python
class PipelineMode(Enum):
    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # With feedback loop
    ANALYZE_REVIEW_WITH_FACT_CHECK = "analyze_review_with_fact_check"  # Parallel verification
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # Phase 3
    FULL_EVALUATION = "full_evaluation"  # Phase 4
```

### Pipeline Flow

```text
1. ANALYZE Mode:
   Input → Analyst → Output

2. ANALYZE_AND_REVIEW Mode:
   Input → Analyst → Reviewer → [Approve/Revise]
            ↑                        |
            └────── Revision ────────┘

3. ANALYZE_REVIEW_WITH_FACT_CHECK Mode:
   Input → Analyst → [Parallel: Reviewer + FactChecker] → [Both Approve/Either Rejects]
            ↑                                                    |
            └──────────────── Revision ─────────────────────────┘
   
   Note: FactChecker has veto power - can force revision even if Reviewer approves. And vice-versa

4. Future modes add Judge and Synthesizer stages
```

### State Management

The pipeline maintains minimal state:

```python
class AnalysisPipeline:
    # Configuration
    system_config: SystemConfig
    analyst_config: AnalystConfig
    reviewer_config: ReviewerConfig
    fact_checker_config: FactCheckerConfig | None = None
    
    # Runtime state
    slug: str  # Generated from idea
    iteration_count: int = 0
    current_analysis_file: Path | None = None
    last_feedback_file: Path | None = None
    analytics: RunAnalytics | None = None
```

### Iteration Control

- Max iterations from `ReviewerConfig.max_iterations`
- Early termination on reviewer approval (or both reviewer and fact-checker in parallel mode)
- Veto power: FactChecker can force revision even if reviewer approves
- Automatic symlink updates to latest iteration

## Configuration System

### Three-Level Hierarchy

```text
SystemConfig (System-wide settings)
    ├── paths (project_root, analyses_dir, etc.)
    ├── limits (output_limit, max_file_size)
    ├── defaults (slug_max_length, etc.)
    └── template_dir (Path to template directory)

BaseAgentConfig (Common agent settings)
    ├── max_turns: int
    ├── prompts_dir: Path
    ├── system_prompt: str
    └── allowed_tools: list[str]

Specific Agent Configs (Agent-specific settings)
    ├── AnalystConfig
    │   ├── max_websearches: int
    │   └── min_words: int
    ├── ReviewerConfig
    │   ├── max_iterations: int
    │   └── strictness: str
    └── FactCheckerConfig
        ├── max_verifications: int
        └── webfetch_per_iteration: int
```

### Configuration Flow

1. **Creation**: Factory creates defaults
2. **CLI Override**: Direct modification of config fields
3. **Pipeline Usage**: Configs passed to agents unchanged

```python
# 1. Create defaults
system_config, analyst_config, reviewer_config, fact_checker_config = create_default_configs(Path.cwd())

# 2. Apply CLI overrides (direct modification)
if args.no_websearch:
    analyst_config.allowed_tools = []
if args.analyst_prompt:
    analyst_config.system_prompt = args.analyst_prompt

# 3. Pass to pipeline
pipeline = AnalysisPipeline(
    idea=idea,
    system_config=system_config,
    analyst_config=analyst_config,
    reviewer_config=reviewer_config,
    fact_checker_config=fact_checker_config if args.with_fact_check else None
)
```

## Context System

### Purpose

Contexts provide runtime-specific information to agents:

- Where to read input
- Where to write output
- Current iteration number
- Reference to analytics

### Context Hierarchy

```text
BaseContext (Minimal shared state)
    ├── iteration: int
    ├── tools: list[str] | None
    └── run_analytics: RunAnalytics | None

AnalystContext (Analysis-specific)
    ├── analysis_output_path: Path
    ├── previous_analysis_input_path: Path | None
    ├── feedback_input_path: Path | None
    ├── idea_slug: str
    └── websearch_count: int

ReviewerContext (Review-specific)
    ├── analysis_input_path: Path
    └── feedback_output_path: Path
```

### Context Creation

Contexts are created by the pipeline with explicit paths:

```python
context = AnalystContext(
    iteration=self.iteration_count,
    idea_slug=self.slug,
    analysis_output_path=Path("analyses/idea/iterations/iteration_1.md"),
    feedback_input_path=None,  # None for first iteration
    run_analytics=self.analytics
)
```

## Result Patterns

### Simple Success/Error Pattern

```python
@dataclass
class Success:
    """Successful agent execution."""
    # No data needed - outputs written to context paths

@dataclass
class Error:
    """Failed agent execution."""
    message: str

AgentResult = Success | Error
```

### Pattern Matching Usage

```python
result = await agent.process(input_data, context)
match result:
    case Success():
        logger.info("Processing succeeded")
        # Continue pipeline
    case Error(message=msg):
        logger.error(f"Processing failed: {msg}")
        return PipelineResult(success=False, error=msg)
```

### Pipeline Result

```python
class PipelineResult(TypedDict):
    success: bool
    idea: str
    slug: str
    analysis_file: str | None  # Path to final analysis
    iterations_completed: int | None
    error: str | None  # Error message if failed
```

## Prompt System

### Prompt Organization

```text
config/prompts/
├── agents/
│   ├── analyst/
│   │   ├── system.md           # Analyst principles
│   │   ├── tools_system.md     # Tool-augmented system prompt
│   │   ├── snippets/           # Conditional content
│   │   │   ├── web_tools_enabled.md
│   │   │   └── web_tools_disabled.md
│   │   └── user/               # User message templates
│   │       ├── initial.md      # Initial analysis
│   │       └── revision.md     # Revision instructions
│   ├── reviewer/
│   │   ├── system.md           # Reviewer principles
│   │   ├── tools_system.md     # Tool-augmented system prompt
│   │   └── user/
│   │       └── review.md       # Review instructions
│   ├── factchecker/
│   │   ├── system.md           # FactChecker principles
│   │   └── user/
│   │       └── fact-check.md   # Fact-checking instructions
│   ├── judge/
│   │   └── system.md           # Judge prompt (Phase 3)
│   └── synthesizer/
│       └── system.md           # Synthesizer prompt (Phase 4)
├── experimental/
│   ├── analyst/
│   │   ├── citation-strict.md  # Strict citation requirements
│   │   └── concise.md          # Concise analysis format
│   ├── reviewer/               # Experimental reviewer prompts
│   └── judge/                  # Future judge prompts
├── shared/
│   └── file_edit_rules.md     # Shared file editing rules
└── versions/                   # Historical prompt versions
    ├── analyst/
    │   ├── analyst_v1.md through analyst_v5_citation_strict.md
    │   └── analyst_old.md
    └── reviewer/
        ├── reviewer_v1.md
        ├── reviewer_v1_simple.md
        └── reviewer_old.md
```

### Prompt Loading

1. **System Prompts**: Loaded via `load_prompt_with_includes()`
   - Supports `{{include:path}}` directives
   - Cached for performance

2. **Template Prompts**: Loaded via `load_prompt()`
   - Simple file loading
   - Used for message templates

### Prompt Resolution

```python
def get_system_prompt_path(self) -> str:
    agent_type = self.agent_name.lower()
    prompt = self.config.system_prompt
    
    if "/" not in prompt:
        # Simple filename: agents/analyst/system.md
        return f"agents/{agent_type}/{prompt}"
    else:
        # Full path: experimental/analyst/concise.md
        return prompt
```

### Key Utilities

**file_operations.py**: Prompt loading with includes, template operations  
**text_processing.py**: Slug generation, text manipulation  
**logger.py**: Structured logging with SDK error awareness  
**result_formatter.py**: CLI output formatting  
**json_validator.py**: Schema validation for agent outputs with field normalization

## Logging and Analytics

### Structured Logging System

The system uses a comprehensive logging architecture that supports both individual pipeline runs and batch processing:

- **Individual Runs**: Logs stored in `logs/runs/{run_id}/`
- **Batch Processing**: Orchestration logs in `logs/batch/{timestamp}_batch/`
- **Dual Logging**: Batch mode maintains separate logs for orchestration and individual pipelines
- **SDK Error Awareness**: Special handling for Claude SDK errors and rate limits
- **JSON-based Debug Logs**: Structured logs for detailed debugging

### RunAnalytics System

Provides comprehensive telemetry for analysis runs:

- **Turn Tracking**: Monitors API calls and interactions per agent
- **Timing Metrics**: Captures duration for each processing stage
- **Token Usage**: Tracks input/output tokens for cost analysis
- **WebSearch Metrics**: Counts and categorizes external tool usage
- **Iteration Tracking**: Records revision cycles and approvals

## Batch Processing

### Batch Processing Architecture

Batch processing enables concurrent evaluation of multiple business ideas with configurable parallelism:

- **Concurrent Execution**: Process 2-5 ideas simultaneously (configurable)
- **Markdown-based Input**: Ideas parsed from markdown files using H1 headers as delimiters
- **Atomic File Management**: Safe movement of ideas between pending/completed/failed states
- **Progress Tracking**: Real-time console display of batch progress
- **Error Resilience**: Individual pipeline failures don't stop the batch

### Implementation

```python
class BatchProcessor:
    async def process_batch(self, ideas_file: Path, max_concurrent: int = 3):
        # Parse ideas from markdown
        ideas = await self.file_manager.parse_ideas_file(ideas_file)
        
        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [self._process_with_semaphore(idea, semaphore) for idea in ideas]
        
        # Gather results with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
```

### CLI Integration

```bash
# Process ideas from pending.md with 2 concurrent pipelines
python -m src.cli --batch --max-concurrent 2

# Process from custom file
python -m src.cli --batch --ideas-file custom-ideas.md
```

### File Management

The FileManager handles atomic operations for idea files:

- **Pending**: Ideas waiting to be processed (`ideas/pending.md`)
- **Completed**: Successfully processed ideas (`ideas/completed.md`)
- **Failed**: Ideas that encountered errors (`ideas/failed.md`)

Each idea is moved atomically after processing to prevent data loss.

## File Structure

```text
idea-assess/
├── src/
│   ├── core/                  # Core system components
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration classes
│   │   ├── agent_base.py      # Abstract agent
│   │   ├── pipeline.py        # Pipeline orchestration
│   │   ├── types.py           # Consolidated types (contexts, results, modes)
│   │   └── run_analytics.py   # Analytics system
│   ├── agents/                # Concrete agents
│   │   ├── __init__.py
│   │   ├── analyst.py         # Analyst implementation
│   │   ├── reviewer.py        # Reviewer implementation
│   │   └── fact_checker.py    # FactChecker implementation
│   ├── batch/                 # Batch processing components
│   │   ├── __init__.py
│   │   ├── processor.py       # Batch orchestration with concurrency
│   │   └── file_manager.py    # Atomic file operations for ideas
│   ├── utils/                 # Utilities
│   │   ├── __init__.py
│   │   ├── file_operations.py # Prompt loading, template operations
│   │   ├── text_processing.py # Slug creation, text manipulation
│   │   ├── logger.py          # Structured logging with SDK awareness
│   │   ├── result_formatter.py# CLI output formatting
│   │   └── json_validator.py  # JSON validation for agent outputs
│   └── cli.py                 # CLI interface with batch support
├── config/
│   ├── prompts/               # Agent prompts (principles-focused)
│   │   ├── agents/            # Agent-specific prompts
│   │   ├── experimental/      # Alternative prompt versions
│   │   ├── shared/            # Shared prompt components
│   │   └── versions/          # Historical versions
│   └── templates/             # File templates (structure-focused)
│       ├── agents/            # Agent-specific templates
│       └── shared/            # Shared templates
├── ideas/                     # Idea management files
│   ├── pending.md             # Ideas waiting to be processed
│   ├── completed.md           # Successfully processed ideas
│   └── failed.md              # Ideas that encountered errors
├── analyses/                  # Output directory
│   └── {idea-slug}/
│       ├── analysis.md        # Latest (symlink)
│       ├── metadata.json      # Metadata
│       └── iterations/        # All iterations
├── logs/                      # Logging directory
│   ├── runs/                  # Individual pipeline runs
│   │   └── {run_id}/          # Timestamped run directory
│   └── batch/                 # Batch processing logs
│       └── {timestamp}_batch/ # Batch orchestration logs
├── docs/                      # Documentation
├── session-logs/              # Development logs
└── test_locally.sh           # Test harness
```

## Data Flow

### Analysis Creation Flow

```text
1. User Input
   └─> CLI parsing
       └─> Config creation/modification
           └─> Pipeline initialization
               └─> Agent execution
                   └─> File output
                       └─> Result formatting
                           └─> User display
```

### Iteration Flow (with Review)

```text
1. Initial Analysis
   ├─> Pipeline creates iteration_1.md from template with TODO instructions
   ├─> Analyst agent reads template and replaces TODO sections
   └─> Pipeline updates analysis.md symlink

2. Review Cycle
   ├─> Pipeline creates reviewer_feedback_iteration_1.json from template
   ├─> Reviewer reads iteration_1.md
   ├─> Reviewer replaces TODO sections in feedback JSON
   └─> Pipeline checks recommendation

3. Revision (if needed)
   ├─> Pipeline creates iteration_2.md from template
   ├─> Analyst reads previous analysis and reviewer feedback
   ├─> Analyst replaces TODO sections with revised content
   └─> Pipeline updates analysis.md symlink

4. Repeat until approved or max_iterations
```

## Extension Points

### Adding New Agents (Phase 3/4)

1. **Create Config Class**:

```python
@dataclass
class JudgeConfig(BaseAgentConfig):
    grading_criteria: list[str]
    grade_scale: str = "A-F"
```

1. **Create Context Class**:

```python
@dataclass
class JudgeContext(BaseContext):
    analysis_input_path: Path
    evaluation_output_path: Path
```

1. **Implement Agent**:

```python
class JudgeAgent(BaseAgent[JudgeConfig, JudgeContext]):
    async def process(self, input_data: str, context: JudgeContext) -> AgentResult:
        # Implementation
```

1. **Add Pipeline Mode**:

```python
PipelineMode.ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"
```

### Adding New Tools

1. Update `BaseAgentConfig.allowed_tools` default
2. Add tool configuration in agent's `process()` method
3. Update prompt templates to include tool instructions

### Custom Prompts

1. Create prompt file in `config/prompts/experimental/`
2. Use CLI flag: `--analyst-prompt experimental/analyst/custom.md`
3. Or modify config: `analyst_config.system_prompt = "custom.md"`

## Design Decisions

### Why Direct Config Modification?

**Problem**: Override patterns create confusion about which value is active  
**Solution**: Direct modification makes state explicit and debuggable

### Why Pattern Matching?

**Problem**: Complex if/else chains for result handling  
**Solution**: Pattern matching provides clear, type-safe control flow

### Why Explicit Typed Paths?

**Problem**: String paths are error-prone and hard to track  
**Solution**: Typed Path objects in contexts ensure correctness

### Why Separate Config and Context?

**Problem**: Mixing configuration and runtime state causes confusion  
**Solution**: Clear separation - config is capability, context is runtime

### Why Template-Prompt Decoupling?

**Problem**: Prompts contained both structure and principles, making changes difficult  
**Solution**: Templates define structure with TODOs, prompts focus on principles only

**Implementation**:

- Templates in `config/templates/agents/`
- Templates contain TODO placeholders for agents to fill
- Pipeline pre-creates files from templates before agent runs
- Agents read templates and replace TODOs with actual content
- Clear separation of structure (templates) from behavior (prompts)

### Why Success/Error Instead of Booleans?

**Problem**: Boolean returns lose error information  
**Solution**: Success/Error pattern preserves error details for debugging

### Why No Metadata in AgentResult?

**Problem**: Metadata wasn't being used but added complexity  
**Solution**: Simple Success/Error with outputs written to files

### Why RunAnalytics Over Simple Logging?

**Problem**: Need structured data for analysis and debugging  
**Solution**: RunAnalytics provides comprehensive telemetry

## Performance Considerations

### Caching

- Prompt templates cached via `@lru_cache`
- Reduces file I/O for repeated loads

### Async Operations

- All agent operations are async
- Enables future parallelization
- Non-blocking I/O for Claude SDK

### File Pre-creation

- Pipeline creates files from templates in `config/templates/` (implemented)
- Templates contain structure with TODO instructions
- Agents replace TODO sections with content
- Enables clear separation of structure from content

## Error Handling

### Agent Level

- Try/catch around SDK calls
- Return Error with descriptive message
- Log errors with context

### Pipeline Level

- Pattern match on agent results
- Early termination on errors
- Comprehensive error reporting

### System Level

- Graceful degradation (e.g., no websearch fallback)
- Timeout handling in test harness
- Interrupt signal handling

## Testing Strategy

### Unit Tests (✅ COMPLETE - Updated 2025-09-04)

Following comprehensive test fixes and quality improvements:

- **107 tests** covering all major components with **81% code coverage**
- **~20s execution time** - comprehensive with real async operations
- **Behavior-focused** - tests what agents DO, not HOW they do it
- **Strategic mocking** - Mock at integration boundaries (SDK, file I/O)
- **Well-organized** - tests grouped by component with shared fixtures
- **Field standardization** - All tests updated for `iteration_recommendation` field
- **FactChecker tests** - Complete coverage with proper mocking patterns

Test files structure:

- `test_agents/` - Agent implementations (analyst, reviewer, fact_checker)
- `test_core/` - Core components (config, pipeline, run_analytics)
- `test_utils/` - Utilities (file_ops, json_validator, logger, etc.)
- `test_cli.py` - CLI interface tests
- `test_sdk_errors.py` - SDK error handling tests

See `tests/README.md` for detailed testing philosophy and patterns.

### Integration Tests

- Test pipeline end-to-end
- Use test_locally.sh for scenarios
- Verify iteration flows

### Manual Testing

- CLI with various flags
- Different prompt configurations
- Error scenarios

## Future Enhancements (Phase 3/4)

### JudgeAgent

- Evaluate analyses on 7 criteria
- Generate letter grades (A-F)
- Provide scoring rationale

### SynthesizerAgent

- Compare multiple analyses
- Generate executive summaries
- Create trend reports

### Parallel Processing

- Run multiple analyses concurrently
- Batch processing mode
- Queue management

## Field Standardization (2025-09-04)

Important field name changes for consistency:

- Reviewer feedback: `recommendation` → `iteration_recommendation`
- Values: "approve" or "revise"
- Fact-checker uses same field name and values
- `overall_assessment` field required in all feedback
- `minor_suggestions` must be objects, not strings
- `iteration_reason` field tracks why revision is needed

## Maintenance Notes

### Debugging

1. Enable debug mode: `--debug`
2. Check `logs/runs/{run_id}/` for details
3. Review message history in JSONL
4. Analyze RunAnalytics summary

### Performance Tuning

1. Adjust `max_turns` for agents
2. Modify `max_websearches` for speed
3. Tune `min_words` for quality
4. Configure timeouts in test harness

--

*For implementation history and decisions, see `docs/phase2-architecture-simplification-v4.md`*  
*For session-by-session development logs, see `session-logs/`*
