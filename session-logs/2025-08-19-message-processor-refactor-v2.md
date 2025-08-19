# MessageProcessor Refactoring Proposal V2

## Executive Summary

Transform the current MessageProcessor into a comprehensive **RunAnalytics** system that tracks, analyzes, and persists detailed metrics for multi-agent pipeline executions. This will enable data-driven optimization of prompts and agent orchestration.

## Core Design Decisions

### 1. Naming & Responsibility

After considering the feedback, I propose renaming and potentially splitting responsibilities:

**Option A: Single Class - RunAnalytics**

```python
class RunAnalytics:
    """
    Comprehensive analytics engine for multi-agent pipeline runs.
    
    Responsibilities:
    1. Track messages, tools, and timing across all agents
    2. Extract and correlate artifacts from SDK messages
    3. Aggregate statistics per agent and globally
    4. Persist analytics data for post-run analysis
    """
```

**Option B: Two Classes - Tracker + Persister**

```python
class MessageTracker:
    """Real-time message and artifact tracking during execution."""
    
class AnalyticsPersister:
    """Handles file output and aggregation of tracked data."""
```

**Option C: Three Classes - Clear Separation**

```python
class MessageTracker:
    """Tracks messages and extracts artifacts in real-time."""
    
class RunAggregator:
    """Aggregates statistics across agents and iterations."""
    
class AnalyticsWriter:
    """Handles all file I/O for logs and summaries."""
```

**Decision**: We'll proceed with Option A (single RunAnalytics class) that leverages existing src/utils/ functions:

- Use `json_validator.py` for validating analytics JSON output
- Use `text_processing.py` for text analysis (word counts, etc.)
- Coordinate with `logger.py` for file paths and run IDs

### 2. Separation of Concerns with /src/utils/

Current utils structure:

- `logger.py` - Handles log setup and console/file output
- `file_operations.py` - Handles analysis file I/O
- `json_validator.py` - JSON validation
- `text_processing.py` - Text manipulation

**Proposed boundaries**:

- **RunAnalytics** (in core/): Message tracking, artifact extraction, statistics aggregation
- **logger.py**: Continue handling stdout.log and console output
- **RunAnalytics**: **Solely responsible for messages.jsonl** (full message logs + extracted artifacts)
  - Gets log directory path from logger.py
  - Writes each message with artifacts as JSONL entries
- **RunAnalytics**: Solely responsible for run_summary.json
- **file_operations.py**: Continue handling analysis files (not analytics files)

## Artifact Extraction Design

Based on SDK types (`ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock`):

### From ToolUseBlock

```python
def extract_tool_use_artifacts(block: ToolUseBlock) -> dict:
    """Extract artifacts from tool invocation."""
    artifacts = {
        "tool_id": block.id,
        "tool_name": block.name,
        "tool_input": {}
    }
    
    # Tool-specific extraction
    if block.name == "WebSearch":
        artifacts["tool_input"]["query"] = block.input.get("query")
    elif block.name == "Read":
        artifacts["tool_input"]["file_path"] = block.input.get("file_path")
    elif block.name == "Write":
        artifacts["tool_input"]["file_path"] = block.input.get("file_path")
        artifacts["tool_input"]["content_size"] = len(block.input.get("content", ""))
    elif block.name == "Edit":
        artifacts["tool_input"]["file_path"] = block.input.get("file_path")
        artifacts["tool_input"]["old_size"] = len(block.input.get("old_string", ""))
        artifacts["tool_input"]["new_size"] = len(block.input.get("new_string", ""))
    elif block.name == "MultiEdit":
        artifacts["tool_input"]["file_path"] = block.input.get("file_path")
        artifacts["tool_input"]["edit_count"] = len(block.input.get("edits", []))
    
    return artifacts
```

### From ToolResultBlock

```python
def extract_tool_result_artifacts(block: ToolResultBlock) -> dict:
    """Extract artifacts from tool results."""
    artifacts = {
        "tool_use_id": block.tool_use_id,
        "is_error": block.is_error,
        "result_data": {}
    }
    
    # Parse content based on structure
    if isinstance(block.content, str):
        # For WebSearch results, parse the JSON-like structure
        if "Links:" in block.content:
            # Extract search result links
            import json
            import re
            links_match = re.search(r'Links:\s*(\[.*?\])', block.content, re.DOTALL)
            if links_match:
                try:
                    links = json.loads(links_match.group(1))
                    artifacts["result_data"]["search_results"] = [
                        {"title": link.get("title"), "url": link.get("url")}
                        for link in links
                    ]
                except json.JSONDecodeError:
                    pass
        
        # For file operations, extract success/failure
        artifacts["result_data"]["content_preview"] = block.content[:200]
    
    elif isinstance(block.content, list):
        # Yes, Python allows list assignment to dict entries
        # This captures structured data from tools that return JSON arrays
        artifacts["result_data"]["structured_result"] = block.content
    
    return artifacts
```

### From TextBlock

```python
def extract_text_artifacts(block: TextBlock) -> dict:
    """Extract artifacts from text blocks."""
    artifacts = {
        "text_length": len(block.text),
        "text_preview": block.text[:100] + "..." if len(block.text) > 100 else block.text
    }
    return artifacts
```

### From ThinkingBlock

```python
def extract_thinking_artifacts(block: ThinkingBlock) -> dict:
    """Extract artifacts from thinking blocks."""
    artifacts = {
        "thinking_length": len(block.thinking),
        "thinking_signature": block.signature,
        # Don't store full thinking content in artifacts to avoid bloat
        "thinking_preview": block.thinking[:200] + "..." if len(block.thinking) > 200 else block.thinking
    }
    return artifacts
```

### From ResultMessage

```python
def extract_result_artifacts(msg: ResultMessage) -> dict:
    """Extract final execution metrics from result message."""
    return {
        "session_metrics": {
            "subtype": msg.subtype,
            "duration_ms": msg.duration_ms,
            "duration_api_ms": msg.duration_api_ms,
            "is_error": msg.is_error,
            "num_turns": msg.num_turns,
            "session_id": msg.session_id,
            "total_cost_usd": msg.total_cost_usd,
            "usage": msg.usage
        }
    }
```

## Enhanced Message Log Structure

```json
{
  "timestamp": "2025-08-19T08:30:00",
  "run_id": "20250819_083000",
  "agent": "analyst",
  "iteration": 1,
  "message_index": 5,
  "message_type": "AssistantMessage",
  "artifacts": {
    "tool_uses": [
      {
        "tool_id": "tool_123",
        "tool_name": "WebSearch",
        "query": "AI fitness apps market size 2024"
      },
      {
        "tool_id": "tool_124",
        "tool_name": "Read",
        "file_path": "config/prompts/analyst_v3.md"
      }
    ],
    "tool_results": [
      {
        "tool_use_id": "tool_123",
        "is_error": false,
        "search_results": [
          {"title": "Market Report 2024", "url": "https://example.com/report"},
          {"title": "Industry Analysis", "url": "https://example.com/analysis"}
        ]
      }
    ],
    "text_blocks": {
      "count": 3,
      "total_length": 4500
    },
    "thinking_blocks": {
      "count": 1,
      "total_length": 2000,
      "signatures": ["thinking_sig_123"]
    }
  },
  "message": { /* truncated SDK message */ }
}
```

## Run Summary Structure (Not Extending ResultMessage)

The run_summary.json represents aggregated analytics across the entire pipeline run, not a single message:

```json
{
  "run_id": "20250819_083000",
  "run_type": "analyst_reviewer_pipeline",
  "status": "completed",
  "total_duration_ms": 120000,
  "start_time": "2025-08-19T08:30:00",
  "end_time": "2025-08-19T08:32:00",
  
  "pipeline_config": {
    "idea": "AI-powered fitness app",
    "slug": "ai-powered-fitness-app",
    "agents_used": ["analyst", "reviewer"],
    "max_iterations": 3,
    "tools_enabled": ["WebSearch", "Read", "Write", "Edit"],
    "prompt_variants": {
      "analyst": "v3",
      "reviewer": "main"
    }
  },
  
  "agent_metrics": {
    "analyst": {
      "invocations": 2,
      "messages_processed": 24,
      "total_duration_ms": 90000,
      "total_cost_usd": 0.18,
      "token_usage": {
        "input": 12000,
        "output": 6000,
        "cached": 3000
      }
    },
    "reviewer": {
      "invocations": 2,
      "messages_processed": 12,
      "total_duration_ms": 30000,
      "total_cost_usd": 0.05,
      "token_usage": {
        "input": 3000,
        "output": 2000,
        "cached": 1000
      }
    }
  },
  
  "iterations": [
    {
      "iteration": 1,
      "analyst_session_id": "session_123",
      "reviewer_session_id": "session_124",
      "decision": "reject",
      "critical_issues": 3,
      "improvements": 5
    },
    {
      "iteration": 2,
      "analyst_session_id": "session_125",
      "reviewer_session_id": "session_126",
      "decision": "accept",
      "critical_issues": 0,
      "improvements": 2
    }
  ],
  
  "tool_usage_summary": {
    "total_invocations": 15,
    "by_tool": {
      "WebSearch": {
        "count": 8,
        "queries": [
          "AI fitness apps market size 2024",
          "senior fitness technology adoption",
          "wearable devices elderly market"
        ],
        "total_results_retrieved": 40
      },
      "Read": {
        "count": 3,
        "files": [
          "config/prompts/analyst_v3.md",
          "config/prompts/reviewer_main.md",
          "analyses/ai-powered-fitness-app/analysis.md"
        ],
        "total_bytes_read": 15000
      },
      "Write": {
        "count": 2,
        "files": [
          "analyses/ai-powered-fitness-app/iterations/1_analysis.md",
          "analyses/ai-powered-fitness-app/analysis.md"
        ],
        "total_bytes_written": 24000
      },
      "Edit": {
        "count": 2,
        "files": [
          "analyses/ai-powered-fitness-app/analysis.md"
        ],
        "total_edits": 2
      }
    }
  },
  
  "content_summary": {
    "final_analysis_length": 12000,
    "final_word_count": 2100,
    "total_text_generated": 30000,
    "total_thinking_tokens": 5000
  },
  
  "error_summary": {
    "total_errors": 0,
    "sdk_errors": [],
    "tool_errors": [],
    "validation_errors": []
  }
}
```

## Error Tracking Clarification

The error tracking section captures different types of issues:

```python
"error_summary": {
    "total_errors": 2,  # Can be >1 if errors are caught and retried
    "sdk_errors": [
        {
            "type": "CLIConnectionError",
            "message": "Connection timeout",
            "timestamp": "2025-08-19T08:31:15",
            "recovered": true
        }
    ],
    "tool_errors": [
        {
            "tool": "WebSearch",
            "error": "Rate limit exceeded",
            "timestamp": "2025-08-19T08:31:45",
            "recovered": false
        }
    ],
    "validation_errors": []  # JSON parsing, schema validation, etc.
}
```

- **Multiple errors possible**: Errors that are caught and handled (with retry logic)
- **SDK errors**: Connection issues, timeout, JSON decode errors
- **Tool errors**: Individual tool failures (rate limits, file not found, etc.)
- **Validation errors**: Data validation issues in our code

## Implementation Architecture Options

### Option 1: Enhanced Single Class

```python
# core/run_analytics.py
class RunAnalytics:
    def __init__(self, run_id: str, idea_slug: str):
        self.run_id = run_id
        self.idea_slug = idea_slug
        self.agent_trackers: dict[str, AgentTracker] = {}
        self.global_stats = GlobalStats()
        
    def track_message(self, message: Message, agent: str, iteration: int):
        """Track a message and extract artifacts."""
        
    def write_message_log(self, message_data: dict):
        """Append to messages.jsonl."""
        
    def write_run_summary(self):
        """Write aggregated run_summary.json."""
        
    def get_current_stats(self) -> dict:
        """Get current statistics for display."""
```

### Option 2: Modular Design

```python
# core/analytics/tracker.py
class MessageTracker:
    """Tracks messages and extracts artifacts."""
    def track(self, message: Message) -> TrackedMessage:
        pass

# core/analytics/aggregator.py  
class StatsAggregator:
    """Aggregates statistics across agents."""
    def add_agent_stats(self, agent: str, stats: dict):
        pass
    
    def get_summary(self) -> dict:
        pass

# core/analytics/writer.py
class AnalyticsWriter:
    """Handles file I/O for analytics."""
    def write_message_log(self, data: dict):
        pass
    
    def write_run_summary(self, summary: dict):
        pass

# core/analytics/analytics.py
class RunAnalytics:
    """Orchestrates tracking, aggregation, and writing."""
    def __init__(self):
        self.tracker = MessageTracker()
        self.aggregator = StatsAggregator()
        self.writer = AnalyticsWriter()
```

### Option 3: Event-Driven

```python
# core/analytics.py
class AnalyticsEvent:
    """Base class for analytics events."""
    pass

class MessageEvent(AnalyticsEvent):
    """Message received event."""
    pass

class ToolUseEvent(AnalyticsEvent):
    """Tool invoked event."""
    pass

class RunAnalytics:
    """Event-driven analytics system."""
    def __init__(self):
        self.event_handlers = {}
        self.register_handlers()
    
    def emit(self, event: AnalyticsEvent):
        """Process an analytics event."""
        handler = self.event_handlers.get(type(event))
        if handler:
            handler(event)
```

**Decision**: Proceed with Option 1 (enhanced single class) for implementation, with clean internal separation that allows future refactoring if complexity grows.

## Integration Points

### 1. Pipeline Integration

```python
# core/pipeline.py
class AnalysisPipeline:
    async def run_analyst_reviewer_loop(self, idea: str, ...):
        # Initialize analytics at pipeline start
        run_analytics = RunAnalytics(run_id, idea_slug)
        
        try:
            for iteration in range(max_iterations):
                # Track analyst execution
                analyst_result = await analyst.process(idea, context)
                run_analytics.track_agent_execution("analyst", analyst_result, iteration)
                
                # Track reviewer execution
                reviewer_result = await reviewer.process("", context)
                run_analytics.track_agent_execution("reviewer", reviewer_result, iteration)
                
        finally:
            # Write final summaries
            run_analytics.write_run_summary()
```

### 2. Agent Integration (Avoiding Duplication with AgentResult)

**Current AgentResult Structure**:

```python
@dataclass
class AgentResult:
    content: str              # The generated analysis/feedback
    metadata: dict[str, object]  # Currently contains: message_count, search_count, duration, etc.
    success: bool
    error: str | None = None
```

**Duplication Concern**: AgentResult.metadata currently tracks some metrics that RunAnalytics would also track.

**Proposed Solution - Clear Separation of Responsibilities**:

<!-- FEEDBACK: Agree here. Keep to a strict minimum necessary to run the code and leave the rest to run_analytics. for example `sections_created` feels unnecessary here. -->
1. **AgentResult.metadata** - Keep strict minimum necessary to run code:
   - `output_file`: Path to generated file
   - `word_count`: Size of generated content (needed for validation)

2. **RunAnalytics** - Track comprehensive execution analytics:
   - All message details and artifacts
   - Tool usage patterns
   - Timing and performance metrics
   - Cross-agent correlations

**Integration Approach**:

After examining the codebase, the integration needs to happen at two levels:

1. **Context Enhancement** - Add optional RunAnalytics to BaseContext:

```python
# core/config.py
@dataclass
class BaseContext:
    """Base context for all agent operations."""
    revision_context: RevisionContext | None = None
    tools_override: list[str] | None = None
    prompt_version_override: str | None = None
    run_analytics: RunAnalytics | None = None  # NEW: Optional analytics tracker
```

2. **Message Tracking in Agent** - Track during SDK message stream:

```python
# Example from agents/analyst.py showing actual implementation
class AnalystAgent(BaseAgent):
    async def _run_analysis(self, idea: str, context: AnalystContext) -> AnalysisResult | None:
        # ... setup code ...
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            
            # This is where messages come from - the SDK client stream
            async for message in client.receive_response():
                # NEW: Track with RunAnalytics (replaces MessageProcessor)
                if context.run_analytics:
                    context.run_analytics.track_message(
                        message, 
                        agent_name="analyst",
                        iteration=context.revision_context.iteration if context.revision_context else 0
                    )
                
                # OLD: processor.track_message(message) - REMOVED
                # The RunAnalytics now handles all tracking duties
                
                if isinstance(message, ResultMessage):
                    # RunAnalytics already captured this for summary
                    # Extract final content for agent return value
                    pass
```

3. **Pipeline Sets Up Analytics**:

```python
# core/pipeline.py
class AnalysisPipeline:
    async def run_analyst_reviewer_loop(self, idea: str, ...):
        # Create RunAnalytics for entire pipeline run
        run_analytics = RunAnalytics(run_id, idea_slug)
        
        # Pass to agents via context
        analyst_context = AnalystContext(
            idea_slug=slug,
            run_analytics=run_analytics  # Pass analytics
        )
        
        # Agents will track messages automatically
        analyst_result = await analyst.process(idea, analyst_context)
```

**Benefits of This Separation**:

- No duplication - each class has clear responsibilities
- AgentResult remains lightweight and output-focused
- RunAnalytics provides comprehensive execution telemetry
- Easy to aggregate AgentResults without redundant analytics data

## Migration Plan

### Phase 1: Core Implementation (3-4 hours)

1. Create RunAnalytics class with artifact extraction
2. Implement message tracking and correlation logic
3. Add file writing capabilities

### Phase 2: Integration (2 hours)

1. Integrate with pipeline.py
2. Update agent_base.py to pass analytics context
3. Ensure logger.py cooperation for messages.jsonl

### Phase 3: Testing (1 hour)

1. Unit tests for artifact extraction
2. Integration test with full pipeline
3. Validate output file formats

## Benefits Over V1

1. **Clearer architecture** with explicit options to evaluate
2. **Accurate SDK type handling** based on actual ContentBlock types
3. **Multi-agent support** built into the design
4. **Proper separation** from ResultMessage (which is per-message, not per-run)
5. **Clear boundaries** with existing utils modules
6. **Actionable error tracking** with recovery status

## Implementation Checklist

### Core RunAnalytics Class

- [ ] Create `core/run_analytics.py` with single class design
- [ ] Implement artifact extraction for all block types (Text, Thinking, ToolUse, ToolResult)
- [ ] Add message tracking with correlation between tool use and results
- [ ] Implement JSONL writer for messages.jsonl
- [ ] Implement JSON writer for run_summary.json
- [ ] Add aggregation methods for statistics

### Integration Tasks

- [ ] Update `pipeline.py` to initialize and pass RunAnalytics
- [ ] Update `agent_base.py` to track messages via context
- [ ] Modify `AgentResult.metadata` to avoid duplication
- [ ] Coordinate with `logger.py` for log directory paths

### Testing

- [ ] Unit test artifact extraction for each block type
- [ ] Test ThinkingBlock handling (even if not used yet)
- [ ] Test tool correlation logic
- [ ] Integration test with full pipeline
- [ ] Validate all three output files

## Final Design Summary

### Key Decisions Made

1. **Class Name**: `RunAnalytics` (not MessageProcessor)
2. **Architecture**: Single class with clean internal methods (Option 1)
3. **File Ownership**:
   - `stdout.log`: Owned by logger.py
   - `messages.jsonl`: Owned by RunAnalytics
   - `run_summary.json`: Owned by RunAnalytics
4. **Integration Pattern**:
   - Add `run_analytics` field to BaseContext
   - Pipeline creates RunAnalytics instance
   - Agents track messages via context during SDK stream
5. **AgentResult.metadata**: Minimal - only output_file and word_count
6. **Block Support**: Full support for TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock

### Implementation Priority

1. **Phase 1**: Create RunAnalytics class with all extractors
2. **Phase 2**: Update BaseContext and integrate with pipeline
3. **Phase 3**: Modify agents to use RunAnalytics from context
4. **Phase 4**: Test with full pipeline run

### Success Metrics

- All three output files generated correctly
- No duplication between AgentResult and RunAnalytics
- Tool correlations working (matching tool_use_id)
- ThinkingBlock tracked even if unused
- Clean separation of concerns maintained

---

*Final V2 proposal with all feedback incorporated and ready for implementation.*
