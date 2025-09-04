# Phase 2 Architecture Simplification v3: Balanced Simplification with Clean Inheritance

**Date**: 2025-08-21  
**Author**: Claude Code Session Analysis  
**Status**: PROPOSAL v3 (Final)  
**Objective**: Simplify Phase 2 while maintaining clean inheritance and extensibility

## Executive Summary

Based on your feedback from v2 and the design questions, this v3 proposal presents a **balanced simplification** that:

1. **Keeps inheritance patterns** for both configs and contexts (for extensibility)
2. **Removes unnecessary abstractions** (PipelineConfig, RevisionContext, _override suffix)
3. **Uses explicit typed fields** instead of flexible dictionaries
4. **Separates SystemConfig from AgentConfigs** for clarity
5. **Simplifies without breaking the architecture** (~25-30% code reduction)

Key principle: **Code clarity is top priority**, followed by easy agent addition and flexibility.

## Proposed Architecture

### 1. Config Structure: Flat with Composition

#### SystemConfig (System-wide settings only)

```python
@dataclass
class SystemConfig:
    """System-wide configuration for paths, limits, and pipeline settings."""
    
    # === Paths ===
    project_root: Path = field(default_factory=lambda: Path.cwd())
    prompts_dir: Path = field(init=False)
    analyses_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    
    # === Pipeline Settings ===
    default_pipeline_mode: PipelineMode = PipelineMode.ANALYZE_AND_REVIEW
    max_iterations_by_mode: dict[PipelineMode, int] = field(
        default_factory=lambda: {
            PipelineMode.ANALYZE: 1,
            PipelineMode.ANALYZE_AND_REVIEW: 3,
            PipelineMode.ANALYZE_REVIEW_AND_JUDGE: 3,
            PipelineMode.FULL_EVALUATION: 3,
        }
    )
    
    # === System Limits ===
    max_content_size: int = 10_000_000  # 10MB
    max_file_read_retries: int = 3
    file_retry_delay: float = 1.0
    
    # === Global Defaults ===
    max_idea_length: int = 500
    slug_max_length: int = 50
    preview_lines: int = 20
    
    def __post_init__(self) -> None:
        """Initialize derived paths."""
        self.prompts_dir = self.project_root / "config" / "prompts"
        self.analyses_dir = self.project_root / "analyses"
        self.logs_dir = self.project_root / "logs"
```

#### BaseAgentConfig (Common agent settings)

<!-- FEEDBACK: we should do away with this notion of default vs override. allowed_tools instead of default_tools. though it makes sense to have default_system_prompt given it will be access through get the get method and possibly modified. maybe we need a get_allowed_tools method for this to work? -->
```python
@dataclass
class BaseAgentConfig:
    """Base configuration shared by all agents."""
    
    # === Common Settings ===
    max_turns: int = 30
    message_log_interval: int = 3
    default_tools: list[str] = field(default_factory=list)
    default_system_prompt: str = "system.md"  # Relative to agent's prompt dir
    
    # === Paths (set by factory or init) ===
    prompts_dir: Path | None = None
    
    def get_system_prompt_path(self, prompt_name: str | None = None) -> Path:
        """Get full path to a prompt file."""
        if not self.prompts_dir:
            raise ValueError("prompts_dir not set")
        
        prompt = prompt_name or self.default_system_prompt
        agent_type = self.__class__.__name__.replace("Config", "").lower()
        
        # Simple resolution: always relative to agent's prompt directory
        return self.prompts_dir / "agents" / agent_type / prompt
```

#### Agent-Specific Configs (Inherit from base)

```python
@dataclass
class AnalystConfig(BaseAgentConfig):
    """Configuration specific to the Analyst agent."""
    
    # === Analyst-Specific Settings ===
    max_websearches: int = 5
    min_analysis_words: int = 900
    max_analysis_words: int = 1200
    default_tools: list[str] = field(default_factory=lambda: ["WebSearch"])
    
<!-- FEEDBACK: remove this section altogether. it's dependent on the system prompt and may change. -->
    # === Section Word Limits ===
    section_word_limits: dict[str, int] = field(
        default_factory=lambda: {
            "executive_summary": 150,
            "market_opportunity": 250,
            "competition_analysis": 200,
            "business_model": 200,
            "risks_challenges": 200,
            "next_steps": 100,
        }
    )

@dataclass
class ReviewerConfig(BaseAgentConfig):
    """Configuration specific to the Reviewer agent."""
    
    # === Reviewer-Specific Settings ===
<!-- FEEDBACK: this is a good idea to have a min and max and put it at the reviewerConfig level like this. kudos -->
    max_review_iterations: int = 3
    min_review_iterations: int = 1
    default_strictness: str = "normal"  # "lenient", "normal", "strict"
<!-- FEEDBACK: no need to override anymore. remove -->
    max_turns: int = 15  # Override base default

<!-- FEEDBACK: let's not worry about Judge and Synthesizer config until we're in phase 3 and 4. remove. -->
@dataclass
class JudgeConfig(BaseAgentConfig):
    """Configuration for the Judge agent (Phase 3)."""
    
    # === Judge-Specific Settings ===
    max_turns: int = 5
    default_criteria_weights: dict[str, float] = field(
        default_factory=lambda: {
            "market_potential": 1.0,
            "competitive_landscape": 1.0,
            "technical_feasibility": 1.0,
            "capital_requirements": 1.0,
            "regulatory_risks": 1.0,
            "execution_difficulty": 1.0,
            "evidence_quality": 1.0,
        }
    )

@dataclass
class SynthesizerConfig(BaseAgentConfig):
    """Configuration for the Synthesizer agent (Phase 4)."""
    
    # === Synthesizer-Specific Settings ===
    max_ideas_to_compare: int = 20
    top_n_recommendations: int = 3
    min_evaluations_required: int = 2
```

### 2. Context Structure: Minimal Base with Extensions

#### BaseContext (Common runtime state)

```python
@dataclass
class BaseContext:
    """Base runtime context shared by all agents."""
    
    # === Required Fields ===
<!-- FEEDBACK: wondering if we need this given that child contexts have input and output paths -->
    output_dir: Path
    
    # === Common Optional Fields ===
    iteration: int = 1
    idea_slug: str | None = None
    
    # === Analytics ===
    run_analytics: Any | None = None  # RunAnalytics instance
    
    # Note: No overrides! Config is updated directly if needed
```

#### Agent-Specific Contexts (Clear extensions)

```python
@dataclass
class AnalystContext(BaseContext):
    """Runtime context for the Analyst agent."""
    
    # === Output Path ===
    analysis_output_path: Path
    
    # === Input Path (for revisions) ===
    feedback_input_path: Path | None = None  # Set on iteration 2+
    
    # === Analyst-Specific State ===
<!-- FEEDBACK: this is tracked by run_analytics. I think -->
    websearch_count: int = 0  # Track searches used

@dataclass
class ReviewerContext(BaseContext):
    """Runtime context for the Reviewer agent."""
    
    # === Input/Output Paths ===
    analysis_input_path: Path
    feedback_output_path: Path
    
    # Note: strictness moved to config, not context

<!-- FEEDBACK: remove anything judges and synthesizers from this document. -->
@dataclass
class JudgeContext(BaseContext):
    """Runtime context for the Judge agent (Phase 3)."""
    
    # === Input Paths ===
    analysis_input_path: Path
    feedback_input_path: Path
    
    # === Output Path ===
    evaluation_output_path: Path

@dataclass
class SynthesizerContext(BaseContext):
    """Runtime context for the Synthesizer agent (Phase 4)."""
    
    # === Input Paths ===
    evaluation_input_paths: list[Path]
    
    # === Output Path ===
    report_output_path: Path
    
    # === State ===
    ideas_processed: list[str] = field(default_factory=list)
```

### 3. Simplified BaseAgent (Optional: Keep or Remove Generics)

Since you don't mind generics, we can keep them for type safety, but simplify:

```python
from typing import TypeVar, Generic

TConfig = TypeVar("TConfig", bound=BaseAgentConfig)
TContext = TypeVar("TContext", bound=BaseContext)

class BaseAgent(ABC, Generic[TConfig, TContext]):
    """
    Base class for all agents in the system.
    
    Simplified: No complex prompt resolution, no override logic.
    """
    
    def __init__(self, config: TConfig):
        """Initialize the agent with its configuration."""
        self.config = config
        self.interrupt_event = threading.Event()
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent."""
        pass
    
    @abstractmethod
    async def process(
        self, 
        input_data: str,
        context: TContext
    ) -> AgentResult:
        """
        Process input and return standardized result.
        
        Args:
            input_data: The input to process
            context: Runtime context with paths and state
            
        Returns:
            AgentResult containing the processing outcome
        """
        pass
    
    def get_system_prompt_path(self) -> Path:
        """
        Get system prompt path from config.
        
        Simplified: No complex resolution, just use config's method.
        """
        return self.config.get_prompt_path()
    
    def load_system_prompt(self) -> str:
        """Load the complete system prompt with includes."""
        from ..utils.file_operations import load_prompt_with_includes
        
        prompt_path = self.get_system_prompt_path()
        return load_prompt_with_includes(
            str(prompt_path.relative_to(self.config.prompts_dir)),
            self.config.prompts_dir
        )
    
    def get_allowed_tools(self) -> list[str]:
        """Get tools from config (no overrides)."""
        return self.config.default_tools
```

### 4. Concrete Agent Example

```python
class AnalystAgent(BaseAgent[AnalystConfig, AnalystContext]):
    """Agent responsible for analyzing business ideas."""
    
    @property
    def agent_name(self) -> str:
        return "analyst"
    
    async def process(
        self,
        input_data: str,  # The business idea
        context: AnalystContext
    ) -> AgentResult:
        """Analyze a business idea."""
        
        # Get configuration values
        max_turns = self.config.max_turns
        max_websearches = self.config.max_websearches
        tools = self.get_allowed_tools()
        
        # Check for revision scenario
        if context.feedback_input_path and context.iteration > 1:
            # Load previous feedback for revision
            feedback = self._load_feedback(context.feedback_input_path)
            # Adjust prompt for revision...
        
        # Load system prompt
        system_prompt = self.load_system_prompt()
        
        # Run SDK client
        client = ClaudeSDKClient(
            system_prompt=system_prompt,
            tools=tools,
            max_turns=max_turns,
            # ... other options
        )
        
        # Process and save to output path
        result = await client.run(input_data)
        
        # Write to analysis_output_path
        context.analysis_output_path.write_text(result.content)
        
<!-- FEEDBACK: I want us to rethink the shape of AgentResult, in conjunction to PipelineResult. To me it should be more of a Succes, Error pattern. See current pipeline.py to see how this may make things simpler. We don't seem to be using much data from AgentResult and we've created these methods in pipeline.py that return booleans. It feels overlapping in roles. -->
        return AgentResult(
            content=str(context.analysis_output_path),
            metadata={
                "iteration": context.iteration,
                "websearch_count": context.websearch_count,
            },
            success=True
        )
```

### 5. Simplified Pipeline

```python
class AnalysisPipeline:
    """Simplified pipeline with cleaner state management."""
    
    def __init__(
        self,
        idea: str,
        system_config: SystemConfig,
        analyst_config: AnalystConfig | None = None,
        reviewer_config: ReviewerConfig | None = None,
        mode: PipelineMode = PipelineMode.ANALYZE_AND_REVIEW,
    ):
        """
        Initialize pipeline with configs.
        
        Note: No overrides! Configs should be configured before passing in.
        """
        self.idea = idea
        self.slug = create_slug(idea)
        self.system_config = system_config
        self.mode = mode
        
        # Use provided configs or create defaults
        self.analyst_config = analyst_config or AnalystConfig(
            prompts_dir=system_config.prompts_dir
        )
        self.reviewer_config = reviewer_config or ReviewerConfig(
            prompts_dir=system_config.prompts_dir
        )
        
        # Setup directories
        self.output_dir = system_config.analyses_dir / self.slug
        self.iterations_dir = self.output_dir / "iterations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_dir.mkdir(exist_ok=True)
        
<!-- FEEDBACK: got to think if this is better like this or in the reviewer's config like we saw above. it's a mode-dependent parameter, but at the same time it's only relevant when there's a reviewer involved. -->
        # Get max iterations from system config (no PipelineConfig!)
        self.max_iterations = system_config.max_iterations_by_mode[mode]
        
        # Runtime state (simplified)
        self.current_iteration = 0
        self.current_analysis_path: Path | None = None
        self.analytics: Any | None = None
    
    async def process(self) -> PipelineResult:
        """Process the business idea through the pipeline."""
        
        # Initialize analytics
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{self.slug}"
        self.analytics = RunAnalytics(run_id=run_id, output_dir=self.system_config.logs_dir / "runs")
        
        try:
            # Route based on mode (simplified, no dictionary dispatch)
            if self.mode == PipelineMode.ANALYZE:
                return await self._analyze_only()
            elif self.mode == PipelineMode.ANALYZE_AND_REVIEW:
                return await self._analyze_with_review()
            elif self.mode == PipelineMode.ANALYZE_REVIEW_AND_JUDGE:
                return await self._analyze_review_judge()
            else:  # FULL_EVALUATION
                return await self._full_evaluation()
        finally:
            if self.analytics:
                self.analytics.finalize()
    
    async def _run_analyst(self, feedback_path: Path | None = None) -> bool:
        """Run analyst for current iteration."""
        self.current_iteration += 1
        
        # Create context with explicit paths
        analysis_path = self.iterations_dir / f"iteration_{self.current_iteration}.md"
        analysis_path.touch()  # Pre-create file
        
        context = AnalystContext(
            output_dir=self.output_dir,
            iteration=self.current_iteration,
            idea_slug=self.slug,
            analysis_output_path=analysis_path,
            feedback_input_path=feedback_path,  # None on first iteration
            run_analytics=self.analytics,
        )
        
        # Run analyst
        analyst = AnalystAgent(self.analyst_config)
        result = await analyst.process(self.idea, context)
        
        if result.success:
            self.current_analysis_path = analysis_path
            self._update_symlink()
            return True
        return False
    
    async def _run_reviewer(self) -> bool:
        """Run reviewer and return whether to continue iterating."""
        if not self.current_analysis_path:
            raise ValueError("No analysis to review")
        
        # Create context with explicit paths
        feedback_path = self.iterations_dir / f"feedback_{self.current_iteration}.json"
        feedback_path.write_text("{}")  # Pre-create with empty JSON
        
        context = ReviewerContext(
            output_dir=self.output_dir,
            iteration=self.current_iteration,
            analysis_input_path=self.current_analysis_path,
            feedback_output_path=feedback_path,
            run_analytics=self.analytics,
        )
        
        # Run reviewer
        reviewer = ReviewerAgent(self.reviewer_config)
        result = await reviewer.process("", context)  # Reviewer doesn't need input_data
        
        if not result.success:
            return False
        
        # Check feedback recommendation
        feedback = json.loads(feedback_path.read_text())
        return feedback.get("recommendation") != "approve"
    
    def _update_symlink(self) -> None:
        """Update analysis.md symlink to latest iteration."""
        symlink = self.output_dir / "analysis.md"
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        if self.current_analysis_path:
            symlink.symlink_to(
                self.current_analysis_path.relative_to(self.output_dir)
            )
```

### 6. CLI Integration (Simplified)

<!-- FEEDBACK: very nice implementation -->
```python
async def main():
    """Simplified CLI main function."""
    
    # Parse arguments
    args = parse_arguments()
    idea = args.idea
    
    # Create system config
    system_config = SystemConfig()
    
    # Create agent configs (modify if needed based on CLI args)
    analyst_config = AnalystConfig(prompts_dir=system_config.prompts_dir)
    reviewer_config = ReviewerConfig(prompts_dir=system_config.prompts_dir)
    
    # Modify configs based on CLI arguments (no overrides!)
    if args.no_websearch:
        analyst_config.default_tools = []  # Direct modification
    
    if args.analyst_prompt:
        analyst_config.default_system_prompt = args.analyst_prompt
    
<!-- FEEDBACK: not needed in the cli yet -->
    if args.strict_review:
        reviewer_config.default_strictness = "strict"
    
    # Determine mode
    mode = PipelineMode.ANALYZE_AND_REVIEW if args.with_review else PipelineMode.ANALYZE
    
    # Create and run pipeline
    pipeline = AnalysisPipeline(
        idea=idea,
        system_config=system_config,
        analyst_config=analyst_config,
        reviewer_config=reviewer_config,
        mode=mode,
    )
    
    result = await pipeline.process()
    
    # Display result
    print_result(result)
```

## What Gets Removed

### 1. PipelineConfig Class ✅

- Merged into SystemConfig as `max_iterations_by_mode` dict

### 2. RevisionContext Class ✅

- State tracked directly in agent contexts

### 3. Override Suffix Pattern ✅

- No more `tools_override`, `system_prompt_override`
- Just modify config directly before passing to agents

### 4. Complex Prompt Resolution (Simplified) ✅

- Keep the patterns but simplify the code
- Make it clearer: always relative to agent's prompt dir

### 5. AnalysisConfig Class ✅

- Replaced by SystemConfig (clearer name, flatter structure)

## Migration Strategy

Since backwards compatibility is not important (clean break preferred):

1. **Archive Current Code**

   ```bash
   mv src/core/config.py archive/config_old.py
   mv src/core/pipeline.py archive/pipeline_old.py
   ```

2. **Implement New Structure**
   - Create new config.py with SystemConfig and agent configs
   - Create new contexts.py with all context classes
   - Update agent_base.py with simplified BaseAgent
   - Update pipeline.py with simplified Pipeline

3. **Update Agents**
   - Modify AnalystAgent to use new context structure
   - Modify ReviewerAgent to use new context structure

4. **Update CLI**
   - Remove override handling
   - Directly modify configs

5. **Test Everything**
   - Create new test suite for new structure
   - Don't worry about old analyses

## Benefits of This Approach

### Achieved Goals

1. ✅ **Code Clarity** (top priority): Clear inheritance, explicit fields
2. ✅ **Easy Agent Addition**: Just extend BaseAgentConfig and BaseContext
3. ✅ **Flexibility**: Can still handle unexpected requirements
4. ✅ **Maintains Structure**: Keeps inheritance for extensibility
5. ✅ **Reduces Complexity**: ~25-30% less code, clearer patterns

### Specific Improvements

- **No Override Confusion**: Config is config, context is runtime state
- **Clear Paths**: Explicit typed fields for all file I/O
- **Simpler Pipeline**: No redundant state, cleaner methods
- **Better Separation**: SystemConfig vs AgentConfigs
- **Type Safety**: Optional generics maintained if desired

### Code Reduction Estimates

| Component | Current | Proposed | Reduction |
|-----------|---------|----------|-----------|
| Config Classes | ~287 lines | ~200 lines | 30% |
| Context Classes | ~100 lines | ~80 lines | 20% |
| BaseAgent | ~188 lines | ~120 lines | 36% |
| Pipeline | ~297 lines | ~200 lines | 33% |
| **Total** | **~872 lines** | **~600 lines** | **31%** |

## Implementation Timeline

### Day 1: Core Changes (3 hours)

1. Create new config.py with all config classes (45 min)
2. Create new contexts.py with all context classes (45 min)
3. Update BaseAgent with simplified logic (30 min)
4. Update Pipeline with new structure (1 hour)

### Day 2: Agent Updates (2 hours)

1. Update AnalystAgent (1 hour)
2. Update ReviewerAgent (1 hour)

### Day 3: Integration & Testing (2 hours)

1. Update CLI (30 min)
2. Create basic tests (1 hour)
3. Manual testing (30 min)

**Total: ~7 hours of focused work**

## Summary

This v3 proposal delivers on your key requirements:

- **Maintains inheritance** for configs and contexts
- **Separates concerns** (SystemConfig vs AgentConfigs)
- **Uses explicit typed fields** for clarity
- **Removes unnecessary complexity** while keeping useful patterns
- **Prioritizes code clarity** above all else

The result is a cleaner, more maintainable codebase that's easier to understand and extend, while still providing the flexibility needed for Phase 3/4 agents.

---

*This v3 proposal incorporates all feedback from the design questions document.*
