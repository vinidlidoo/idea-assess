# MessageProcessor Refactoring Proposal

## Executive Summary

The MessageProcessor currently serves a limited role: tracking basic message counts, extracting search queries, and optionally logging messages to JSONL files. This proposal expands its responsibilities to become a comprehensive **Run Analytics Engine** that collects, processes, and outputs detailed metrics for optimization and analysis of agent pipelines.

## Current State Analysis

### What MessageProcessor Does Now

1. **Basic Statistics**: Tracks `message_count` and `search_count`
2. **Message Logging**: Writes full messages to `{run_id}_messages.jsonl` when DEBUG mode
3. **Content Extraction**: Extracts text content and search queries from messages
4. **Session ID Tracking**: Extracts session IDs from SystemMessages

### Current Problems

1. **Incomplete Data Extraction**:
   - Only extracts search queries from ToolUseBlock, ignores actual search result links in ToolResultBlock
   - No tracking of other tool usage (Read, Write, etc.)
   - No tracking of message block types and counts

2. **Limited Output**:
   - Statistics not written to disk, only available in memory
   - No structured run summary file for post-analysis
   - Message logs only written in DEBUG mode

3. **Missing Context**:
   - No correlation between searches and their results
   - No timing information per message
   - No error tracking or retry counts

## Proposed Architecture

### New MessageProcessor Responsibilities

```python
<!-- FEEDBACK: Should maybe think about a better suited name for that class. Something that better describes what this does. -->
class MessageProcessor:
    """
    Run Analytics Engine for tracking, analyzing, and persisting agent execution metrics.
    
    Primary responsibilities:
    1. Track comprehensive message statistics and tool usage
    2. Extract and correlate search queries with result links
    3. Track timing, costs, and resource usage
<!-- FEEDBACK: Have to think about separation of concerns between this class role and the methods in the /src/utils/ folder. requires to think about the two together, I think -->
    4. Output three standardized files per run:
       - stdout.log: Console output (existing)
       - messages.jsonl: Full message logs (enhanced)
       - run_summary.json: Comprehensive run analytics (new)
    """
```

### Three-File Output System

#### 1. **stdout.log** (No Change)

- Current console output captured via logging
- Location: `logs/runs/{run_id}_{slug}.log`

#### 2. **messages.jsonl** (Enhanced)

- **Change**: Always write, not just in DEBUG mode
- **Trigger**: Write when log level is INFO or higher
- **Enhancement**: Include extracted artifacts inline
- Location: `logs/runs/{run_id}_{slug}_messages.jsonl`

Example enhanced message entry:

```json
{
  "timestamp": "2025-08-19T08:30:00",
  "event_type": "sdk_message_detail",
  "agent": "analyst",
  "message_index": 5,
  "message_type": "AssistantMessage",
<!-- FEEDBACK: this is a good start for the extracted_artifacts, but have to think about this a bit deeper. don't think a timestamp is needed here since we have one at the message parent level. we'll need to think about extract_artifacts in each of these cases: ToolUseBlock, ToolResultBlock, which are part of the ContentBlock type, and then we would need to think about what to extract when we get the ResultMessage. looking carefully through the sdk types file is crucial here  -->
  "extracted_artifacts": {
    "web_searches": [
      {
        "query": "AI fitness apps market size 2024",
        "tool_use_id": "tool_123",
        "timestamp": "2025-08-19T08:30:05"
      }
    ],
    "tool_results": [
      {
        "tool_use_id": "tool_123",
        "search_results": [
          {"title": "Market Report 2024", "url": "https://example.com/report"},
          {"title": "Industry Analysis", "url": "https://example.com/analysis"}
        ]
      }
    ],
    "files_read": ["config/prompts/analyst_v3.md"],
<!-- FEEDBACK: maybe look file name that were `edited` too? could be multiple files btw. -->
    "files_written": ["analyses/test-idea/analysis.md"]
  },
  "message": { /* existing message structure */ }
}
```

#### 3. **run_summary.json** (New)

- Comprehensive analytics extending ResultMessage
- Location: `logs/runs/{run_id}_{slug}_summary.json`

```json
{
<!-- FEEDBACK: Have to be careful here. ResultMessage is for a single msg. run_summary is across all msgs received during the run. make sure you check the schema for ResultMessage. Also, maybe the fields we land on should be part of the run_metadata key? -->
  // Standard ResultMessage fields
  "subtype": "analysis_complete",
  "duration_ms": 45000,
  "duration_api_ms": 42000,
  "is_error": false,
  "num_turns": 12,
  "session_id": "324a72c2-c7a7-4b68-90ac-34372b6a31d8",
  "total_cost_usd": 0.23,
  "usage": {
    "input_tokens": 15000,
    "output_tokens": 8000,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 5000
  },
  "result": "Analysis completed successfully",
  
  // Extended analytics
  "run_metadata": {
    "run_id": "20250819_083000",
    "idea": "AI-powered fitness app",
    "slug": "ai-powered-fitness-app",
<!-- FEEDBACK: a run is not only for a single agent, it can be a combination of different agents, right now it's analyst and reviewer, but with phase 3 that will evolve to include a judge and eventually more agents -->
    "agent": "analyst",
    "prompt_variant": "v3",
    "tools_enabled": ["WebSearch", "Read", "Write"],
    "iteration_count": 1,
    "start_time": "2025-08-19T08:30:00",
    "end_time": "2025-08-19T08:30:45"
  },
  
  "message_statistics": {
    "total_messages": 12,
    "by_type": {
      "SystemMessage": 1,
      "UserMessage": 5,
      "AssistantMessage": 5,
      "ResultMessage": 1
    },
    "by_agent": {
      "analyst": 10,
      "system": 2
    }
  },
  
  "block_statistics": {
    "total_blocks": 47,
    "by_type": {
      "TextBlock": 35,
      "ToolUseBlock": 6,
      "ToolResultBlock": 6
    },
    "average_blocks_per_message": 3.9
  },
  
  "tool_usage": {
    "total_tool_calls": 6,
    "by_tool": {
      "WebSearch": 4,
      "Read": 1,
      "Write": 1
    },
    "web_searches": {
      "total": 4,
      "queries": [
        {
          "index": 1,
          "query": "AI fitness apps market size 2024",
          "timestamp": "2025-08-19T08:30:05",
          "result_count": 5,
          "result_links": [
            "https://example.com/market-report",
            "https://example.com/industry-analysis"
          ]
        }
      ]
    },
    "file_operations": {
      "files_read": ["config/prompts/analyst_v3.md"],
<!-- FEEDBACK: maybe here too delineate between file writes and file edits? -->
      "files_written": ["analyses/ai-fitness/analysis.md"],
      "total_bytes_read": 4500,
      "total_bytes_written": 12000
    }
  },
  
  "content_statistics": {
    "total_text_length": 45000,
    "analysis_length": 12000,
    "word_count": 2100,
    "section_count": 8
  },
  
<!-- FEEDBACK: this is a good idea, but maybe we do this at a later stage, not a priority. -->
  "quality_metrics": {
    "evidence_citations": 12,
    "market_data_points": 8,
    "competitor_mentions": 5,
    "risk_factors_identified": 4
  },
  
<!-- FEEDBACK: not sure about this one, wouldn't the error count always be 1 at most? retries is for when the request times out right? warnings is for what? tell me a bit more -->
  "error_tracking": {
    "errors_encountered": 0,
    "retries": 0,
    "warnings": []
  }
}
```

## Implementation Plan

<!-- FEEDBACK: I'm not feeling the two-class architecture here. It might be right but I need more thoughts here. Maybe we insert options and select the best one together? -->
### Phase 1: Core Refactoring (2-3 hours)

1. **Update MessageProcessor class**:
   - Add comprehensive tracking fields
   - Implement tool result parsing for search links
   - Track timing per message
   - Build correlation between tool use and results

2. **Implement artifact extraction**:
   - Parse ToolResultBlock JSON for search result links
   - Track all tool usage, not just WebSearch
   - Extract file paths from Read/Write operations

3. **Create RunSummary class**:
   - Extend ResultMessage with additional fields
   - Implement aggregation methods
   - Add serialization logic

### Phase 2: Integration (1-2 hours)

1. **Update agent_base.py**:
   - Pass MessageProcessor to agents
   - Hook into message stream processing

2. **Update pipeline.py**:
   - Initialize MessageProcessor at pipeline start
   - Collect statistics after each agent run
   - Write run summary at pipeline completion

3. **Update CLI**:
   - Ensure MessageProcessor outputs are written
   - Display key metrics on completion

### Phase 3: Testing & Validation (1 hour)

1. **Unit tests**:
   - Test ToolResultBlock parsing
   - Test statistics aggregation
   - Test file output formats

2. **Integration test**:
   - Run full pipeline with test idea
   - Verify all three files are created
   - Validate JSON structure

## Benefits

### For Prompt Optimization

- Compare search query effectiveness across prompt versions
- Track which prompts generate more evidence-based content
- Measure output quality metrics (citations, data points)

### For Pipeline Optimization

- Identify bottlenecks (which agent takes longest)
- Track iteration patterns in reviewer feedback
- Measure tool usage efficiency

### For Cost Management

- Detailed token usage per agent
- Cost breakdown by operation
- Identify optimization opportunities

### For Debugging

- Complete message history always available
- Correlated tool use and results
- Timing information for performance analysis

## Migration Strategy

1. **Backward Compatibility**:
   - Keep existing get_statistics() method
   - Maintain current logging behavior
   - Add new functionality without breaking existing code

2. **Feature Flags**:
   - Add config option for enhanced logging
   - Default to new behavior, allow opt-out

3. **Gradual Rollout**:
   - Test with analyst agent first
   - Expand to reviewer and judge
   - Full pipeline integration last

## Open Questions

1. **Storage Format**: Should we use JSONL for run_summary or single JSON?
<!-- FEEDBACK: Agree -->
   - **Recommendation**: Single JSON for easy loading and analysis

2. **Compression**: Should we compress message logs for long runs?
<!-- FEEDBACK: Agree -->
   - **Recommendation**: Not initially, add if needed

3. **Real-time Updates**: Should run_summary update during execution?
<!-- FEEDBACK: Agree -->
   - **Recommendation**: Yes, write partial summaries for long runs

4. **Metrics Extensibility**: How to add agent-specific metrics?
<!-- FEEDBACK: Yeah.. we don't need to think about that yet. -->
   - **Recommendation**: Allow agents to contribute custom metrics dict

## Next Steps

1. Review and approve this proposal
2. Implement Phase 1 (core refactoring)
3. Test with existing analyst agent
4. Integrate with pipeline
5. Add comprehensive tests
6. Document new metrics for users

## Success Criteria

- [ ] All three files generated for every run
- [ ] Search result links successfully extracted
- [ ] Run summary contains all proposed fields
- [ ] No performance degradation
- [ ] Existing code continues to work
- [ ] Tests pass with new implementation

---

*This proposal addresses the need for comprehensive run analytics to support prompt optimization and pipeline improvement efforts.*
