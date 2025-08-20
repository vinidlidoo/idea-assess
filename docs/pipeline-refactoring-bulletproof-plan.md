# Pipeline Refactoring: Bulletproof Execution Plan

## Core Principle

**The pipeline creates empty files for agents to edit. That's it.**

Agents are autonomous. They write their own files. The pipeline merely orchestrates and provides file paths.

## Current State Assessment

### ✅ Already Fixed (Just Now)

1. **Iteration numbering** - Now consistently 1-based (iteration 1 = first iteration)
2. **Analyst file paths** - Now writes to `iterations/iteration_1.md` correctly
3. **Pipeline feedback lookup** - Now looks for `reviewer_feedback_iteration_{n}.json`

### ❌ Still Broken

1. **Pipeline reads content back** - Line 301 gets a path string, not content!
2. **SimplePipeline exists** - 120 lines of duplicate code
3. **Unused files created** - metadata.json, iteration_history.json
4. **Duplicate tracking** - Pipeline tracks what RunAnalytics already tracks
5. **analysis.md overwritten** - Should be a symlink to latest iteration

## Phase 1: Emergency Fix (15 mins)

### Fix the Critical Path Bug

**Problem**: Pipeline expects content but gets file path from analyst.

```python
# Line 301 - CURRENT (BROKEN):
current_analysis = analyst_result.content  # This is a PATH!

# Line 301 - FIXED:
analysis_file_path = Path(analyst_result.content)
# Don't read it back! Just track the path.
```

**Changes needed:**

1. Remove `current_analysis` variable entirely
2. Remove `_save_analysis_files()` method (lines 133-165)
3. Don't read content back, just track paths
4. Update line 420 to not include `final_analysis` field

## Phase 2: Delete SimplePipeline (10 mins)

### Remove Duplication

**Files to modify:**

1. `src/core/pipeline.py` - Delete lines 513-631
2. `src/cli.py` - Change import and usage:

```python
# BEFORE:
from src.core.pipeline import AnalysisPipeline, SimplePipeline
...
if max_iterations == 1:
    result = await SimplePipeline.run_analyst_only(...)
else:
    result = await pipeline.run_analyst_reviewer_loop(...)

# AFTER:
from src.core.pipeline import AnalysisPipeline
...
result = await pipeline.run_analyst_reviewer_loop(idea, max_iterations, ...)
```

## Phase 3: Clean File Structure (20 mins)

### Implement Correct File Pattern

<!-- FEEDBACK: run_summary goes into the logs/runs/ already. let's not change that. -->
**New structure:**

```
analyses/
└── {slug}/
    ├── analysis.md → iterations/iteration_N.md  # SYMLINK to latest
    ├── iterations/
    │   ├── iteration_1.md
    │   ├── iteration_1_feedback.json
    │   ├── iteration_2.md
    │   └── iteration_2_feedback.json
    └── logs/
        └── {run_id}_run_summary.json  # From RunAnalytics
```

**Delete these files entirely:**

- metadata.json (NEVER read)
- iteration_history.json (NEVER read)
- reviewer_feedback.json (duplicate)

### Implementation

```python
def _setup_directories(self, slug: str) -> Path:
    """Setup minimal directory structure."""
    analysis_dir = Path("analyses") / slug
    iterations_dir = analysis_dir / "iterations"
    iterations_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir

def _update_symlink(self, analysis_dir: Path, latest_file: Path):
    """Update analysis.md symlink to point to latest iteration."""
    symlink = analysis_dir / "analysis.md"
    if symlink.exists() or symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(latest_file.relative_to(analysis_dir))
```

## Phase 4: Remove Content Tracking (30 mins)

### Let Agents Own Their Files

**Delete these tracking variables:**

- `current_analysis` (line 213)
- `current_analysis_file` (line 214)
- `feedback_history` (line 215)
- `iteration_results` (line 216)

**Keep only:**

- `iteration_count` - for loop control
- `latest_analysis_path` - to pass to reviewer
- `should_continue` - for loop control

### Simplified Loop

```python
async def run_analyst_reviewer_loop(self, idea: str, max_iterations: int = 3, use_websearch: bool = True):
    slug = create_slug(idea)
    analysis_dir = self._setup_directories(slug)
    
    # Setup RunAnalytics (it tracks EVERYTHING)
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{slug}"
    run_analytics = RunAnalytics(run_id=run_id, output_dir=analysis_dir / "logs")
    
    try:
        analyst = AnalystAgent(self.config.analyst)
        reviewer = ReviewerAgent(self.config.reviewer)
        
        for iteration in range(1, max_iterations + 1):  # 1-based
            # Create empty file for analyst
            analysis_file = analysis_dir / "iterations" / f"iteration_{iteration}.md"
            analysis_file.touch()
            
            # Run analyst
            analyst_context = AnalystContext(
                idea_slug=slug,
                output_dir=analysis_dir,
                iteration=iteration,
                run_analytics=run_analytics,
                tools_override=["WebSearch"] if use_websearch and iteration == 1 else [],
            )
            
            if iteration > 1:
                analyst_context.revision_context = RevisionContext(
                    iteration=iteration - 1,
                    previous_analysis_path=analysis_dir / "iterations" / f"iteration_{iteration-1}.md",
                    feedback_path=analysis_dir / "iterations" / f"iteration_{iteration-1}_feedback.json",
                )
            
            result = await analyst.process(idea, analyst_context)
            if not result.success:
                return {"success": False, "error": result.error}
            
            # Update symlink to latest
            self._update_symlink(analysis_dir, Path(result.content))
            
            # Skip reviewer on last iteration
            if iteration >= max_iterations:
                break
            
            # Create empty feedback file for reviewer
            feedback_file = analysis_dir / "iterations" / f"iteration_{iteration}_feedback.json"
            feedback_file.write_text("{}")
            
            # Run reviewer
            reviewer_context = ReviewerContext(
                analysis_path=Path(result.content),
                run_analytics=run_analytics,
            )
            
            feedback_result = await reviewer.process("", reviewer_context)
            if not feedback_result.success:
                break  # Accept analysis if reviewer fails
            
            # Check if should continue (read from feedback file)
            with open(feedback_file) as f:
                feedback = json.load(f)
                if feedback.get("iteration_recommendation") == "accept":
                    break
                    
    finally:
        run_analytics.finalize()
    
    return {
        "success": True,
        "idea": idea,
        "slug": slug,
        "analysis_file": str(analysis_dir / "analysis.md"),
        "analytics_file": str(analysis_dir / "logs" / f"{run_id}_run_summary.json"),
    }
```

## Phase 5: Delete Archive Manager (15 mins)

### Why Delete It?

1. Creates metadata.json that's NEVER read
2. Complex archiving logic for files we don't need
3. RunAnalytics already tracks everything

**Action**: Remove all archive_manager references from pipeline.py

## Phase 6: Testing & Validation (20 mins)

### Test Cases

1. **Single iteration** (`max_iterations=1`)
   - Should create `iteration_1.md` only
   - Should NOT run reviewer
   - `analysis.md` symlinks to `iteration_1.md`

2. **Two iterations** (`max_iterations=2`)
   - Should create `iteration_1.md`, `iteration_1_feedback.json`, `iteration_2.md`
   - `analysis.md` symlinks to `iteration_2.md`

3. **Early acceptance** (reviewer accepts on iteration 1)
   - Should stop after iteration 1 review
   - Should have `iteration_1.md` and `iteration_1_feedback.json`

### Validation Commands

```bash
# Test single iteration
python -m src.cli analyze "test idea 1" --max-iterations 1
ls -la analyses/test-idea-1/
# Expected: analysis.md -> iterations/iteration_1.md

# Test multiple iterations
python -m src.cli analyze "test idea 2" --max-iterations 3
ls -la analyses/test-idea-2/iterations/
# Expected: iteration_1.md, iteration_1_feedback.json, iteration_2.md, ...

# Verify no metadata.json or iteration_history.json
find analyses/ -name "metadata.json" -o -name "iteration_history.json"
# Expected: No results
```

## Success Metrics

### Code Reduction

- **Before**: 632 lines
- **Target**: ~150 lines
- **Reduction**: 76%

### Files Written

- **Before**: 8 files per run
<!-- FEEDBACK: analytics writes 3 files, but agree on pipeline needing to create only 2 files (analysis and feedback) per cycle -->
- **After**: 3 files per run (analysis, feedback, analytics)

### Complexity

- **Before**: 5 helper methods, 2 classes, complex tracking
- **After**: 1 class, 2 helper methods, no tracking

## Risk Mitigation

### Backup Plan

1. Copy current pipeline.py to pipeline_backup.py before changes
2. Test each phase independently
3. Git commit after each successful phase

### Rollback Triggers

- Tests fail after any phase
- File structure breaks
- RunAnalytics stops working

## Final Checklist

- [ ] Phase 1: Fix critical content/path bug
- [ ] Phase 2: Delete SimplePipeline
- [ ] Phase 3: Implement clean file structure with symlinks
- [ ] Phase 4: Remove all content tracking
- [ ] Phase 5: Delete archive manager
- [ ] Phase 6: Run all test cases
- [ ] Verify 76% code reduction achieved
- [ ] Update documentation

---

*This plan fixes the broken pipeline while achieving radical simplification.*
