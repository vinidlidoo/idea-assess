# Pipeline Architecture Options - DECISION MADE

## Context

The pipeline currently has parameters that duplicate configuration:

- `use_websearch` duplicates `AnalystConfig.default_tools`
- `max_iterations` duplicates `ReviewerConfig.max_review_iterations`
- Parameters are passed through multiple layers

## Decision: Mode-Driven Pipeline

After evaluating 7 different options, we've decided on a **mode-driven pipeline architecture** that:

1. Uses verb-based pipeline modes (ANALYZE, ANALYZE_AND_REVIEW, etc.)
2. Eliminates redundant parameters - everything comes from config
3. Reuses existing context classes (no new abstractions)
4. Makes the pipeline a pure orchestrator

## Final Design

See: `2025-08-20-pipeline-architecture-refactoring.md` for complete implementation details and task list.

### Key Benefits

- **Config-driven**: All settings come from AnalysisConfig
- **Simple interface**: `pipeline.process(idea, mode)`
- **Extensible**: Easy to add new pipeline modes
- **No redundancy**: Reuses existing contexts and configs
- **Clean separation**: Pipeline orchestrates, agents execute

### Example Usage

```python
# Simple usage with defaults
pipeline = AnalysisPipeline(config)
result = await pipeline.process("AI fitness app")

# Explicit mode selection
result = await pipeline.process("AI fitness app", mode=PipelineMode.ANALYZE_AND_REVIEW)
```

This removes all parameter passing and makes the pipeline truly config-driven.
