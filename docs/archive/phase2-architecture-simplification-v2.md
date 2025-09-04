# Phase 2 Architecture Simplification v2: Moderate Simplification with Extensibility

**Date**: 2025-08-21  
**Author**: Claude Code Session Analysis  
**Status**: PROPOSAL v2  
**Objective**: Simplify Phase 2 implementation while maintaining extensibility for future agents

## Executive Summary

After deeper analysis of the codebase and considering the need for extensibility (Judge and Synthesizer agents in Phase 3/4), this v2 proposal focuses on **Option 2: Moderate Simplification**. This approach maintains separation of concerns while reducing complexity by ~30% through:

1. Merging AnalysisConfig and PipelineConfig into a single SystemConfig
2. Creating a unified RuntimeContext for all agents
3. Removing generics from BaseAgent while keeping the inheritance structure
4. Simplifying prompt resolution and override patterns

This approach provides a cleaner architecture that's easier to understand while preserving the flexibility needed for future agent types.

## Deep Dive: Current State Analysis

### Configuration Usage Patterns

After analyzing the codebase, here's how configurations are actually used:

#### AnalysisConfig (config.py:62-116)

- **Purpose**: Container for all system-wide settings
- **Contains**: Paths, limits, and nested agent configs
- **Used by**: Pipeline constructor, never modified after creation
- **Nested configs**: analyst, reviewer (future: judge, synthesizer)

#### PipelineConfig (config.py:43-54)

- **Purpose**: Just holds max_iterations_by_mode dictionary
- **Used by**: Only within AnalysisConfig
- **Observation**: Over-abstracted for a single dictionary

#### Agent Configs (AnalystConfig, ReviewerConfig)

- **Purpose**: Agent-specific defaults and limits
- **Fields actually used**:
  - Both agents: `prompts_dir`, `max_turns`, `message_log_interval`
  - Analyst: `max_websearches`, `min_analysis_words`, `section_word_limits`
  - Reviewer: `max_review_iterations`, `default_strictness`

#### Context Classes

- **AnalystContext fields used**: `idea_slug`, `output_dir`, `iteration`, `system_prompt_override`, `tools_override`, `run_analytics`
- **ReviewerContext fields used**: `analysis_path`, `output_dir`, `system_prompt_override`, `run_analytics`
- **Observation**: Significant overlap, artificial separation

### Key Findings

1. **Config/Context Boundary is Artificial**: The distinction between "immutable config" and "mutable context" doesn't provide value in practice
2. **Override Pattern is Confusing**: The `_override` suffix convention is unclear (None means "use default" not "no value")
3. **Generics Add No Value**: With only 2 agents (4 planned), generics create more complexity than they solve
4. **PipelineConfig is Unnecessary**: It's just a wrapper around one dictionary

## Proposed Architecture: Option 2 Detailed

### 1. Merged SystemConfig

Combine AnalysisConfig and PipelineConfig into a single, flatter structure:

<!-- FEEDBACK: This is good, but I think we should separate into two config types: SystemConfig, and AgentConfig. The current agent defaults crammed into SystemConfig isn't scalable. -->
```python
@dataclass
class SystemConfig:
    """Unified system configuration for the entire analysis pipeline."""
    
    # === System Paths ===
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
    
    # === System Limits (true constants) ===
    max_content_size: int = 10_000_000
    max_file_read_retries: int = 3
    file_retry_delay: float = 1.0
    
    # === Configurable Defaults ===
    max_idea_length: int = 500
    slug_max_length: int = 50
    preview_lines: int = 20
    
    # === Agent Defaults (flat, no nesting) ===
    # Analyst defaults
    analyst_max_turns: int = 30
    analyst_max_websearches: int = 5
    analyst_min_words: int = 900
    analyst_max_words: int = 1200
    analyst_default_tools: list[str] = field(default_factory=lambda: ["WebSearch"])
    
    # Reviewer defaults
    reviewer_max_turns: int = 10
    reviewer_max_iterations: int = 3
    reviewer_default_strictness: str = "normal"
    
    # Judge defaults (Phase 3)
    judge_max_turns: int = 5
    judge_criteria_weights: dict[str, float] = field(default_factory=dict)
    
    # Synthesizer defaults (Phase 4)
    synthesizer_max_ideas: int = 20
    synthesizer_top_n: int = 3
    
    def __post_init__(self) -> None:
        """Initialize derived paths."""
        self.prompts_dir = self.project_root / "config" / "prompts"
        self.analyses_dir = self.project_root / "analyses"
        self.logs_dir = self.project_root / "logs"
```

**Benefits**:

- Single source of truth for all configuration
- Flat structure is easier to understand
- No nested configs to traverse
- Clear naming convention (agent_setting)
- Easy to extend for new agents

### 2. Unified RuntimeContext

<!-- FEEDBACK: After reading all of this, I'm not sure we should have a single context class as again it doesn't scale. maybe just separate config and context .py files and keep the inheritance logic? -->
A single context class that works for all agents:

```python
@dataclass
class RuntimeContext:
    """
    Unified runtime context for all agents.
    
    This replaces all agent-specific context classes with a single,
    flexible structure that can handle any agent's needs.
    """
    
    # === Required Fields ===
    agent_type: str  # "analyst", "reviewer", "judge", "synthesizer"
    output_dir: Path
    
    # === Common Optional Fields ===
    iteration: int = 1
    idea_slug: str | None = None
    
    # === Tool & Prompt Overrides ===
    tools: list[str] | None = None  # None = use agent's defaults
    system_prompt: str | None = None  # None = use agent's default
    
<!-- FEEDBACK: How this input/output paths would work in practice isn't super clear. I also actually prefer a inheritance system like we have now, maybe just simplified. -->
    # === Input/Output Paths ===
    input_paths: dict[str, Path] = field(default_factory=dict)
    """
    Flexible input paths for different agents:
    - Analyst: {} (no input files)
    - Reviewer: {"analysis": Path("analysis.md")}
    - Judge: {"analysis": Path("analysis.md"), "feedback": Path("feedback.json")}
    - Synthesizer: {"evaluations": [Path("eval1.json"), ...]}
    """
    
    output_paths: dict[str, Path] = field(default_factory=dict)
    """
    Expected output paths:
    - Analyst: {"analysis": Path("iteration_1.md")}
    - Reviewer: {"feedback": Path("feedback_1.json")}
    - Judge: {"evaluation": Path("evaluation.json")}
    - Synthesizer: {"report": Path("summary.md")}
    """
    
<!-- FEEDBACK: I think this should go into an agent-specific config, perhaps inheriting from a base agent config -->
    # === Agent-Specific Settings ===
    settings: dict[str, Any] = field(default_factory=dict)
    """
    Flexible settings for agent-specific needs:
    - Reviewer: {"strictness": "strict"}
    - Judge: {"criteria_weights": {...}}
    - Synthesizer: {"top_n": 5}
    """
    
    # === Analytics & Monitoring ===
    run_analytics: Any | None = None  # RunAnalytics instance
    
    # === Helper Methods ===
    def get_input_path(self, key: str) -> Path | None:
        """Get an input path by key."""
        return self.input_paths.get(key)
    
    def get_output_path(self, key: str) -> Path | None:
        """Get an output path by key."""
        return self.output_paths.get(key)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an agent-specific setting."""
        return self.settings.get(key, default)
```

**Benefits**:

- Single context class for all agents
- Flexible input/output path handling
- Extensible settings dictionary for agent-specific needs
- Clear, self-documenting structure
- No need for separate context classes per agent

<!-- FEEDBACK: no strong opinions here. let's see a v3 first. -->
### 3. Simplified BaseAgent (No Generics)

Remove generics while maintaining clean inheritance:

```python
class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    
    Simplified without generics but maintaining extensibility.
    """
    
    def __init__(self, config: SystemConfig):
        """
        Initialize the agent with system configuration.
        
        Args:
            config: System-wide configuration
        """
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
        context: RuntimeContext
    ) -> AgentResult:
        """
        Process input and return standardized result.
        
        Args:
            input_data: The input to process
            context: Runtime context with paths, settings, and overrides
            
        Returns:
            AgentResult containing the processing outcome
        """
        pass
    
    # === Configuration Helpers ===
    
    def get_max_turns(self) -> int:
        """Get max turns for this agent from config."""
        return getattr(self.config, f"{self.agent_name.lower()}_max_turns", 30)
    
    def get_default_tools(self) -> list[str]:
        """Get default tools for this agent from config."""
        return getattr(
            self.config, 
            f"{self.agent_name.lower()}_default_tools", 
            []
        )
    
    def get_allowed_tools(self, context: RuntimeContext) -> list[str]:
        """Get tools for this run (context overrides or defaults)."""
        if context.tools is not None:
            return context.tools
        return self.get_default_tools()
    
    # === Prompt Management (Simplified) ===
    
    def get_system_prompt_path(self, context: RuntimeContext) -> Path:
        """
        Get system prompt path (simplified logic).
        
        Priority:
        1. Context override (if provided)
        2. Default agent prompt
        """
        if context.system_prompt:
            # Assume it's a path relative to prompts_dir
            return self.config.prompts_dir / context.system_prompt
        
        # Default: agents/{agent_name}/system.md
        return self.config.prompts_dir / "agents" / self.agent_name.lower() / "system.md"
    
    def load_system_prompt(self, context: RuntimeContext) -> str:
        """Load the complete system prompt with includes."""
        from ..utils.file_operations import load_prompt_with_includes
        
        prompt_path = self.get_system_prompt_path(context)
        return load_prompt_with_includes(
            str(prompt_path.relative_to(self.config.prompts_dir)),
            self.config.prompts_dir
        )
```

**Benefits**:

- No complex generic type parameters
- Simple, clear method signatures
- Dynamic config access using agent name
- Easier to understand and extend

### 4. Updated Agent Implementations

Example of how concrete agents would look:

```python
class AnalystAgent(BaseAgent):
    """Agent responsible for analyzing business ideas."""
    
    @property
    def agent_name(self) -> str:
        return "analyst"
    
    async def process(
        self,
        input_data: str,
        context: RuntimeContext
    ) -> AgentResult:
        """Analyze a business idea."""
        
        # Validate context
        if context.agent_type != "analyst":
            raise ValueError(f"Wrong context type: {context.agent_type}")
        
        # Get configuration values
        max_turns = self.get_max_turns()
        max_websearches = self.config.analyst_max_websearches
        tools = self.get_allowed_tools(context)
        
        # Get output path
        analysis_path = context.get_output_path("analysis")
        if not analysis_path:
            raise ValueError("No analysis output path in context")
        
        # Load prompts
        system_prompt = self.load_system_prompt(context)
        
        # Run SDK client...
        # (implementation details)
        
        return AgentResult(
            content=str(analysis_path),
            metadata={"iteration": context.iteration},
            success=True
        )


class JudgeAgent(BaseAgent):
    """Agent responsible for grading analyses (Phase 3)."""
    
    @property
    def agent_name(self) -> str:
        return "judge"
    
    async def process(
        self,
        input_data: str,
        context: RuntimeContext
    ) -> AgentResult:
        """Grade a business analysis."""
        
        # Get input paths
        analysis_path = context.get_input_path("analysis")
        if not analysis_path:
            raise ValueError("No analysis path in context")
        
        # Get criteria weights from context or config
        weights = context.get_setting(
            "criteria_weights",
            self.config.judge_criteria_weights
        )
        
        # Get output path
        evaluation_path = context.get_output_path("evaluation")
        
        # Grade the analysis...
        # (implementation details)
        
        return AgentResult(
            content=str(evaluation_path),
            metadata={"grades": {...}},
            success=True
        )
```

### 5. Simplified Pipeline Integration

How the pipeline would create and use contexts:

```python
class AnalysisPipeline:
    """Simplified pipeline with unified context creation."""
    
    def __init__(
        self,
        idea: str,
        config: SystemConfig,
        mode: PipelineMode = PipelineMode.ANALYZE_AND_REVIEW,
        **overrides  # Prompt overrides, tool overrides, etc.
    ):
        self.idea = idea
        self.slug = create_slug(idea)
        self.config = config
        self.mode = mode
        self.overrides = overrides
        
        # Setup directories
        self.output_dir = Path("analyses") / self.slug
        self.iterations_dir = self.output_dir / "iterations"
        
    async def _run_analyst(self, iteration: int) -> AgentResult:
        """Run analyst with unified context."""
        
        # Create context for analyst
        context = RuntimeContext(
            agent_type="analyst",
            output_dir=self.output_dir,
            iteration=iteration,
            idea_slug=self.slug,
            tools=self.overrides.get("analyst_tools"),
            system_prompt=self.overrides.get("analyst_prompt"),
            output_paths={
                "analysis": self.iterations_dir / f"iteration_{iteration}.md"
            }
        )
        
        # Inject analytics if available
        if hasattr(self, "analytics"):
            context.run_analytics = self.analytics
        
        # Run agent
        analyst = AnalystAgent(self.config)
        return await analyst.process(self.idea, context)
    
    async def _run_reviewer(self, iteration: int, analysis_path: Path) -> AgentResult:
        """Run reviewer with unified context."""
        
        context = RuntimeContext(
            agent_type="reviewer",
            output_dir=self.output_dir,
            iteration=iteration,
            system_prompt=self.overrides.get("reviewer_prompt"),
            input_paths={"analysis": analysis_path},
            output_paths={
                "feedback": self.iterations_dir / f"feedback_{iteration}.json"
            },
            settings={"strictness": self.overrides.get("reviewer_strictness", "normal")}
        )
        
        if hasattr(self, "analytics"):
            context.run_analytics = self.analytics
        
        reviewer = ReviewerAgent(self.config)
        return await reviewer.process("", context)  # Reviewer doesn't need input_data
    
    async def _run_judge(self, analysis_path: Path, feedback_path: Path) -> AgentResult:
        """Run judge with unified context (Phase 3)."""
        
        context = RuntimeContext(
            agent_type="judge",
            output_dir=self.output_dir,
            input_paths={
                "analysis": analysis_path,
                "feedback": feedback_path
            },
            output_paths={
                "evaluation": self.output_dir / "evaluation.json"
            }
        )
        
        judge = JudgeAgent(self.config)
        return await judge.process("", context)
```

## Migration Path

### Phase 1: Core Changes (3 hours)

1. **Create SystemConfig** (30 min)
   - Merge AnalysisConfig and PipelineConfig
   - Flatten agent settings
   - Update config.py

2. **Create RuntimeContext** (30 min)
   - Single unified context class
   - Flexible path and settings handling
   - Replace all context classes

3. **Update BaseAgent** (30 min)
   - Remove generics
   - Update method signatures
   - Simplify prompt loading

4. **Update Existing Agents** (1 hour)
   - Modify AnalystAgent to use new structure
   - Modify ReviewerAgent to use new structure
   - Update process() methods

5. **Update Pipeline** (30 min)
   - Use SystemConfig instead of AnalysisConfig
   - Create RuntimeContext instances
   - Remove context class imports

6. **Update CLI** (30 min)
   - Use SystemConfig
   - Pass overrides as dictionary
   - Simplify config creation

### Phase 2: Testing & Validation (2 hours)

1. **Update Unit Tests** (1 hour)
   - Fix config/context creation
   - Update mocks
   - Verify all tests pass

2. **Integration Testing** (1 hour)
   - Run full pipeline tests
   - Test with various overrides
   - Verify backwards compatibility

### Phase 3: Cleanup (1 hour)

1. **Remove Old Code** (30 min)
   - Delete old config classes
   - Delete old context classes
   - Clean up imports

2. **Documentation** (30 min)
   - Update docstrings
   - Create migration guide
   - Update README

## Blind Spots and Considerations

### Identified Blind Spots

1. **Prompt Include System**
   - Current: Complex include directive processing
   - Risk: May need refactoring if prompt paths change
   - Mitigation: Keep include system but simplify paths

2. **RunAnalytics Integration**
   - Current: Injected into context after creation
   - Risk: Type safety issues with Any type
   - Mitigation: Consider making it a required context field

3. **File Creation Logic**
   - Current: Pipeline pre-creates files for agents
   - Risk: Agents might expect different file handling
   - Mitigation: Document file creation responsibility clearly

4. **RevisionContext**
   - Current: Separate class for tracking iterations
   - Risk: Lost functionality when merged
   - Mitigation: Use context.settings for iteration history

### Edge Cases to Test

1. **Empty Overrides**: Ensure None vs empty list/string handled correctly
2. **Path Resolution**: Test relative vs absolute prompt paths
3. **Missing Config Fields**: Graceful fallbacks for new agents
4. **Concurrent Runs**: Ensure contexts don't interfere
5. **Backwards Compatibility**: Old analyses should still work

### Future Extensibility Validation

#### Judge Agent (Phase 3)

```python
# Config: Already has judge_ prefixed settings in SystemConfig
# Context: Uses input_paths for analysis, output_paths for evaluation
# Integration: Simple addition to pipeline, no structural changes needed
```

#### Synthesizer Agent (Phase 4)

```python
# Config: Already has synthesizer_ settings in SystemConfig
# Context: Uses input_paths["evaluations"] for multiple files
# Integration: Can handle lists in input_paths, flexible enough
```

#### Custom Future Agent

```python
# Config: Add new_{agent}_setting to SystemConfig
# Context: Use settings dict for any special needs
# Integration: Inherit from BaseAgent, implement process()
```

## Comparison with Current Architecture

### Complexity Reduction

| Component | Current Lines | Proposed Lines | Reduction |
|-----------|--------------|----------------|-----------|
| Config Classes | ~280 | ~120 | 57% |
| Context Classes | ~100 | ~50 | 50% |
| BaseAgent | ~190 | ~100 | 47% |
| Pipeline Context Creation | ~40 | ~25 | 37% |
| **Total** | **~610** | **~295** | **52%** |

### Cognitive Load Reduction

| Aspect | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Classes to Understand | 9 | 4 | 55% fewer |
| Config Nesting Levels | 3 | 1 | 66% flatter |
| Generic Type Parameters | 2 | 0 | 100% simpler |
| Override Patterns | 3 | 1 | 66% fewer |

## Benefits of This Approach

### Immediate Benefits

1. **Simpler Mental Model**: One config, one context, clear inheritance
2. **Easier Debugging**: Fewer places to look for settings
3. **Better IDE Support**: No generics means better autocomplete
4. **Clearer Data Flow**: Context explicitly shows inputs/outputs

### Long-term Benefits

1. **Easy Agent Addition**: Just extend BaseAgent, add config fields
2. **Flexible Evolution**: Settings dict allows experimentation
3. **Maintainable**: Clear separation between config and runtime
4. **Testable**: Simpler structures are easier to mock

## Risks and Mitigation

### Risk 1: Breaking Existing Functionality

- **Mitigation**: Comprehensive test suite before changes
- **Mitigation**: Keep old code in archive/ during transition

### Risk 2: Losing Type Safety

- **Mitigation**: Use TypedDict for settings where appropriate
- **Mitigation**: Add runtime validation in agents

### Risk 3: Future Requirements Don't Fit

- **Mitigation**: Settings dict provides escape hatch
- **Mitigation**: Can add fields to RuntimeContext as needed

## Conclusion

This Option 2 approach provides the best balance between simplification and extensibility:

- **30-50% code reduction** while maintaining structure
- **Clear extension path** for Judge and Synthesizer
- **Simpler mental model** without sacrificing flexibility
- **Pragmatic design** that solves real problems

The unified RuntimeContext and simplified BaseAgent make the system significantly easier to understand while the flat SystemConfig makes configuration management straightforward. Most importantly, this design naturally accommodates the Phase 3/4 agents without requiring architectural changes.

## Next Steps

1. **Review and Approve**: Discuss any concerns with this approach
2. **Create Test Harness**: Ensure we can validate changes
3. **Implement Phase 1**: Core changes (3 hours)
4. **Test Thoroughly**: Validate all functionality preserved
5. **Document Changes**: Update all documentation

---

*This v2 proposal is based on deep analysis of the current codebase and future requirements as of 2025-08-21.*
