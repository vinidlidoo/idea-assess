# Fact-Checker Agent Specification

**Created**: 2025-08-26  
**Status**: Draft v1  
**Purpose**: Parallel citation verification agent to ensure accuracy of analyst-generated content

## Problem Statement

Based on citation analysis (see `session-logs/2025-08-26-citation-analysis-findings.md`), we found:

- Baseline analyses have a 70% citation failure rate
- Even improved prompts have 33% citation errors
- Common issues: 404 errors, false attributions, fabricated statistics
- WebFetch usage directly correlates with accuracy, but analysts rarely use it

## Proposed Solution

A dedicated Fact-Checker Agent that runs in parallel with the Reviewer Agent, focusing exclusively on verifying factual accuracy and citation validity.

## Architecture

```text
                    AnalystAgent
                         ↓
                    Analysis.md
                    ↓          ↓
            [Parallel Execution]
            ↓                    ↓
      ReviewerAgent         FactCheckerAgent
            ↓                    ↓
      feedback.json       fact_check.json
            ↓                    ↓
            └────────┬───────────┘
                     ↓
                JudgeAgent (uses both)
```

## Agent Configuration

### Base Class

```python
class FactCheckerAgent(BaseAgent):
    """
    Verifies factual accuracy of analyses through systematic citation checking.
    
    Runs in parallel with ReviewerAgent to maintain performance.
    """
```

### Core Capabilities

**Primary Tools**:

- `WebFetch` - Primary tool for verification (mandatory for all citations)
- `WebSearch` - Finding alternative sources when citations fail
- `Read` - Examining the analysis document
- `Write` - Creating fact-check report

**No Access To**:

- `Edit` - Cannot modify the analysis
- `TodoWrite` - Not needed for verification

## Fact-Checking Workflow

### Phase 1: Extraction

1. Read analysis document
2. Extract all factual claims
3. Map claims to citations
4. Identify unsourced claims

### Phase 2: Verification

For each citation:

1. WebFetch the URL
2. Verify claim matches source
3. Check number accuracy
4. Validate company/product attributions

### Phase 3: Assessment

1. Calculate accuracy metrics
2. Categorize issues by severity
3. Generate recommendations
4. Output structured report

## Input/Output Specification

### Input Context

```python
@dataclass
class FactCheckerContext:
    """Context for fact-checking operations."""
    
    analysis_input_path: Path        # The analysis to verify
    fact_check_output_path: Path     # Where to write results
    iteration: int                    # Current iteration number
    run_analytics: RunAnalytics | None = None
```

### Output Format

```json
{
  "timestamp": "2025-08-26T16:45:00Z",
  "analysis_path": "analyses/ai-tutoring-platform/iteration_1.md",
  "summary": {
    "total_claims": 25,
    "verified_claims": 18,
    "unverified_claims": 4,
    "false_claims": 3,
    "accuracy_score": 72.0,
    "citations_checked": 10,
    "citations_valid": 7
  },
  "critical_issues": [
    {
      "severity": "high",
      "claim": "Our pilot with 500 students showed 73% improvement",
      "issue": "No source provided, appears fabricated",
      "location": "line 45",
      "recommendation": "Remove claim or provide verifiable source"
    }
  ],
  "citation_issues": [
    {
      "citation_id": "[2]",
      "url": "https://example.com/study",
      "status": "404_not_found",
      "claim": "AI tutoring doubles learning gains",
      "recommendation": "Find alternative source or remove claim"
    },
    {
      "citation_id": "[6]",
      "url": "https://example.com/pricing",
      "status": "claim_not_in_source",
      "claim": "$4/month or $44/year",
      "actual": "No pricing information found",
      "recommendation": "Correct to match source or remove"
    }
  ],
  "unsourced_claims": [
    {
      "claim": "87% of students use digital learning tools daily",
      "location": "line 67",
      "severity": "medium",
      "recommendation": "Add citation or qualify as estimate"
    }
  ],
  "verification_details": {
    "webfetch_attempts": 10,
    "webfetch_successful": 7,
    "websearch_fallbacks": 2,
    "processing_time_seconds": 45.3
  },
  "recommendations": [
    "Priority 1: Remove or source the pilot study claim",
    "Priority 2: Replace broken Harvard citation [2]",
    "Priority 3: Verify pricing claims with current sources"
  ]
}
```

## Prompt Structure

### System Prompt (`config/prompts/agents/fact-checker/system.md`)

```markdown
# Fact-Checker Agent

You are a meticulous fact-checking specialist. Your sole purpose is to verify the accuracy of every factual claim and citation in business analyses.

## Core Principles

1. **Trust Nothing** - Verify every claim, even if it seems reasonable
2. **Source First** - A claim without a verifiable source is invalid
3. **Exact Matching** - Numbers and attributions must match sources exactly
4. **Fail Gracefully** - If you can't verify, mark as unverified (don't guess)

## Verification Requirements

For EVERY citation:
- You MUST use WebFetch to access the source
- You MUST verify the claim matches what's stated
- You MUST check numerical accuracy
- You MUST validate company/product attributions

For unsourced claims:
- Flag any statistical claim without citation
- Flag any market size/growth claim without source
- Flag any competitor data without verification

## Severity Levels

**Critical (High)**:
- Fabricated data (pilot results, user counts)
- False company attributions
- Completely wrong statistics (>50% error)

**Significant (Medium)**:
- Broken links (404/403 errors)
- Unsourced market claims
- Minor numerical errors (10-50% off)

**Minor (Low)**:
- Vague attributions
- Missing publication dates
- Incomplete citations
```

### User Prompt (`config/prompts/agents/fact-checker/user/main.md`)

```markdown
Analyze the document at {{analysis_path}} and verify all factual claims.

Your task:
1. Extract every factual claim from the analysis
2. Use WebFetch to verify EVERY citation
3. Search for sources for any unsourced claims
4. Calculate accuracy metrics
5. Write your findings to {{output_path}}

Focus areas:
- Market size and growth statistics
- Company metrics (users, revenue, funding)
- Product features and pricing
- Success rates and pilot results
- Competitor comparisons

Be especially vigilant for:
- Claims about "our pilot" or "our results" (often fabricated)
- Precise percentages without sources
- Company-specific data that seems too detailed
- Links that return 404 or 403 errors

Output a comprehensive fact-check report in JSON format.
```

## Implementation Plan

### File Structure

```text
config/prompts/agents/fact-checker/
├── system.md                 # Core fact-checking principles
└── user/
    ├── main.md              # Main task prompt
    └── examples.md          # Good/bad citation examples

src/agents/
└── fact_checker.py          # FactCheckerAgent implementation

templates/agents/fact-checker/
└── fact_check.json          # Output template
```

### Core Implementation

```python
# src/agents/fact_checker.py

from typing import Any
from pathlib import Path
import json

from ..core.agent_base import BaseAgent
from ..core.types import Success, Error, AgentResult
from ..utils.file_operations import load_prompt_with_includes

class FactCheckerAgent(BaseAgent):
    """
    Fact-checking agent for verifying analysis accuracy.
    
    Responsibilities:
    - Verify all citations using WebFetch
    - Flag unsourced claims
    - Calculate accuracy metrics
    - Generate fact-check report
    """
    
    def __init__(self, config: Any) -> None:
        super().__init__(config)
        # Ensure WebFetch is always available
        if "WebFetch" not in self.config.allowed_tools:
            self.config.allowed_tools.append("WebFetch")
    
    async def process(
        self,
        input_data: str,
        context: Any
    ) -> AgentResult:
        """
        Process analysis for fact-checking.
        
        Args:
            input_data: Unused (reads from context.analysis_input_path)
            context: FactCheckerContext with paths and metadata
            
        Returns:
            Success with fact-check results or Error
        """
        try:
            # Load analysis document
            analysis_content = context.analysis_input_path.read_text()
            
            # Create user prompt with context
            user_prompt = self.build_user_prompt(
                analysis_path=str(context.analysis_input_path),
                output_path=str(context.fact_check_output_path)
            )
            
            # Run fact-checking via message processor
            response = await self.message_processor.process_message(
                system_prompt=self.load_system_prompt(),
                user_prompt=user_prompt,
                context={
                    "agent": "fact_checker",
                    "iteration": context.iteration
                }
            )
            
            # Parse and validate output
            fact_check_data = self._parse_fact_check_output(
                context.fact_check_output_path
            )
            
            # Log metrics
            self._log_metrics(fact_check_data, context)
            
            return Success(
                data=fact_check_data,
                metadata={
                    "accuracy_score": fact_check_data.get("summary", {}).get("accuracy_score", 0),
                    "critical_issues": len(fact_check_data.get("critical_issues", [])),
                    "processing_time": fact_check_data.get("verification_details", {}).get("processing_time_seconds", 0)
                }
            )
            
        except Exception as e:
            return Error(message=f"Fact-checking failed: {str(e)}")
    
    def _parse_fact_check_output(self, output_path: Path) -> dict:
        """Parse and validate fact-check JSON output."""
        try:
            return json.loads(output_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Invalid fact-check output: {e}")
    
    def _log_metrics(self, data: dict, context: Any) -> None:
        """Log fact-checking metrics to analytics."""
        if context.run_analytics:
            summary = data.get("summary", {})
            context.run_analytics.log_custom_metric(
                "fact_check_accuracy",
                summary.get("accuracy_score", 0)
            )
            context.run_analytics.log_custom_metric(
                "fact_check_issues",
                len(data.get("critical_issues", []))
            )
```

### Pipeline Integration

```python
# src/core/pipeline.py modifications

async def _run_review_and_fact_check(self) -> tuple[bool, dict]:
    """Run reviewer and fact-checker in parallel."""
    
    reviewer = ReviewerAgent(self.reviewer_config)
    fact_checker = FactCheckerAgent(self.fact_checker_config)
    
    # Create contexts
    reviewer_context = ReviewerContext(...)
    fact_checker_context = FactCheckerContext(...)
    
    # Run in parallel
    review_task = asyncio.create_task(
        reviewer.process("", reviewer_context)
    )
    fact_check_task = asyncio.create_task(
        fact_checker.process("", fact_checker_context)
    )
    
    # Wait for both
    review_result, fact_check_result = await asyncio.gather(
        review_task, fact_check_task
    )
    
    # Process results
    return self._process_review_results(review_result, fact_check_result)
```

## Success Metrics

### Primary Metrics

- **Citation Accuracy Rate**: Target >90% valid citations
- **False Claim Detection**: Catch 100% of fabricated claims
- **Processing Time**: <60 seconds per analysis

### Secondary Metrics

- WebFetch success rate
- Unsourced claims identified
- Alternative sources found

## Testing Strategy

### Test Cases

1. **Fabrication Detection**
   - Input: Analysis with "Our pilot showed 73% improvement"
   - Expected: Flagged as critical issue, no source

2. **404 Detection**
   - Input: Citation to non-existent page
   - Expected: Marked as 404, recommendation to remove

3. **Number Verification**
   - Input: "Market worth $50B" with source saying $30B
   - Expected: Flagged as false claim with correction

4. **Attribution Check**
   - Input: Generic stat attributed to specific company
   - Expected: Flagged as misattribution

### A/B Testing

Run parallel on same analyses:

- Control: Analyst + Reviewer only
- Test: Analyst + Reviewer + FactChecker

Measure:

- Citation accuracy improvement
- False claims caught
- User trust metrics

## Rollout Plan

### Phase 1: MVP (Week 1)

- Basic WebFetch verification
- JSON output format
- Critical issue detection

### Phase 2: Enhancement (Week 2)

- Parallel execution with reviewer
- Alternative source suggestions
- Severity scoring

### Phase 3: Integration (Week 3)

- Judge agent incorporation
- UI badges for fact-checked content
- Metrics dashboard

## Open Questions

1. **Should fact-checker be able to edit?**
   - Pro: Could fix minor issues automatically
   - Con: Maintains separation of concerns
   - Recommendation: Read-only for v1

2. **Threshold for passing?**
   - Option A: Any critical issue = fail
   - Option B: Accuracy score threshold (e.g., >80%)
   - Recommendation: Critical issues = mandatory fix

3. **WebFetch rate limits?**
   - Need to test with high citation counts
   - May need queuing or caching strategy

## Related Documents

- `session-logs/2025-08-26-citation-analysis-findings.md` - Evidence for this agent
- `config/prompts/experimental/analyst/citation-strict.md` - Current mitigation attempt
- `src/agents/reviewer.py` - Parallel agent pattern reference

---

*Draft specification v1 - 2025-08-26*
