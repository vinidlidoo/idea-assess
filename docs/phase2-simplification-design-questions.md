# Phase 2 Simplification: Design Questions for v3

**Date**: 2025-08-21  
**Purpose**: Align on key architectural decisions before creating v3 proposal  
**Status**: AWAITING FEEDBACK

## Question 1: Config Inheritance Structure

Should we maintain an inheritance hierarchy for configs to support extensibility?

<!-- FEEDBACK: Option B pls -->

### Option A: Nested Hierarchy

```python
SystemConfig (paths, limits, pipeline settings)
└── BaseAgentConfig (common: max_turns, prompts_dir)
    ├── AnalystConfig (max_websearches, min_words)
    ├── ReviewerConfig (max_iterations, strictness)  
    ├── JudgeConfig (criteria_weights)
    └── SynthesizerConfig (top_n, max_ideas)
```

### Option B: Flat with Composition

```python
SystemConfig (paths, limits, pipeline settings)

AnalystConfig(BaseAgentConfig)  # Separate classes
ReviewerConfig(BaseAgentConfig)  # Passed to agents directly
```

### Option C: Single Config with Agent Sections

```python
@dataclass
class SystemConfig:
    # System stuff
    paths: PathConfig
    
    # Agent configs as nested objects
    analyst: AnalystConfig
    reviewer: ReviewerConfig
    judge: JudgeConfig | None = None
```

## Question 2: Context Inheritance Pattern

You mentioned preferring inheritance for contexts. How should we structure it?

<!-- FEEDBACK: Option B -->

### Option A: Keep Current Pattern (Simplified)

```python
BaseContext
├── AnalystContext (idea_slug, iteration)
├── ReviewerContext (analysis_path, strictness)
├── JudgeContext (analysis_path, feedback_path)
└── SynthesizerContext (evaluation_paths)
```

### Option B: Minimal Base with Extensions

```python
@dataclass
class BaseContext:
    output_dir: Path
    iteration: int = 1
    tools: list[str] | None = None
    system_prompt: str | None = None
    run_analytics: Any | None = None

@dataclass  
class ReviewerContext(BaseContext):
    analysis_path: Path  # Required for reviewer
    strictness: str = "normal"  # Reviewer-specific
```

### Option C: Two-Level Hierarchy

```python
BaseContext (common fields)
├── InputContext (for agents that read files)
│   ├── ReviewerContext
│   └── JudgeContext
└── OutputContext (for agents that create files)
    └── AnalystContext
```

## Question 3: Input/Output Path Handling

How should agents specify their file inputs and outputs?

<!-- FEEDBACK: Option A -->

### Option A: Explicit Typed Fields

```python
@dataclass
<!-- FEEDBACK: Analyst will have a feedback_input_path on iteration 2+ -->
class AnalystContext(BaseContext):
    analysis_output_path: Path  # Clear, typed
    
@dataclass
class ReviewerContext(BaseContext):
    analysis_input_path: Path   # Clear input
    feedback_output_path: Path  # Clear output
```

### Option B: Standardized Names

```python
@dataclass
class BaseContext:
    input_file: Path | None = None   # Standard name
    output_file: Path | None = None  # Standard name
    
    # Agents know what these mean for them
```

### Option C: Lists for Multiple Files

```python
@dataclass
class BaseContext:
    input_files: list[Path] = field(default_factory=list)
    output_files: list[Path] = field(default_factory=list)
    
    # Judge: input_files = [analysis, feedback]
    # Synthesizer: input_files = [eval1, eval2, ...]
```

## Question 4: What Should We Definitely Remove?

Please confirm which of these we should remove:

<!-- FEEDBACK: Not sure here. I don't mind Generics frankly.  -->
1. **Generics from BaseAgent** (TConfig, TContext)
   - Remove? Yes/No
   - Alternative: Just use union types

<!-- FEEDBACK: YES, remove -->
2. **PipelineConfig wrapper class**
   - Remove? Yes/No  
   - Alternative: Move dict directly into SystemConfig

<!-- FEEDBACK: Keep, but simplify the associated code if at all possible. -->
3. **Complex prompt resolution** (3 patterns: experimental/, full path, relative)
   - Remove? Yes/No
   - Alternative: Single pattern with clear rules

<!-- FEEDBACK: Yes, probably better to separate. -->
4. **RevisionContext as separate class**
   - Remove? Yes/No
   - Alternative: Track revision state in BaseContext

<!-- FEEDBACK: Yes, remove -->
5. **The `_override` suffix pattern**
   - Remove? Yes/No
   - Alternative: See Question 5

## Question 5: Override Pattern Design

How should we handle config overrides in contexts?

<!-- FEEDBACK: Don't think we truly need overrides. We can you just update the config directly for tools and system_prompts if needed.  -->
### Option A: Current Pattern (Clarified)

```python
# None means "use agent's default"
tools_override: list[str] | None = None
system_prompt_override: str | None = None
```

### Option B: Remove "override" Suffix

```python
# Simpler naming, same behavior
tools: list[str] | None = None  # None = use default
system_prompt: str | None = None
```

### Option C: Explicit Defaults

```python
# Use special value for defaults
tools: list[str] | Literal["default"] = "default"
system_prompt: str | Literal["default"] = "default"
```

### Option D: Separate Override Object

```python
@dataclass
class ContextOverrides:
    tools: list[str] | None = None
    system_prompt: str | None = None
    
class BaseContext:
    overrides: ContextOverrides | None = None
```

## Question 6: Agent-Specific Settings

How should we handle agent-specific configuration that doesn't fit common patterns?

### Option A: Settings Dictionary (Flexible)

```python
class ReviewerContext(BaseContext):
    settings: dict[str, Any] = field(default_factory=dict)
    # settings["strictness"] = "strict"
```

<!-- FEEDBACK: Explicit like this but those examples like strictness are more configs than contexts -->
### Option B: Explicit Fields (Type-Safe)

```python
class ReviewerContext(BaseContext):
    strictness: str = "normal"  # Explicit field
    
class JudgeContext(BaseContext):
    criteria_weights: dict[str, float] = field(default_factory=dict)
```

### Option C: Config Objects

```python
@dataclass
class ReviewerSettings:
    strictness: str = "normal"
    
class ReviewerContext(BaseContext):
    settings: ReviewerSettings = field(default_factory=ReviewerSettings)
```

## Question 7: Scalability Priorities

Rank these in order of importance (1 = most important):

- [5] **Type Safety**: Everything strongly typed, no Any or dicts
- [2] **Easy Agent Addition**: Minimal code to add new agent types  
- [1] **Code Clarity**: Easy to understand without documentation
- [3] **Flexibility**: Can handle unexpected future requirements
- [4] **Minimal Boilerplate**: Less code to write and maintain
- [6] **IDE Support**: Good autocomplete and type checking

## Question 8: Config/Context Relationship

How should configs and contexts relate to each other?

### Option A: Context References Config

```python
class BaseContext:
    config: BaseAgentConfig  # Context has reference to its config
    # Runtime overrides on top
```

<!-- FEEDBACK: option B is best in my opinion -->
### Option B: Separate but Parallel

```python
# Config and context are separate
# Agent gets both in __init__ and process()
agent = AnalystAgent(config)
result = await agent.process(input, context)
```

### Option C: Context Contains Everything

```python
# Context has all config values + runtime state
# Config is just for defaults, context is source of truth
context = AnalystContext.from_config(config)
```

## Question 9: Pipeline Simplification

How much should we simplify the Pipeline class?

### Option A: Minimal Changes

- Just remove PipelineConfig
- Keep current structure mostly intact

<!-- FEEDBACK: the devil is in the details, but leaning towards Option B -->
### Option B: Moderate Refactor  

- Simplify context creation
- Remove redundant state tracking
- Cleaner method signatures

### Option C: Major Refactor

- Pipeline just orchestrates
- Agents handle all their own file I/O
- Pipeline only manages iteration flow

## Question 10: Backwards Compatibility

<!-- FEEDBACK: Not important at all. This is a personal project and not used by anyone else. don't want backwards compatibility -->
How important is backwards compatibility with existing analyses?

### Option A: Full Compatibility

- All old analyses must work unchanged
- May limit how much we can simplify

### Option B: Migration Path

- Provide migration script
- Can make breaking changes

<!-- FEEDBACK: this -->
### Option C: Clean Break

- New structure for new analyses
- Keep old code in archive/ for reference

## Your Preferences Summary

<!-- FEEDBACK: you got the high-level right. let's work on v3 with what you have now! -->
Based on your v2 feedback, I understand you prefer:

1. Keep inheritance for configs and contexts (more flexible/scalable)
2. Separate SystemConfig from AgentConfigs (not all crammed together)
3. Typed fields over flexible dicts (clearer intent)
4. Some simplification but not radical changes

**Please provide your preferences for each question above, and I'll create a v3 proposal that aligns with your vision.**

---

*Ready to create v3 proposal once we align on these decisions.*
