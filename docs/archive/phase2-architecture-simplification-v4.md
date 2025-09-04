# Phase 2 Architecture Simplification v4: Final Refinement

**Date**: 2025-08-21  
**Author**: Claude Code Session Analysis  
**Status**: PROPOSAL v4 (Final Refinement)  
**Objective**: Final simplification incorporating all feedback

## Executive Summary

This v4 proposal is the final refinement based on your v3 feedback. Key changes:

1. **Remove "default" terminology** (except for system_prompt) - use `allowed_tools`
2. **Remove Phase 3/4 elements** - focus only on current needs
3. **Redesign AgentResult** - cleaner Success/Error pattern
4. **Move max_iterations to ReviewerConfig** - it's reviewer-specific
5. **Simplify BaseContext** - remove output_dir if not needed
6. **Remove unnecessary tracking** - websearch_count is in run_analytics

## Core Design Decisions

### Key Insight: AgentResult/PipelineResult Overlap

Looking at the current pipeline.py, the agent methods return booleans and we're not using AgentResult metadata. This suggests we need a simpler pattern:

```python
# Current (overlapping responsibilities):
result = await analyst.process(idea, context)
if not result.success:  # Boolean check
    return self._build_result(error="Analyst failed")  # Another result type

# Proposed (clear separation):
result = await analyst.process(idea, context)
match result:
    case Success():
        # Continue pipeline
    case Error(message):
        return PipelineError(message)
```

## Proposed Architecture v4

### 1. Config Structure: Clean and Focused

#### SystemConfig (System-wide only)

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

#### BaseAgentConfig (No "default" prefix except system_prompt)

```python
@dataclass
class BaseAgentConfig:
    """Base configuration shared by all agents."""
    
    # === Common Settings ===
    max_turns: int = 30
    message_log_interval: int = 5
    allowed_tools: list[str] = field(default_factory=list)  # Not "default_tools"
    system_prompt: str = "system.md"  # Relative to agent's prompt dir
    
    # === Paths (set by factory or init) ===
    prompts_dir: Path | None = None
    
    def get_system_prompt_path(self) -> Path:
        """Get full path to the system prompt file."""
        if not self.prompts_dir:
            raise ValueError("prompts_dir not set")
        
        agent_type = self.__class__.__name__.replace("Config", "").lower()
        
        # Simple resolution: always relative to agent's prompt directory
        return self.prompts_dir / "agents" / agent_type / self.system_prompt
    
    def get_allowed_tools(self) -> list[str]:
        """Get the list of allowed tools for this agent."""
        return self.allowed_tools
```

#### Agent-Specific Configs (Current agents only)

```python
@dataclass
class AnalystConfig(BaseAgentConfig):
    """Configuration specific to the Analyst agent."""
    
    # === Analyst-Specific Settings ===
    max_websearches: int = 5
    min_analysis_words: int = 900
    max_analysis_words: int = 1200
    allowed_tools: list[str] = field(default_factory=lambda: ["WebSearch"])
    
    # Note: Removed section_word_limits - it's prompt-dependent

@dataclass
class ReviewerConfig(BaseAgentConfig):
    """Configuration specific to the Reviewer agent."""
    
    # === Reviewer-Specific Settings ===
    max_iterations: int = 3  # Moved here from SystemConfig!
    min_iterations: int = 1
    strictness: str = "normal"  # "lenient", "normal", "strict"
    
    # Note: No max_turns override needed, inherits from base
```

### 2. Result Types: Clean Success/Error Pattern

```python
from typing import Union

@dataclass
class Success:
    """Successful agent execution."""
    # No data needed - context already has output paths

@dataclass
class Error:
    """Failed agent execution."""
    message: str
    details: dict[str, Any] = field(default_factory=dict)

# Simple type alias
AgentResult = Union[Success, Error]

# For pipeline results, keep the TypedDict but simplified
class PipelineResult(TypedDict):
    """Result from running the analysis pipeline."""
    success: bool
    idea: str
    slug: str
    # Success fields (optional)
    analysis_file: str | None
    iterations_completed: int | None
    # Error fields (optional)
    error: str | None
```

### 3. Context Structure: Minimal and Clear

#### BaseContext (Simplified)

```python
@dataclass
class BaseContext:
    """Base runtime context shared by all agents."""
    
    # === Common Fields ===
    iteration: int = 1
    idea_slug: str | None = None
    
    # === Analytics ===
    run_analytics: Any | None = None  # RunAnalytics instance
    
    # Note: Removed output_dir - child contexts have specific paths
```

#### Agent-Specific Contexts

```python
@dataclass
class AnalystContext(BaseContext):
    """Runtime context for the Analyst agent."""
    
    # === Required Paths ===
    analysis_output_path: Path
    
    # === Optional Input (for revisions) ===
    feedback_input_path: Path | None = None  # Set on iteration 2+
    
    # Note: Removed websearch_count - tracked by run_analytics

@dataclass
class ReviewerContext(BaseContext):
    """Runtime context for the Reviewer agent."""
    
    # === Required Paths ===
    analysis_input_path: Path
    feedback_output_path: Path
    
    # Note: strictness is in config, not context
```

### 4. Simplified BaseAgent

```python
from typing import TypeVar, Generic

TConfig = TypeVar("TConfig", bound=BaseAgentConfig)
TContext = TypeVar("TContext", bound=BaseContext)

class BaseAgent(ABC, Generic[TConfig, TContext]):
    """
    Base class for all agents in the system.
    
    Clean and simple: config in, result out.
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
        Process input and return Success or Error.
        
        Args:
            input_data: The input to process
            context: Runtime context with paths and state
            
        Returns:
            Success() or Error(message)
        """
        pass
    
    def load_system_prompt(self) -> str:
        """Load the complete system prompt with includes."""
        from ..utils.file_operations import load_prompt_with_includes
        
        prompt_path = self.config.get_system_prompt_path()
        return load_prompt_with_includes(
            str(prompt_path.relative_to(self.config.prompts_dir)),
            self.config.prompts_dir
        )
```

### 5. Concrete Agent Example

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
        
        try:
            # Get configuration values
            max_turns = self.config.max_turns
            max_websearches = self.config.max_websearches
            tools = self.config.get_allowed_tools()
            
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
            
            # Process
            result = await client.run(input_data)
            
            # Write to output path
            context.analysis_output_path.write_text(result.content)
            
            # Simple success - no metadata needed
            return Success()
            
        except Exception as e:
            return Error(f"Analyst failed: {str(e)}")
```

### 6. Simplified Pipeline

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
        """Initialize pipeline with configs."""
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
        
        # Runtime state
        self.current_iteration = 0
        self.current_analysis_path: Path | None = None
        self.analytics: Any | None = None
    
    async def process(self) -> PipelineResult:
        """Process the business idea through the pipeline."""
        
        # Initialize analytics
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{self.slug}"
        self.analytics = RunAnalytics(
            run_id=run_id, 
            output_dir=self.system_config.logs_dir / "runs"
        )
        
        try:
            # Simple routing
            if self.mode == PipelineMode.ANALYZE:
                return await self._analyze_only()
            elif self.mode == PipelineMode.ANALYZE_AND_REVIEW:
                return await self._analyze_with_review()
            # Future modes...
            
        finally:
            if self.analytics:
                self.analytics.finalize()
    
    async def _analyze_only(self) -> PipelineResult:
        """Run analyst only."""
        result = await self._run_analyst()
        
        match result:
            case Success():
                return {
                    "success": True,
                    "idea": self.idea,
                    "slug": self.slug,
                    "analysis_file": str(self.current_analysis_path),
                    "iterations_completed": 1,
                    "error": None,
                }
            case Error(message):
                return {
                    "success": False,
                    "idea": self.idea,
                    "slug": self.slug,
                    "analysis_file": None,
                    "iterations_completed": 0,
                    "error": message,
                }
    
    async def _analyze_with_review(self) -> PipelineResult:
        """Run analyst-reviewer feedback loop."""
        
        # Use max_iterations from ReviewerConfig
        max_iterations = self.reviewer_config.max_iterations
        
        while self.current_iteration < max_iterations:
            # Run analyst
            analyst_result = await self._run_analyst()
            match analyst_result:
                case Error(message):
                    return {
                        "success": False,
                        "idea": self.idea,
                        "slug": self.slug,
                        "error": message,
                    }
                case Success():
                    pass  # Continue
            
            # Skip review on last iteration
            if self.current_iteration >= max_iterations:
                break
            
            # Run reviewer
            should_continue = await self._should_continue_after_review()
            if not should_continue:
                break
        
        return {
            "success": True,
            "idea": self.idea,
            "slug": self.slug,
            "analysis_file": str(self.current_analysis_path),
            "iterations_completed": self.current_iteration,
            "error": None,
        }
    
    async def _run_analyst(self, feedback_path: Path | None = None) -> AgentResult:
        """Run analyst for current iteration."""
        self.current_iteration += 1
        
        # Create context with explicit paths
        analysis_path = self.iterations_dir / f"iteration_{self.current_iteration}.md"
        analysis_path.touch()  # Pre-create file
        
        context = AnalystContext(
            iteration=self.current_iteration,
            idea_slug=self.slug,
            analysis_output_path=analysis_path,
            feedback_input_path=feedback_path,
            run_analytics=self.analytics,
        )
        
        # Run analyst
        analyst = AnalystAgent(self.analyst_config)
        result = await analyst.process(self.idea, context)
        
        match result:
            case Success():
                self.current_analysis_path = analysis_path
                self._update_symlink()
            case Error():
                pass  # Error propagated up
        
        return result
    
    async def _should_continue_after_review(self) -> bool:
        """Run reviewer and return whether to continue iterating."""
        if not self.current_analysis_path:
            raise ValueError("No analysis to review")
        
        # Create context
        feedback_path = self.iterations_dir / f"feedback_{self.current_iteration}.json"
        feedback_path.write_text("{}")  # Pre-create
        
        context = ReviewerContext(
            iteration=self.current_iteration,
            analysis_input_path=self.current_analysis_path,
            feedback_output_path=feedback_path,
            run_analytics=self.analytics,
        )
        
        # Run reviewer
        reviewer = ReviewerAgent(self.reviewer_config)
        result = await reviewer.process("", context)
        
        match result:
            case Error():
                return False  # Stop on error
            case Success():
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

### 7. CLI Integration (Clean)

```python
async def main():
    """Simplified CLI main function."""
    
    # Parse arguments
    args = parse_arguments()
    idea = args.idea
    
    # Create system config
    system_config = SystemConfig()
    
    # Create agent configs
    analyst_config = AnalystConfig(prompts_dir=system_config.prompts_dir)
    reviewer_config = ReviewerConfig(prompts_dir=system_config.prompts_dir)
    
    # Modify configs based on CLI arguments
    if args.no_websearch:
        analyst_config.allowed_tools = []  # Direct modification
    
    if args.analyst_prompt:
        analyst_config.system_prompt = args.analyst_prompt  # No "default_"
    
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

## Key Changes from v3

### 1. Naming Improvements

- `default_tools` → `allowed_tools`
- `default_strictness` → `strictness`
- Kept `system_prompt` (not `default_system_prompt` since it's modifiable)

### 2. Removed Phase 3/4 Elements

- No JudgeConfig or SynthesizerConfig
- No JudgeContext or SynthesizerContext
- Focus only on current needs

### 3. Simplified AgentResult

- Simple Success/Error pattern
- No metadata (wasn't being used)
- Clean pattern matching in pipeline

### 4. Moved max_iterations

- From SystemConfig to ReviewerConfig
- It's reviewer-specific functionality
- Pipeline gets it from reviewer config

### 5. Simplified BaseContext

- Removed `output_dir` (child contexts have specific paths)
- Removed `websearch_count` (tracked by run_analytics)

### 6. Removed Unnecessary Elements

- Section word limits (prompt-dependent)
- Strict review CLI flag (not needed yet)
- Max turns override in ReviewerConfig

## What Gets Removed (Summary)

1. ✅ **PipelineConfig** → Merged into SystemConfig
2. ✅ **RevisionContext** → State in agent contexts
3. ✅ **Override suffix pattern** → Direct config modification
4. ✅ **AnalysisConfig** → Renamed to SystemConfig
5. ✅ **"default_" prefix** → Cleaner names (except system_prompt)
6. ✅ **Unused metadata** → Simpler AgentResult
7. ✅ **Future agent configs** → Phase 3/4 elements

## Benefits of v4

### Clean Separation of Concerns

- **Config**: What the agent can do
- **Context**: Where to read/write for this run
- **Result**: Simple success/error

### Improved Clarity

- No "default" confusion
- Clear ownership (max_iterations in ReviewerConfig)
- Explicit typed paths

### Simpler Patterns

- Pattern matching for results
- Direct config modification
- No complex overrides

### Future-Ready

- Easy to add JudgeConfig when needed
- Simple to extend contexts
- Clear patterns to follow

## Implementation Strategy

Since we're doing a clean break:

1. **Archive current code** (30 min)
2. **Create new structures** (2 hours)
   - New config.py with all configs
   - New contexts.py with all contexts
   - New results.py with Success/Error
3. **Update agents** (2 hours)
   - Simplify AnalystAgent
   - Simplify ReviewerAgent
4. **Update pipeline** (1.5 hours)
   - Pattern matching for results
   - Get max_iterations from reviewer config
5. **Update CLI** (30 min)
6. **Test everything** (1 hour)

**Total: ~7 hours**

## Conclusion

This v4 proposal addresses all your feedback:

- Cleaner naming without "default" prefix
- No Phase 3/4 elements
- Simpler Success/Error pattern
- Logical placement of max_iterations
- Minimal, focused contexts
- Clean, understandable code

The result is a system that's easy to understand, extend, and maintain while being ready for Phase 3 when needed.

---

*v4 incorporates all feedback from v3 review.*
