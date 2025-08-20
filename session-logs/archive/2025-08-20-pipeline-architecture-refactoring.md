# Pipeline Architecture Refactoring - Final Design

## Final Design: Mode-Driven Pipeline

```python
# In src/core/types.py
from enum import Enum

class PipelineMode(Enum):
    """Pipeline execution modes using verb-based naming."""
    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # Analyst + Reviewer loop
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # + Judge
    FULL_EVALUATION = "full_evaluation"  # All agents

# In src/core/config.py
@dataclass
class PipelineConfig:
    """Configuration for pipeline execution modes."""
    max_iterations_by_mode: dict[PipelineMode, int] = field(
        default_factory=lambda: {
            PipelineMode.ANALYZE: 1,
            PipelineMode.ANALYZE_AND_REVIEW: 3,
            PipelineMode.ANALYZE_REVIEW_AND_JUDGE: 3,
            PipelineMode.FULL_EVALUATION: 3,
        }
    )

@dataclass
class AnalysisConfig:
    # ... existing fields ...
    default_pipeline_mode: PipelineMode = PipelineMode.ANALYZE_AND_REVIEW
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

# In src/core/pipeline.py
class AnalysisPipeline:
    """Pipeline that processes ideas through various agent configurations."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        # Instance variables for current run (set in process())
        self.idea: str | None = None
        self.slug: str | None = None
        self.output_dir: Path | None = None
        self.run_analytics: RunAnalytics | None = None
        self.mode: PipelineMode | None = None
    
    async def process(
        self, 
        idea: str, 
        mode: PipelineMode | None = None,
        max_iterations_override: int | None = None  # Allow CLI override
    ) -> PipelineResult:
        """
        Process an idea through the pipeline.
        
        Args:
            idea: The business idea to analyze
            mode: Pipeline mode (defaults to config.default_pipeline_mode)
            max_iterations_override: Override max iterations from CLI (optional)
        """
        mode = mode or self.config.default_pipeline_mode
        
        # Store run context as instance variables
        self.idea = idea
        self.slug = create_slug(idea)
        self.output_dir = self.config.analyses_dir / self.slug
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.max_iterations_override = max_iterations_override
        
        self.run_analytics = RunAnalytics(
            run_id=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.slug}",
            output_dir=self.config.logs_dir / "runs"
        )
        
        try:
            # Clean dispatch - no parameters needed
            handlers = {
                PipelineMode.ANALYZE: self._analyze_only,
                PipelineMode.ANALYZE_AND_REVIEW: self._analyze_with_review,
                PipelineMode.ANALYZE_REVIEW_AND_JUDGE: self._analyze_review_judge,
                PipelineMode.FULL_EVALUATION: self._full_evaluation,
            }
            
            handler = handlers.get(mode)
            if not handler:
                raise ValueError(f"Unknown pipeline mode: {mode}")
            
            return await handler()  # No parameters!
        finally:
            self.run_analytics.finalize()
            # Clean up instance variables
            self.idea = None
            self.slug = None
            self.output_dir = None
            self.run_analytics = None
            self.mode = None
            self.max_iterations_override = None
    
    async def _analyze_only(self) -> PipelineResult:
        """Single analyst pass."""
        # Create context using instance variables
        analyst_context = AnalystContext(
            idea_slug=self.slug,
            output_dir=self.output_dir,
            run_analytics=self.run_analytics,
            iteration=1
        )
        
        analyst = AnalystAgent(self.config.analyst)
        result = await analyst.process(self.idea, analyst_context)
        
        if not result.success:
            raise RuntimeError(f"Analyst failed: {result.error}")
        
        # Create symlink to analysis
        analysis_file = Path(result.content)
        symlink = self.output_dir / "analysis.md"
        symlink.unlink(missing_ok=True)
        symlink.symlink_to(analysis_file.relative_to(self.output_dir))
        
        # Build pipeline result
        return {
            "success": True,
            "idea": self.idea,
            "slug": self.slug,
            "file_path": str(symlink),
            "iteration_count": 1,
            "final_status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _analyze_with_review(self) -> PipelineResult:
        """Analyst with reviewer feedback loop."""
        iterations_dir = self.output_dir / "iterations"
        iterations_dir.mkdir(exist_ok=True)
        
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)
        
        # Get max iterations - use override if provided, else use config
        if self.max_iterations_override is not None:
            max_iterations = self.max_iterations_override
        else:
            max_iterations = self.config.pipeline.max_iterations_by_mode[self.mode]
        
        iteration_count = 0
        current_analysis_file = None
        final_status = "accepted"
        
        while iteration_count < max_iterations:
            iteration_count += 1
            
            # Create analyst context
            analyst_context = AnalystContext(
                idea_slug=self.slug,
                output_dir=self.output_dir,
                run_analytics=self.run_analytics,
                iteration=iteration_count
            )
            
            # Add revision context for iterations > 1
            if iteration_count > 1 and current_analysis_file:
                analyst_context.revision_context = RevisionContext(
                    iteration=iteration_count,
                    previous_analysis_path=Path(current_analysis_file),
                    feedback_path=iterations_dir / f"reviewer_feedback_iteration_{iteration_count - 1}.json"
                )
                analyst_context.tools_override = []  # No WebSearch on revisions
            
            # Run analyst
            analyst_result = await analyst.process(self.idea, analyst_context)
            if not analyst_result.success:
                raise RuntimeError(f"Analyst failed at iteration {iteration_count}: {analyst_result.error}")
            
            current_analysis_file = analyst_result.content
            
            # Update symlink
            symlink = self.output_dir / "analysis.md"
            symlink.unlink(missing_ok=True)
            symlink.symlink_to(Path(current_analysis_file).relative_to(self.output_dir))
            
            # Skip reviewer on last iteration (no chance to revise)
            if iteration_count >= max_iterations:
                final_status = "max_iterations_reached"
                break
            
            # Run reviewer
            reviewer_context = ReviewerContext(
                analysis_path=Path(current_analysis_file),
                run_analytics=self.run_analytics
            )
            
            reviewer_result = await reviewer.process(reviewer_context)  # input_data optional, defaults to ""
            if not reviewer_result.success:
                raise RuntimeError(f"Reviewer failed at iteration {iteration_count}: {reviewer_result.error}")
            
            # Check feedback
            feedback_text = Path(reviewer_result.content).read_text()
            feedback = json.loads(feedback_text)
            
            if feedback.get("iteration_recommendation") != "reject":
                logger.info(f"Analysis accepted after {iteration_count} iteration(s)")
                final_status = "accepted"
                break
            
            # Log rejection reason
            logger.info(f"Analysis rejected at iteration {iteration_count}, continuing...")
        
        # Return result
        return {
            "success": True,
            "idea": self.idea,
            "slug": self.slug,
            "file_path": str(self.output_dir / "analysis.md"),
            "iteration_count": iteration_count,
            "final_status": final_status,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _analyze_review_judge(self) -> PipelineResult:
        """Run analysis with review, then judge."""
        # First run the review loop
        result = await self._analyze_with_review()
        
        # Then run judge (Phase 3 - not yet implemented)
        # judge_result = await self._run_judge(result)
        
        return result
    
    async def _full_evaluation(self) -> PipelineResult:
        """Run all agents including synthesizer."""
        # Run through judge
        result = await self._analyze_review_judge()
        
        # Then run synthesizer (Phase 4 - not yet implemented)
        # final_result = await self._run_synthesizer(result)
        
        return result
```

## Key Design Improvements

1. **Clean method dispatch** - Handlers take no parameters, use instance variables instead
   - Store `idea`, `slug`, `output_dir`, `run_analytics` as instance variables
   - Clean up in finally block to avoid state leakage

2. **Dictionary-based routing** - Replace if/elif chain with clean dictionary dispatch

3. **CLI override capability** - Added `max_iterations_override` parameter for CLI flexibility
   - If provided, overrides config value
   - Preserves backward compatibility with CLI

4. **Proper file organization**:
   - `PipelineMode` enum in `types.py`
   - `PipelineConfig` in `config.py`
   - Clean separation of concerns

5. **BaseAgent.process() signature change** - Make `input_data` optional with default `""`
   - Allows ReviewerAgent to be called without passing empty string

6. **Consistent error handling** - All agent failures raise `RuntimeError` with context

---

## Implementation Task List

### Phase 1: Core Refactoring

- [ ] **1. Add PipelineMode enum to types.py**
  - Add enum with verb-based names
  - Export from `__init__.py`

- [ ] **2. Add PipelineConfig to config.py**
  - Create PipelineConfig dataclass
  - Add max_iterations_by_mode dictionary
  - Add to AnalysisConfig with default_pipeline_mode

- [ ] **3. Update BaseAgent interface**
  - Change `process()` signature to make input_data optional: `input_data: str = ""`
  - Update all agent implementations to match

- [ ] **4. Update ReviewerAgent**
  - Update to use optional input_data from BaseAgent
  - Call with `reviewer.process(reviewer_context)` (no empty string needed)
  - Update docstring to clarify input_data not used

- [ ] **5. Refactor AnalysisPipeline**
  - Remove `run_analyst_reviewer_loop` method
  - Add new `process(idea, mode)` method
  - Implement mode-specific handler methods
  - Move output_dir creation to common setup
  - Use PipelineConfig for max_iterations

### Phase 2: CLI Updates

- [ ] **6. Update CLI to use new pipeline interface**
  - Change from `run_analyst_reviewer_loop()` to `process()`
  - Map `--with-review` flag to PipelineMode
  - Remove tools_override parameter passing

- [ ] **7. Clean up CLI parameters**
  - Keep `--max-iterations` for override capability
  - Pass as `max_iterations_override` to pipeline.process()
  - Remove `--tools` option (if not already done)
  - Clean up parameter extraction logic

### Phase 3: Testing & Validation

- [ ] **8. Update unit tests**
  - Fix tests for new pipeline.process() signature
  - Update reviewer tests for new signature
  - Add tests for PipelineMode enum

- [ ] **9. Update integration tests**
  - Test each pipeline mode
  - Verify mode-specific max_iterations work
  - Test error handling for failed agents

- [ ] **10. Run full test suite**
  - `pytest tests/`
  - `test_locally.sh` with all scenarios
  - Manual testing of each mode

### Phase 4: Documentation

- [ ] **11. Update docstrings**
  - Pipeline class and methods
  - Config classes
  - Agent process methods

- [ ] **12. Update README and docs**
  - Document new pipeline modes
  - Update CLI usage examples
  - Document config structure changes

### Phase 5: Cleanup

- [ ] **13. Remove deprecated code**
  - Remove old `run_analyst_reviewer_loop` method
  - Remove unused parameters from pipeline
  - Clean up imports

- [ ] **14. Standardize imports** (as noted earlier)
  - Use module-level imports consistently
  - Update all files to follow same pattern

- [ ] **15. Final review**
  - Run linters (ruff, basedpyright)
  - Check for any remaining `reportAny` warnings
  - Verify all TODOs addressed

## Migration Notes

### Breaking Changes

1. **Pipeline interface change**
   - Old: `pipeline.run_analyst_reviewer_loop(idea, max_iterations, use_websearch)`
   - New: `pipeline.process(idea, mode)`

2. **BaseAgent.process() signature**
   - Old: `process(input_data: str, context: BaseContext)`
   - New: `process(input_data: str = "", context: BaseContext)`
   - Allows calling without input_data for agents that don't need it

3. **Config structure**
   - Added `PipelineConfig` and `default_pipeline_mode`
   - Max iterations now in config, not runtime parameter

### Backward Compatibility

- Not a concern for this internal refactoring
- No external API contracts to maintain

## Summary

This refactoring achieves:

- **Clean parameterless handlers** using instance variables
- **Dictionary-based dispatch** replacing if/elif chains
- **Config-driven defaults** with CLI override capability
- **Proper separation** with PipelineMode in types.py, PipelineConfig in config.py
- **Optional input_data** in BaseAgent for cleaner agent interfaces

## Estimated Effort

- **Core refactoring**: 2-3 hours
- **Testing & validation**: 1-2 hours
- **Documentation**: 1 hour
- **Total**: ~4-6 hours

---

*Ready for implementation. The pipeline will be cleaner, more extensible, and fully config-driven.*
