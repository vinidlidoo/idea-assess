# Batch Processing Feature - Specification & Implementation Plan

**Version**: 1.0  
**Date**: 2025-09-05  
**Status**: Draft  
**Author**: Claude Code Session

## Executive Summary

This document specifies the batch processing feature for the Business Idea Evaluator, enabling concurrent analysis of multiple business ideas from a single input file. The feature transforms the current sequential processing model into a parallel execution system while maintaining backward compatibility and respecting API rate limits.

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Design Goals](#design-goals)
3. [Architecture Overview](#architecture-overview)
4. [Detailed Design](#detailed-design)
5. [Implementation Plan](#implementation-plan)
6. [Risk Analysis](#risk-analysis)
7. [Testing Strategy](#testing-strategy)
8. [Migration Path](#migration-path)

## Problem Statement

### Current Limitations

1. **Sequential Processing Only**: Each idea must be processed one at a time via separate CLI invocations
2. **Manual Coordination**: User must manually run multiple commands or write shell scripts
3. **No Progress Visibility**: No unified view of multiple analyses in progress
4. **Inefficient Resource Use**: Cannot leverage parallel processing capabilities
5. **No Batch Management**: No way to track or manage groups of analyses

### User Requirements

From `requirements.md`:

- Support 10-15 active ideas simultaneously  
- Ideas stored in input file (format TBD based on multi-line requirement)
- Enable systematic comparison across multiple ideas
- Support longer idea descriptions (up to 300 words)

## Design Goals

### Primary Objectives

1. **Concurrent Execution**: Run multiple pipelines in parallel (default: 3 concurrent)
2. **Progress Tracking**: Real-time visibility into all running analyses
3. **Graceful Degradation**: Handle failures without affecting other pipelines
4. **Backward Compatibility**: Existing single-idea CLI must continue working

### Non-Goals

1. Distributed processing across multiple machines
2. Dynamic idea generation during batch processing
3. Real-time web dashboard (CLI output only)
4. Automatic retry of failed ideas (manual re-run required)

## Architecture Overview

### High-Level Design (Simplified)

```text
CLI with --batch flag
        │
        ▼
BatchProcessor (NEW)
        │
        ├─► Load ideas from ideas/pending.md
        │
        ├─► asyncio.Semaphore(max_concurrent=3)
        │
        └─► asyncio.gather() with progress tracking
            ├─► AnalysisPipeline 1 ──► RunAnalytics 1
            ├─► AnalysisPipeline 2 ──► RunAnalytics 2
            ├─► AnalysisPipeline 3 ──► RunAnalytics 3
            └─► ... (limited by semaphore)
```

### Key Components

1. **BatchProcessor**: Simple orchestration using existing asyncio primitives
2. **Ideas Loading**: Parse markdown file with idea descriptions
3. **Concurrency Control**: Standard asyncio.Semaphore (no custom classes)
4. **Progress Tracking**: Simple counter with periodic console updates
5. **Results Aggregation**: Collect PipelineResults from gather()

## Detailed Design

### 1. Input File Format & Workflow

**Files**:

- `ideas/pending.md` - Ideas waiting to be processed
- `ideas/completed.md` - Successfully processed ideas (moved here after completion)
- `ideas/failed.md` - Failed ideas (moved here with error notes)

**Format**: Markdown with H1 headers as idea titles

```markdown
# AI Fitness for Seniors

A comprehensive fitness platform designed specifically for seniors with mobility 
limitations. The app would use AI to analyze individual capabilities, medical 
conditions, and progress over time to create personalized exercise routines.

Key features would include:
- Real-time form correction using computer vision
- Integration with medical devices and health records
- Social features to connect with other seniors
- Gamification elements appropriate for the demographic

The platform would partner with physical therapists and geriatric specialists
to ensure exercises are safe and effective.

# B2B Recycled Materials Marketplace

An online marketplace connecting businesses that produce recyclable waste materials
with companies that can use these materials in their manufacturing processes.
This creates a circular economy while reducing waste disposal costs.

# Virtual Interior Design AR

[Short idea - just a title is fine too]

# Sustainable Packaging Solutions

Biodegradable packaging made from agricultural waste products that can replace
traditional plastic packaging in the food industry. The material would be
compostable within 30 days and safe for food contact.
```

**Parsing Rules**:

- Each H1 header (`#`) starts a new idea
- The header text becomes the idea's short name/slug  
- All content until the next H1 is the idea description
- Empty ideas (just header) are valid
- Maximum 300 words per idea description

### 2. Idea File Management

After processing, ideas are moved between files:

```python
def update_idea_files(self, results: list, ideas: list[tuple[str, str]]):
    """Move processed ideas to completed.md or failed.md."""
    
    completed_ideas = []
    failed_ideas = []
    remaining_ideas = []
    
    for i, (title, description) in enumerate(ideas):
        if i < len(results):
            if isinstance(results[i], Exception):
                # Add to failed with error note
                failed_ideas.append(f"# {title}\n\n{description}\n\n**Error**: {str(results[i])}\n")
            else:
                # Add to completed with timestamp
                completed_ideas.append(f"# {title}\n\n{description}\n\n**Completed**: {datetime.now()}\n")
        else:
            # Keep in pending if not processed
            remaining_ideas.append(f"# {title}\n\n{description}\n")
    
    # Update files atomically
    if completed_ideas:
        completed_path = Path("ideas/completed.md")
        existing = completed_path.read_text() if completed_path.exists() else ""
        completed_path.write_text(existing + "\n".join(completed_ideas))
    
    if failed_ideas:
        failed_path = Path("ideas/failed.md")
        existing = failed_path.read_text() if failed_path.exists() else ""
        failed_path.write_text(existing + "\n".join(failed_ideas))
    
    # Rewrite pending with only unprocessed ideas
    if remaining_ideas:
        Path("ideas/pending.md").write_text("\n".join(remaining_ideas))
    else:
        Path("ideas/pending.md").write_text("# No pending ideas\n")
```

### 3. BatchProcessor Class (Simplified)

```python
class BatchProcessor:
    """Simple batch processor using existing asyncio primitives."""
    
    def __init__(
        self,
        system_config: SystemConfig,
        analyst_config: AnalystConfig,
        reviewer_config: ReviewerConfig,
        fact_checker_config: FactCheckerConfig,
        mode: PipelineMode = PipelineMode.ANALYZE,
        max_concurrent: int = 3
    ):
        self.system_config = system_config
        self.analyst_config = analyst_config
        self.reviewer_config = reviewer_config
        self.fact_checker_config = fact_checker_config
        self.mode = mode
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.progress = {}  # Track progress by idea slug
        
    async def process_batch(self, ideas_file: Path) -> dict:
        """Process all ideas from markdown file concurrently."""
        ideas = self.load_ideas(ideas_file)
        
        # Create tasks with semaphore control
        tasks = []
        for title, description in ideas:
            task = self.process_with_semaphore(title, description)
            tasks.append(task)
        
        # Run all tasks and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return summary
        return {
            "total": len(ideas),
            "successful": sum(1 for r in results if not isinstance(r, Exception)),
            "failed": sum(1 for r in results if isinstance(r, Exception)),
            "results": results
        }
    
    async def process_with_semaphore(self, title: str, description: str) -> PipelineResult:
        """Process single idea with concurrency limit."""
        async with self.semaphore:
            # Combine title and description for full context to analyst
            # Format: "Title: <title>\n\n<description>" or just title if no description
            if description:
                idea = f"{title}\n\n{description}"
            else:
                idea = title
            
            # Pass the full idea text but use title for slug generation
            # Note: We'll need to add slug_override parameter to AnalysisPipeline
            pipeline = AnalysisPipeline(
                idea=idea,
                system_config=self.system_config,
                analyst_config=self.analyst_config,
                reviewer_config=self.reviewer_config,
                fact_checker_config=self.fact_checker_config,
                mode=self.mode,
                slug_suffix=None  # Could use create_slug(title) here for explicit control
            )
            
            # Use title-based slug for tracking (not the full description)
            slug = create_slug(title)  # Import from text_processing
            self.progress[slug] = "running"
            
            try:
                result = await pipeline.process()
                self.progress[slug] = "completed"
                return result
            except Exception as e:
                self.progress[slug] = "failed"
                raise
    
    def load_ideas(self, ideas_file: Path) -> list[tuple[str, str]]:
        """Parse markdown file to extract ideas."""
        content = ideas_file.read_text()
        ideas = []
        
        # Simple regex to split on H1 headers
        import re
        sections = re.split(r'^# (.+)$', content, flags=re.MULTILINE)
        
        # sections[0] is content before first header (ignore)
        # Then alternating title, content, title, content...
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                title = sections[i].strip()
                description = sections[i + 1].strip()
                ideas.append((title, description))
            else:
                # Title without description
                title = sections[i].strip()
                ideas.append((title, ""))
        
        return ideas
```

### 3. Progress Reporting & Logging

**Dual Logging Architecture**: Each pipeline logs individually PLUS batch coordination logging

```python
# In CLI main() when batch mode:
from src.utils.logger import setup_logging

# 1. Setup batch orchestration logging
batch_log_file = setup_logging(
    debug=args.debug,
    idea_slug="batch",  
    run_type="batch"    # Creates logs/batch/TIMESTAMP_batch/
)

# 2. Each pipeline ALSO creates its own logs (unchanged from single mode)
# Inside BatchProcessor.process_with_semaphore():
async def process_with_semaphore(self, title: str, description: str) -> PipelineResult:
    """Process single idea with concurrency limit."""
    async with self.semaphore:
        # ... prepare idea text ...
        
        pipeline = AnalysisPipeline(
            idea=idea,
            # ... configs ...
        )
        
        # The pipeline.process() call will:
        # - Create its own RunAnalytics instance
        # - Log to logs/runs/TIMESTAMP_idea-slug/ as normal
        # - All stdout/stderr captured there as usual
        result = await pipeline.process()
        
        # Batch orchestrator logs summary
        logger.info(f"Pipeline {slug} completed: {result.get('success')}")
        return result

# 3. Progress reporting shows aggregate status
async def show_progress(batch_processor: BatchProcessor, update_interval: float = 2.0):
    """Progress reporter for batch orchestration."""
    logger = logging.getLogger(__name__)  # Logs to batch.log
    
    while True:
        await asyncio.sleep(update_interval)
        
        # Count statuses
        running = sum(1 for s in batch_processor.progress.values() if s == "running")
        completed = sum(1 for s in batch_processor.progress.values() if s == "completed")
        failed = sum(1 for s in batch_processor.progress.values() if s == "failed")
        total = len(batch_processor.progress)
        
        # Log to batch.log AND display to console
        status_msg = f"[Batch Progress] Running: {running}, Completed: {completed}, Failed: {failed}, Total: {total}"
        logger.info(status_msg)  # Goes to logs/batch/*/batch.log
        print(f"\r{status_msg}", end="", flush=True)  # Console display
        
        if running == 0 and total > 0:
            print()  # New line after progress
            break
```

**Log Structure**:

```text
logs/
├── batch/                              # Batch orchestration logs
│   └── 20250905_164200_batch/
│       └── batch.log                   # Batch coordination, progress, summary
│
└── runs/                               # Individual pipeline logs (UNCHANGED)
    ├── 20250905_164201_ai-fitness-seniors/
    │   ├── messages.jsonl              # Agent messages for this idea
    │   ├── run_summary.json            # RunAnalytics summary for this idea
    │   └── debug.log                   # If debug mode enabled
    ├── 20250905_164202_b2b-recycled-materials/
    │   ├── messages.jsonl
    │   ├── run_summary.json
    │   └── debug.log
    └── ... (one per idea processed)
```

**Key Points**:

- Each pipeline runs exactly as if invoked individually
- Each pipeline gets its own `logs/runs/` directory with full logging
- The batch orchestrator has a separate log for coordination
- No changes needed to existing pipeline/logging code
- Full traceability: batch.log shows orchestration, individual logs show details

### 4. Usage Examples

**Basic batch processing:**

```bash
# Process all ideas in ideas/pending.md with default settings
python -m src.cli --batch

# With specific concurrency limit
python -m src.cli --batch --max-concurrent 2

# Fast testing mode (no web tools, analyze only)
python -m src.cli --batch --no-web-tools

# Full processing with review
python -m src.cli --batch --with-review --max-iterations 2

# Debug mode for troubleshooting
python -m src.cli --batch --debug
```

**File workflow:**

```bash
# Before:
ideas/pending.md    # 10 ideas
ideas/completed.md  # Empty or non-existent
ideas/failed.md     # Empty or non-existent

# After successful batch:
ideas/pending.md    # Empty (all processed)
ideas/completed.md  # 9 ideas with timestamps
ideas/failed.md     # 1 idea with error message
```

### 5. CLI Integration

```python
# In cli.py
parser.add_argument(
    "--batch",
    "-b", 
    action="store_true",
    help="Process multiple ideas from ideas/pending.md"
)

parser.add_argument(
    "--ideas-file",
    default="ideas/pending.md",
    help="Path to ideas markdown file (default: ideas/pending.md)"
)

parser.add_argument(
    "--max-concurrent",
    type=int,
    default=3,
    choices=range(1, 6),
    help="Maximum concurrent analyses (default: 3, max: 5)"
)

# Main logic
if args.batch:
    # Create batch processor with same configs as single mode
    processor = BatchProcessor(
        system_config=system_config,
        analyst_config=analyst_config,
        reviewer_config=reviewer_config,
        fact_checker_config=fact_checker_config,
        mode=mode,  # Same mode selection logic as single
        max_concurrent=args.max_concurrent
    )
    
    # Run with progress display
    ideas_file = Path(args.ideas_file)
    if not ideas_file.exists():
        print(f"❌ Ideas file not found: {ideas_file}")
        sys.exit(1)
    
    # Start progress reporter
    progress_task = asyncio.create_task(show_progress(processor))
    
    # Process batch
    print(f"🚀 Processing ideas from {ideas_file}")
    results = await processor.process_batch(ideas_file)
    
    # Wait for progress to finish
    await progress_task
    
    # Show summary
    print(f"\n✅ Completed: {results['successful']}/{results['total']}")
    if results['failed'] > 0:
        print(f"❌ Failed: {results['failed']}")
else:
    # Existing single-idea processing unchanged
    pipeline = AnalysisPipeline(...)
    result = await pipeline.process()
```

### 5. Error Handling

The simplified approach uses `asyncio.gather(return_exceptions=True)` to handle failures gracefully:

```python
# In BatchProcessor.process_batch()
results = await asyncio.gather(*tasks, return_exceptions=True)

# Results will contain mix of:
# - PipelineResult dicts for successful runs
# - Exception objects for failed runs

# Easy to filter and report:
successful = [r for r in results if not isinstance(r, Exception)]
failed = [r for r in results if isinstance(r, Exception)]

# Log failures
for i, result in enumerate(results):
    if isinstance(result, Exception):
        logger.error(f"Idea {i} failed: {result}")
```

### 7. Output Format

**Console Output During Processing**:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH PROCESSING: 10 ideas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Progress: ████████░░░░░░░░ 50% (5/10)

In Progress (3):
  • ai-fitness-seniors     [Iteration 2/3] 🔄
  • b2b-marketplace        [Iteration 1/3] 📝
  • virtual-interior-ar    [Starting]      🚀

Completed: 4 ✅
Failed: 1 ❌
Remaining: 5

[Updated every 1s, Ctrl+C to abort]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Final Summary**:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH PROCESSING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duration: 24m 31s
Success Rate: 90% (9/10)

Results:
┌─────────────────────────┬──────────┬────────────┬─────────┐
│ Idea                    │ Status   │ Iterations │ Time    │
├─────────────────────────┼──────────┼────────────┼─────────┤
│ ai-fitness-seniors      │ ✅ Done  │ 2          │ 3m 45s  │
│ b2b-marketplace         │ ✅ Done  │ 3          │ 5m 12s  │
│ virtual-interior-ar     │ ✅ Done  │ 1          │ 2m 30s  │
│ sustainable-packaging   │ ❌ Failed│ -          │ 0m 15s  │
│ ...                     │          │            │         │
└─────────────────────────┴──────────┴────────────┴─────────┘

Analyses saved to: analyses/
Logs saved to: logs/runs/
Ideas updated: pending.md → completed.md/failed.md
```

## Implementation Order & Critical Path

### MVP (Minimum Viable Product) - 3 hours

For the absolute simplest working version:

1. **Markdown Parser** (30 min)
   - Parse `ideas/pending.md` into list of (title, description)
   - Handle edge cases (empty, malformed)

2. **Simple BatchProcessor** (1 hour)
   - Semaphore for concurrency
   - asyncio.gather() for parallel execution
   - Basic progress print statements

3. **CLI Integration** (30 min)
   - Add `--batch` flag
   - Wire up BatchProcessor

4. **Manual Test** (1 hour)
   - Create test `ideas/pending.md` with 2 ideas
   - Run with `--batch --no-web-tools`
   - Verify analyses created correctly

### Enhancement Layer - 3 hours

After MVP works:

1. **File Management** (1 hour)
   - Move completed ideas to `completed.md`
   - Move failed ideas to `failed.md`
   - Handle file conflicts

2. **Progress Display** (1 hour)
   - Rich table format with emojis
   - Real-time updates

3. **Error Handling** (1 hour)
   - Graceful Ctrl+C handling
   - Clear error messages
   - Validation before processing

## Implementation Plan

### Phase 1: Foundation (1-2 hours)

1. Create `docs/batch-processing/` directory ✅
2. Create markdown parsing function for ideas file
3. Create idea file management functions (move to completed/failed)
4. Write unit tests for markdown parsing

### Phase 2: Core Processing (2-3 hours)

1. Implement simple `BatchProcessor` class
2. Add asyncio.Semaphore for concurrency control
3. Use asyncio.gather() with return_exceptions=True
4. Integrate with existing logging infrastructure

### Phase 3: CLI Integration (1-2 hours)

1. Add `--batch` flag and `--max-concurrent` arguments
2. Add batch mode logic to main()
3. Create enhanced progress display function
4. Update file management after batch completion

### Phase 4: Testing (2 hours)

1. Write unit tests for BatchProcessor
2. Create sample ideas.md file with 2-3 ideas
3. Initial testing: 2 ideas concurrently, analyze-only mode, --no-web-tools
4. Test error handling and file updates
5. Scale up testing after initial validation

### Phase 5: Documentation (30 min)

1. Update README with batch usage example
2. Document markdown format for ideas file
3. Document workflow (pending → completed/failed)

## Risk Analysis

### Technical Risks

1. **Memory Usage**
   - **Risk**: Multiple concurrent pipelines consume significant memory
   - **Mitigation**: Limited to 3-5 concurrent via Semaphore
   - **Impact**: Low

2. **File System Conflicts**
   - **Risk**: Concurrent writes to same directories
   - **Mitigation**: Each idea gets unique slug/directory
   - **Impact**: Low

### Operational Risks

1. **Partial Failures**
   - **Risk**: Some ideas fail, others succeed
   - **Mitigation**: gather(return_exceptions=True) handles gracefully
   - **Impact**: Low - expected behavior

2. **Long Running Times**
   - **Risk**: Batch of 10+ ideas takes 30+ minutes
   - **Mitigation**: Progress reporting shows status (no resume capability in v1)
   - **Impact**: Medium - user expectation setting needed

## Edge Cases & Blind Spots

### Input Validation

1. **Malformed Markdown**
   - **Issue**: Missing or invalid H1 headers
   - **Solution**: Validate format before processing, clear error message

2. **Duplicate Titles**
   - **Issue**: Two ideas with same H1 header → slug collision
   - **Solution**: Not handling in v1 - user should ensure unique titles

3. **Empty Ideas**
   - **Issue**: H1 header with no description
   - **Solution**: Already handled - use title as full idea text

4. **Oversized Descriptions**
   - **Issue**: Description exceeds 300 words
   - **Solution**: Truncate with warning

### File Management

1. **Existing completed/failed.md Files**
   - **Issue**: Files already exist with content
   - **Solution**: Append new entries with timestamps, don't overwrite

2. **Interrupted Processing (Ctrl+C)**
   - **Issue**: Partial updates to pending/completed/failed files
   - **Solution**: Write to temp files first, then atomic rename (implement in v1)

### Error Scenarios

1. **All Ideas Fail**
   - **Issue**: Empty completed.md, all in failed.md
   - **Solution**: Clear messaging, suggest checking logs

2. **Invalid Characters in Titles**
   - **Issue**: Special chars break slug generation
   - **Solution**: Already handled by create_slug() function

3. **File Permission Errors**
   - **Issue**: Can't write to ideas/ or logs/ directories
   - **Solution**: Check permissions upfront, clear error message

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_core/test_batch_processor.py
class TestBatchProcessor:
    async def test_load_ideas_from_file(self)
    async def test_concurrent_execution_limit(self)
    async def test_error_handling(self)
    async def test_progress_reporting(self)
```

### Manual Testing

Skip integration tests - focus on manual testing with real pipelines:

1. Create `ideas/pending.md` with 2 simple ideas
2. Run `python -m src.cli --batch --no-web-tools`
3. Verify analyses created
4. Check file movements (pending → completed/failed)

### Manual Testing Scenarios

1. **Small Batch**: 3 ideas with review mode
2. **Large Batch**: 15 ideas, analyst-only
3. **Mixed Modes**: Different flags per idea (future)
4. **Failure Recovery**: Kill process, check state
5. **Rate Limit**: Aggressive concurrency settings

## Migration Path

### Backward Compatibility

- Existing single-idea CLI unchanged
- All current flags work with `--batch`
- Output structure remains compatible

### Upgrade Path

1. **v1.0**: Basic batch with fixed configuration
2. **v1.1**: Per-idea configuration support
3. **v1.2**: Resume interrupted batches
4. **v2.0**: Web dashboard for monitoring

### Configuration Migration

```bash
# Old way (shell script)
for idea in $(cat ideas.txt); do
    python -m src.cli "$idea" --with-review
done

# New way (built-in)
python -m src.cli --batch --with-review
```

## Out of Scope for v1

To maintain simplicity, the following are explicitly NOT included:

1. **Resume Capability**: If batch is interrupted, must restart from beginning
2. **Rate Limiting**: No throttling between pipeline starts
3. **Per-Idea Configuration**: All ideas use same mode/flags
4. **Idea Dependencies**: No support for ideas that depend on others
5. **Priority Queue**: Ideas processed in file order
6. **Retry Logic**: Failed ideas are not automatically retried
7. **Progress Persistence**: Progress lost if process crashes
8. **Dynamic Concurrency**: Fixed max_concurrent, no auto-adjustment
9. **Web Dashboard**: CLI output only
10. **Distributed Processing**: Single machine only

These can be added in future versions based on usage patterns.

## Appendix A: Alternative Designs Considered

### 1. Multiprocessing Instead of Asyncio

**Pros**: True parallelism, process isolation  
**Cons**: Higher overhead, complex IPC, harder debugging  
**Decision**: Asyncio sufficient since we're I/O bound (API calls)

### 2. Queue-Based Architecture

**Pros**: Better for distributed systems, persistent queue  
**Cons**: Over-engineered for current needs, adds dependencies  
**Decision**: Keep simple with in-memory management

### 3. Dynamic Concurrency Adjustment

**Pros**: Optimal resource usage  
**Cons**: Complex implementation, unpredictable behavior  
**Decision**: Fixed concurrency with manual tuning

## Appendix B: Future Enhancements

1. **Priority Queue**: Process high-priority ideas first
2. **Dependency Management**: Ideas that depend on others
3. **Incremental Processing**: Resume from specific iteration
4. **Cluster Mode**: Distribute across multiple machines
5. **Web API**: REST endpoints for batch management
6. **Metrics Collection**: Prometheus/Grafana integration
7. **Smart Scheduling**: Time-based or resource-based scheduling
8. **Caching**: Reuse results for similar ideas

## Appendix C: Implementation Checklist

- [x] Create markdown parsing function for ideas file (`src/batch/parser.py`)
- [x] Implement idea file management (pending → completed/failed) (`src/batch/file_manager.py`)
- [x] Create simple BatchProcessor class (`src/batch/processor.py`)
- [x] Add asyncio.Semaphore for concurrency control
- [ ] Integrate with existing logger.py infrastructure
- [x] Create enhanced progress display (simplified version without rich)
- [ ] Add --batch flag and --max-concurrent to CLI
- [ ] Write unit tests for all components
- [ ] Test with 5-10 ideas concurrently
- [ ] Update documentation with examples
- [ ] Code review

**Current Status**: Core modules implemented, CLI integration pending

## Summary

This specification provides a clean batch processing implementation that:

### Key Design Decisions

1. **Markdown Input Format**: Ideas in `pending.md` with H1 headers, supports multi-paragraph descriptions
2. **Automatic File Management**: Processed ideas move to `completed.md` or `failed.md`  
3. **Dual Logging Architecture**: Individual pipeline logs in `logs/runs/` + batch coordination in `logs/batch/`
4. **Rich Progress Display**: Detailed table with progress bar and iteration tracking
5. **Zero Pipeline Changes**: Existing `AnalysisPipeline` runs exactly as before

### Implementation Simplicity

- Uses standard `asyncio.Semaphore` and `gather()` - no custom concurrency classes
- No rate limiting needed for 3-5 concurrent pipelines
- Leverages existing logging, pipeline, and analytics infrastructure
- BatchProcessor is a thin orchestration layer (~100 lines)

**Total Implementation Estimate**: 6-8 hours

Ready for implementation with clear separation of concerns and minimal complexity.

---

*This specification is a living document and will be updated as implementation progresses.*
