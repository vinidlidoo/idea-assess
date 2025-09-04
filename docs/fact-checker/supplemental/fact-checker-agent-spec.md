# Fact-Checker Agent Specification

**Created**: 2025-08-26  
**Updated**: 2025-08-27  
**Status**: Implementation-Ready v2  
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

### Iteration-Aware Parallel Execution

```text
Iteration 1:     AnalystAgent
                      ↓
                 Analysis.md (v1)
                   ↓        ↓
            [Parallel Execution]
            ↓                  ↓
      ReviewerAgent      FactCheckerAgent
            ↓                  ↓
      feedback.json      fact_check.json
            ↓                  ↓
            └────────┬─────────┘
                     ↓
              Both must approve?
                  No ↓ Yes
                     ↓
Iteration 2:   AnalystAgent
                (incorporates both feedbacks)
                      ↓
                 Analysis.md (v2)
                   ↓        ↓
            [Parallel Execution]
                  ... repeat ...

Final:         JudgeAgent
          (uses final analysis + all feedback)
```

### Key Design Principles

1. **Parallel by Default**: FactChecker always runs alongside Reviewer
2. **Veto Power**: Either agent can reject; both must approve to proceed
3. **Iteration Awareness**: Each iteration gets fresh fact-checking
4. **Template-Based Output**: Like Reviewer, fills pre-created JSON templates

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

**Available Tools** (same pattern as Analyst/Reviewer):

- `WebFetch` - Primary tool for verification (mandatory for all citations)
- `WebSearch` - Finding alternative sources when citations fail
- `Read` - Examining the analysis document
- `Edit` - Filling the pre-created fact_check.json template
- `TodoWrite` - Organizing complex verification tasks

**Tool Usage Pattern**:

- Pipeline pre-creates `fact_check.json` template with TODO sections
- FactChecker uses `Edit` to replace TODOs with findings
- No `Write` tool (follows existing agent patterns)

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
class FactCheckerContext(BaseContext):
    """Context for fact-checking operations."""
    
    # Explicit typed paths (following existing patterns)
    analysis_input_path: Path        # The analysis to verify
    fact_check_output_path: Path     # Where to write results
    
    # FactChecker-specific state
    max_webfetches: int = 20         # WebFetch allowance
    previous_fact_check_path: Path | None = None  # For iterations 2+
```

### Output Format

#### Conceptual Hierarchy

```text
Claim (any factual assertion)
├── Has Citation
│   ├── Verified True → No issue ✓
│   ├── Verified False → High severity (claim contradicts source)
│   └── Unverifiable → Medium/High severity (404=High, ambiguous=Medium)
└── No Citation
    ├── Statistical/Numerical → High severity (must have source)
    ├── Market/Competition data → High severity (must have source)
    └── General/Qualitative → Low severity (may be acceptable)
```

#### Key Definitions

- **Claim**: Any factual assertion in the analysis (e.g., "market worth $50B", "87% of users prefer X")
- **Citation**: A reference/link provided to back up a specific claim
- **Sourced Claim**: A claim that has an associated citation
- **Unsourced Claim**: A claim lacking any citation (automatic flag for review)

#### Verification States (for Sourced Claims)

- **Verified True**: Claim matches the cited source exactly or within acceptable margin
- **Verified False**: Claim contradicts or significantly misrepresents the source
- **Unverifiable**: Cannot verify due to 404, paywall, ambiguous source, etc.

#### JSON Structure

```json
{
  "recommendation": "reject",
  "recommendation_reason": "3 high-severity issues found: fabricated pilot data, 404 citations, and 40% error in market size claim",
  "timestamp": "2025-08-26T16:45:00Z",
  "analysis_path": "analyses/ai-tutoring-platform/iteration_1.md",
  "summary": {
    "total_claims": 25,
    "sourced_claims": 18,
    "unsourced_claims": 7,
    "verification_results": {
      "verified_true": 14,
      "verified_false": 3,
      "unverifiable": 1
    },
    "accuracy_score": 72.0,
    "citations_checked": 18,
    "citations_working": 17,
    "severity_counts": {
      "high": 3,
      "medium": 3,
      "low": 2
    }
  },
  "issues": [
    {
      "severity": "high",
      "type": "unsourced",
      "claim": "Our pilot with 500 students showed 73% improvement",
      "location": "Executive Summary, paragraph 2",
      "problem": "No source provided for pilot study claim",
      "evidence": "No citation found, appears to be fabricated",
      "recommendation": "Remove claim or provide verifiable source"
    },
    {
      "severity": "high",
      "type": "unverifiable",
      "claim": "AI tutoring doubles learning gains [2]",
      "location": "Market Opportunity, citation [2]",
      "problem": "Citation returns 404 error",
      "evidence": "https://example.com/study - Page not found",
      "recommendation": "Find alternative source or remove claim"
    },
    {
      "severity": "high",
      "type": "verified_false",
      "claim": "$4/month or $44/year [6]",
      "location": "Business Model, citation [6]",
      "problem": "Pricing contradicts source",
      "evidence": "Source shows $9/month, no annual pricing mentioned",
      "recommendation": "Correct to $9/month per source"
    },
    {
      "severity": "medium",
      "type": "unsourced",
      "claim": "87% of students use digital learning tools daily",
      "location": "Market Opportunity, paragraph 3",
      "problem": "Statistical claim lacks citation",
      "evidence": "No source provided for percentage",
      "recommendation": "Add citation or qualify as estimate"
    }
  ],
  "verification_details": {
    "webfetch_attempts": 10,
    "webfetch_successful": 7,
    "websearch_fallbacks": 2,
    "processing_time_seconds": 45.3
  },
  "top_priorities": [
    "Priority 1: Remove fabricated pilot study claim (High)",
    "Priority 2: Fix 404 citation [2] with working source (High)",
    "Priority 3: Correct pricing to match source [6] (High)"
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

### Pass/Fail Criteria

- **Reject**: Any high severity issue OR 3+ medium severity issues
- **Accept**: Only if no high AND <3 medium issues

### Severity Definitions (Aligned with Claim Hierarchy)

**High** (reject if ≥1):
- Claims with citations that are **Verified False** (contradicts source)
- **Unsourced** statistical/numerical claims
- **Unsourced** market size, TAM, or competition data  
- Claims with citations that are **Unverifiable** due to 404/403 errors
- Fabricated/invented data ("our pilot showed..." without any source)
- Significant numerical errors (>20% off from cited source)

**Medium** (reject if ≥3):
- Claims with citations that are **Unverifiable** due to ambiguity/paywall
- Moderate numerical errors (10-20% off from cited source)
- Outdated sourced data (>2 years) for fast-changing markets
- **Unsourced** company metrics that need specificity
- Missing critical context that changes claim meaning

**Low** (never reject alone):
- **Unsourced** general/qualitative claims (acceptable without citation)
- Claims **Verified True** but with minor discrepancies (<10%)
- Missing publication dates on otherwise valid citations
- Incomplete citation formatting (but link works)
- Typos that don't affect verification
```

### User Prompts

#### Initial Iteration (`config/prompts/agents/fact-checker/user/initial.md`)

```markdown
Fact-check the business analysis at: {{analysis_path}}

This is the FIRST iteration. Your task:
1. Read the analysis thoroughly
2. Extract EVERY factual claim (statistics, market sizes, company data)
3. Use WebFetch to verify ALL citations (max {{max_webfetches}} fetches)
4. For unsourced claims, use WebSearch to find verification
5. Calculate accuracy score and categorize issues by severity
6. Edit the fact-check report at: {{fact_check_output_path}}

Be especially vigilant for:
- Claims about "our pilot" or "our results" (often fabricated)
- Precise percentages without sources
- Suspiciously specific company metrics
- All citation URLs (test each with WebFetch)

Replace ALL TODO sections in the JSON template with your findings.
Your recommendation determines if the analysis needs revision.
```

#### Revision Iterations (`config/prompts/agents/fact-checker/user/revision.md`)

```markdown
Fact-check the REVISED business analysis at: {{analysis_path}}

This is iteration {{iteration}} of {{max_iterations}}.

Previous fact-check found issues at: {{previous_fact_check_path}}
The analyst has revised based on your previous feedback.

Your task:
1. Read the revised analysis
2. Verify that previous issues have been addressed
3. Check any NEW claims or citations added
4. Re-verify critical claims even if previously checked
5. Edit the fact-check report at: {{fact_check_output_path}}

Focus on:
- Were fabricated claims removed or sourced?
- Were broken citations fixed or replaced?
- Are numerical errors corrected?
- Any new issues introduced in revision?

Use up to {{max_webfetches}} WebFetch calls for thorough verification.
```

## Implementation Plan

### Files to Create/Modify

```text
NEW FILES:
├── src/agents/fact_checker.py                    # FactCheckerAgent implementation
├── config/prompts/agents/fact-checker/
│   ├── system.md                                 # Core fact-checking principles
│   └── user/
│       ├── initial.md                           # First iteration prompt
│       └── revision.md                          # Subsequent iterations prompt
├── config/templates/agents/fact-checker/
│   └── fact_check.json                          # Template with TODO sections
└── tests/unit/test_agents/test_fact_checker.py  # Unit tests

MODIFIED FILES:
├── src/core/types.py                            # Add FactCheckerContext
├── src/core/config.py                           # Add FactCheckerConfig
├── src/core/pipeline.py                         # Add parallel execution logic
├── src/core/run_analytics.py                    # Add fact-check metrics
├── src/cli.py                                   # Add --with-fact-checker flag
└── system-architecture.md                       # Document integration
```

### Core Implementation

```python
# src/agents/fact_checker.py

from typing import Any
from pathlib import Path
import json

from ..core.agent_base import BaseAgent
from ..core.types import Success, Error, AgentResult, FactCheckerContext
from ..core.config import FactCheckerConfig
from ..utils.file_operations import load_prompt_with_includes
from ..utils.json_validator import FactCheckValidator

class FactCheckerAgent(BaseAgent[FactCheckerConfig, FactCheckerContext]):
    """
    Fact-checking agent for verifying analysis accuracy.
    
    Responsibilities:
    - Verify all citations using WebFetch
    - Flag unsourced claims
    - Calculate accuracy metrics
    - Generate fact-check report
    """
    
    def __init__(self, config: FactCheckerConfig):
        super().__init__(config)
        # WebFetch is already in default allowed_tools
    
    @property
    @override
    def agent_name(self) -> str:
        return "FactChecker"
    
    @override
    async def process(
        self, 
        input_data: str = "",
        context: FactCheckerContext | None = None
    ) -> AgentResult:
        """
        Process analysis for fact-checking.
        
        Args:
            input_data: Unused (reads from context.analysis_input_path)
            context: FactCheckerContext with paths and metadata
            
        Returns:
            Success with fact-check results or Error
        """
        if context is None:
            raise ValueError("FactChecker requires context")
            
        try:
            # Load system prompt
            system_prompt = self.load_system_prompt()
            
            # Choose user prompt based on iteration
            if context.iteration == 1:
                user_template = load_prompt(
                    "agents/fact-checker/user/initial.md",
                    self.config.prompts_dir
                )
            else:
                user_template = load_prompt(
                    "agents/fact-checker/user/revision.md", 
                    self.config.prompts_dir
                )
                
            # Format user prompt
            user_prompt = user_template.format(
                analysis_path=str(context.analysis_input_path),
                fact_check_output_path=str(context.fact_check_output_path),
                iteration=context.iteration,
                max_iterations=self.config.max_iterations,
                max_webfetches=context.max_webfetches,
                previous_fact_check_path=str(context.previous_fact_check_path) 
                    if context.previous_fact_check_path else ""
            )
            
            # Configure and run fact-checking
            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                max_turns=self.config.max_turns,
                allowed_tools=self.config.get_allowed_tools(),
                permission_mode="acceptEdits"
            )
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)
                
                async for message in client.receive_response():
                    if self.interrupt_event.is_set():
                        await client.interrupt()
                        return Error(message="Fact-checking interrupted")
                        
                    if context.run_analytics:
                        context.run_analytics.track_message(
                            message, "fact_checker", context.iteration
                        )
                        
                    if isinstance(message, ResultMessage):
                        break
            
            # Parse and validate output
            fact_check_data = self._parse_fact_check_output(
                context.fact_check_output_path
            )
            
            # Log metrics
            self._log_metrics(fact_check_data, context)
            
            # Check if fact-check file was edited
            if context.fact_check_output_path.exists():
                # Validate and potentially fix the output
                fact_check_data = self._validate_fact_check(
                    context.fact_check_output_path
                )
                if fact_check_data:
                    return Success()
                else:
                    return Error(message="Invalid fact-check output")
            else:
                return Error(message="FactChecker failed to edit output file")
            
        except Exception as e:
            return Error(message=f"Fact-checking failed: {str(e)}")
    
    def _validate_fact_check(self, fact_check_path: Path) -> dict | None:
        """Validate and potentially fix fact-check JSON."""
        try:
            with open(fact_check_path, "r") as f:
                fact_check_data = json.load(f)
                
            validator = FactCheckValidator()
            is_valid, error_msg = validator.validate(fact_check_data)
            
            if not is_valid:
                logger.warning(f"Fact-check validation failed: {error_msg}")
                fact_check_data = validator.fix_common_issues(fact_check_data)
                is_valid, _ = validator.validate(fact_check_data)
                
                if is_valid:
                    with open(fact_check_path, "w") as f:
                        json.dump(fact_check_data, f, indent=2)
                else:
                    return None
                    
            return fact_check_data
            
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read fact-check file: {e}")
            return None
```

### Pipeline Integration

#### Configuration Addition

```python
# src/core/config.py

@dataclass
class FactCheckerConfig(BaseAgentConfig):
    """Configuration for the FactChecker agent."""
    
    max_iterations: int = 3  # Same as reviewer
    max_webfetches: int = 20  # Higher limit for thorough verification
    strictness: str = "normal"  # normal, strict, lenient
    
    # Default tools include WebFetch for verification
    allowed_tools: list[str] = field(
        default_factory=lambda: [
            "WebFetch", "WebSearch", "Read", "Edit", "TodoWrite"
        ]
    )
```

#### Context Addition

```python
# src/core/types.py

@dataclass
class FactCheckerContext(BaseContext):
    """Context for fact-checking operations."""
    
    # Explicit typed paths
    analysis_input_path: Path = Path("analysis.md")
    fact_check_output_path: Path = Path("fact_check.json")
    
    # FactChecker-specific state
    max_webfetches: int = 20
    previous_fact_check_path: Path | None = None
```

#### Pipeline Modes Update

```python
# src/core/pipeline.py modifications

class PipelineMode(Enum):
    ANALYZE = "analyze"  # Analyst only
    ANALYZE_AND_REVIEW = "analyze_and_review"  # Analyst + Reviewer
    ANALYZE_REVIEW_WITH_FACT_CHECK = "analyze_review_with_fact_check"  # NEW: Analyst + (Reviewer & FactChecker in parallel)
    ANALYZE_REVIEW_AND_JUDGE = "analyze_review_and_judge"  # Future: + Judge
    FULL_EVALUATION = "full_evaluation"  # Future: All agents

class AnalysisPipeline:
    def __init__(self, ..., fact_checker_config: FactCheckerConfig | None = None):
        # ... existing init ...
        self.fact_checker_config = fact_checker_config
        self.with_fact_checking = fact_checker_config is not None
        
    async def _analyze_review_with_fact_check(self) -> PipelineResult:
        """Run analyst followed by parallel reviewer and fact-checker."""
        analyst = AnalystAgent(self.analyst_config)
        reviewer = ReviewerAgent(self.reviewer_config)
        fact_checker = FactCheckerAgent(self.fact_checker_config) if self.fact_checker_config else None
        
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            
            # Run analyst
            if not await self._run_analyst(analyst):
                return self._build_result(error="Analyst failed")
                
            # Skip review/fact-check on last iteration
            if self.iteration_count >= self.max_iterations:
                break
                
            # Run reviewer and fact-checker in parallel
            should_continue = await self._run_parallel_review_and_fact_check(
                reviewer, fact_checker
            )
            if not should_continue:
                break
                
        return self._build_result()
        
    async def _run_parallel_review_and_fact_check(
        self, 
        reviewer: ReviewerAgent,
        fact_checker: FactCheckerAgent | None
    ) -> bool:
        """Run reviewer and fact-checker in parallel."""
        
        # Create feedback file from template
        feedback_file = (
            self.iterations_dir / 
            f"reviewer_feedback_iteration_{self.iteration_count}.json"
        )
        create_file_from_template(
            self.system_config.template_dir / "agents" / "reviewer" / "feedback.json",
            feedback_file
        )
        
        # Create contexts
        reviewer_context = ReviewerContext(
            analysis_input_path=self.current_analysis_file,
            feedback_output_path=feedback_file,
            iteration=self.iteration_count,
            run_analytics=self.analytics
        )
        
        if fact_checker:
            # Create fact-check file from template
            fact_check_file = (
                self.iterations_dir / 
                f"fact_check_iteration_{self.iteration_count}.json"
            )
            create_file_from_template(
                self.system_config.template_dir / "agents" / "fact-checker" / "fact_check.json",
                fact_check_file
            )
            
            # Determine previous fact-check for iterations 2+
            previous_fact_check = None
            if self.iteration_count > 1:
                previous_fact_check = (
                    self.iterations_dir / 
                    f"fact_check_iteration_{self.iteration_count - 1}.json"
                )
                
            fact_checker_context = FactCheckerContext(
                analysis_input_path=self.current_analysis_file,
                fact_check_output_path=fact_check_file,
                iteration=self.iteration_count,
                max_webfetches=self.fact_checker_config.max_webfetches,
                previous_fact_check_path=previous_fact_check,
                run_analytics=self.analytics
            )
            
            # Run both in parallel
            import asyncio
            review_result, fact_check_result = await asyncio.gather(
                reviewer.process("", reviewer_context),
                fact_checker.process("", fact_checker_context)
            )
        else:
            # Just run reviewer
            review_result = await reviewer.process("", reviewer_context)
            fact_check_result = Success()
            
        # Process results - both must approve
        return self._process_dual_feedback(
            review_result, 
            fact_check_result,
            feedback_file,
            fact_check_file if fact_checker else None
        )
        
    def _process_dual_feedback(
        self,
        review_result: AgentResult,
        fact_check_result: AgentResult,
        feedback_file: Path,
        fact_check_file: Path | None
    ) -> bool:
        """Process feedback from both agents."""
        
        # Check for errors
        match (review_result, fact_check_result):
            case (Error(message=msg), _):
                logger.error(f"Reviewer failed: {msg}")
                return False
            case (_, Error(message=msg)):
                logger.error(f"FactChecker failed: {msg}")
                return False
            case (Success(), Success()):
                pass
                
        # Parse reviewer feedback
        try:
            with open(feedback_file, "r") as f:
                feedback = json.load(f)
            reviewer_recommendation = feedback.get("recommendation", "approve")
        except (json.JSONDecodeError, OSError):
            logger.error("Failed to parse reviewer feedback")
            return False
            
        # Parse fact-check if present
        fact_checker_recommendation = "approve"
        if fact_check_file and fact_check_file.exists():
            try:
                with open(fact_check_file, "r") as f:
                    fact_check = json.load(f)
                fact_checker_recommendation = fact_check.get("recommendation", "approve")
            except (json.JSONDecodeError, OSError):
                logger.error("Failed to parse fact-check")
                return False
                
        # Both must approve to stop iterating
        if reviewer_recommendation == "approve" and fact_checker_recommendation == "approve":
            logger.info(f"✅ Both agents approved at iteration {self.iteration_count}")
            return False  # Stop iterating
        else:
            reasons = []
            if reviewer_recommendation != "approve":
                reasons.append("Reviewer requests revision")
            if fact_checker_recommendation != "approve":
                reasons.append("FactChecker found accuracy issues")
            logger.info(f"🔄 Revision needed: {', '.join(reasons)}")
            
            # Save feedback references for next iteration
            self.last_feedback_file = feedback_file
            self.last_fact_check_file = fact_check_file
            
            return True  # Continue iterating
```

### Template Structure

```json
// config/templates/agents/fact-checker/fact_check.json
{
  "recommendation": "[TODO: Choose 'reject' or 'accept' based on severity of issues found]",
  "recommendation_reason": "[TODO: Explain your recommendation in 1-2 sentences]",
  
  "summary": {
    "total_claims": "[TODO: Total number of factual claims found]",
    "sourced_claims": "[TODO: Claims that have citations]",
    "unsourced_claims": "[TODO: Claims lacking citations]",
    "verification_results": {
      "verified_true": "[TODO: Claims verified as accurate]",
      "verified_false": "[TODO: Claims that contradict sources]",
      "unverifiable": "[TODO: Claims that couldn't be verified]"
    },
    "accuracy_score": "[TODO: Percentage of verified claims (0-100)]",
    "citations_checked": "[TODO: Number of citations tested]",
    "citations_working": "[TODO: Number of accessible citations]",
    "severity_counts": {
      "high": "[TODO: Count of high severity issues]",
      "medium": "[TODO: Count of medium issues]",
      "low": "[TODO: Count of low issues]"
    }
  },
  
  "issues": [
    {
      "severity": "[TODO: 'high', 'medium', or 'low']",
      "type": "[TODO: 'verified_false', 'unverifiable', 'unsourced', 'error', etc.]",
      "claim": "[TODO: The specific claim or citation in question]",
      "location": "[TODO: Section or line number in analysis]",
      "problem": "[TODO: What's wrong with this claim/citation]",
      "evidence": "[TODO: What we found when verifying (if applicable)]",
      "recommendation": "[TODO: Specific fix needed]"
    },
    "[TODO: Add all issues found, ordered by severity (high → medium → low)]"
  ],
  
  "verification_details": {
    "webfetch_attempts": "[TODO: Number of WebFetch calls made]",
    "webfetch_successful": "[TODO: Number of successful fetches]",
    "websearch_fallbacks": "[TODO: Number of WebSearch attempts]"
  },
  
  "top_priorities": [
    "[TODO: Priority 1 - Most critical fix from issues above]",
    "[TODO: Priority 2 - Second most important fix]",
    "[TODO: Priority 3 - Third priority fix]"
  ]
}
```

## Success Metrics

### Primary Metrics

- **Citation Accuracy Rate**: Target >90% valid citations
- **False Claim Detection**: Catch 100% of fabricated claims
- **Processing Time**: 5-10 minutes per iteration (realistic for thorough verification)

### Secondary Metrics

- WebFetch success rate
- Unsourced claims identified
- Alternative sources found

## Testing Strategy

### Unit Test Implementation

```python
# tests/unit/test_agents/test_fact_checker.py

class TestFactCheckerAgent:
    """Unit tests for FactCheckerAgent."""
    
    async def test_process_success(self, mock_sdk_client):
        """Test successful fact-checking."""
        # Test that agent correctly processes analysis
        # and fills fact_check.json template
        
    async def test_iteration_handling(self, mock_sdk_client):
        """Test handling of multiple iterations."""
        # Verify agent uses correct prompts for
        # initial vs revision iterations
        
    async def test_severity_detection(self, mock_sdk_client):
        """Test detection of different severity issues."""
        # Ensure critical issues trigger rejection
        
    async def test_parallel_execution(self):
        """Test parallel execution with reviewer."""
        # Verify both agents can run concurrently
```

### Integration Test Cases

1. **Fabrication Detection**
   - **Setup**: Create analysis with "Our pilot showed 73% improvement"
   - **Execution**: Run fact-checker on the analysis
   - **Validation**: Assert recommendation="reject", severity="critical"

2. **404 Citation Detection**
   - **Setup**: Analysis with broken Harvard.edu citation
   - **Execution**: FactChecker attempts WebFetch
   - **Validation**: Assert 404 detected, marked as "high" severity

3. **Numerical Accuracy Check**
   - **Setup**: Analysis claims "$50B market" but source says "$30B"
   - **Execution**: FactChecker fetches source and compares
   - **Validation**: Assert 40% error detected as "high" severity

4. **Parallel Execution Test**
   - **Setup**: Analysis needing both review and fact-check
   - **Execution**: Run pipeline with both agents
   - **Validation**: Assert both complete within timeout, results combined

### A/B Testing

Run parallel on same analyses:

- Control: Analyst + Reviewer only
- Test: Analyst + Reviewer + FactChecker

Measure:

- Citation accuracy improvement
- False claims caught
- User trust metrics

## Implementation Task Plan

### Phase 0: Pre-Implementation Review (Day 1)

- [ ] **Review existing pipeline.py complexity**
  - [ ] Identify opportunities to simplify before adding FactChecker
  - [ ] Consider extracting parallel execution logic to separate method
  - [ ] Review if current iteration logic needs refactoring

- [ ] **Audit agent base patterns**
  - [ ] Ensure BaseAgent can handle parallel execution cleanly
  - [ ] Check if interrupt handling works for parallel agents
  - [ ] Verify RunAnalytics can track parallel agents properly

- [ ] **Simplify existing validation logic**
  - [ ] Consider creating shared validator base class
  - [ ] Review if FeedbackValidator pattern can be reused

### Phase 1: Core Implementation (Days 2-3)

- [ ] **Create FactCheckerConfig and Context**
  - [ ] Add to src/core/config.py
  - [ ] Add to src/core/types.py
  - [ ] Follow existing patterns exactly

- [ ] **Implement FactCheckerAgent**
  - [ ] Create src/agents/fact_checker.py
  - [ ] Implement process() method with iteration awareness
  - [ ] Add WebFetch verification logic

- [ ] **Create prompts and templates**
  - [ ] config/prompts/agents/fact-checker/system.md
  - [ ] config/prompts/agents/fact-checker/user/initial.md
  - [ ] config/prompts/agents/fact-checker/user/revision.md
  - [ ] config/templates/agents/fact-checker/fact_check.json

### Phase 2: Pipeline Integration (Days 4-5)

- [ ] **Add parallel execution to pipeline.py**
  - [ ] Implement _run_parallel_review_and_fact_check()
  - [ ] Add ANALYZE_REVIEW_WITH_FACT_CHECK mode
  - [ ] Handle dual feedback processing

- [ ] **Update CLI with clear agent-specific flags**
  - [ ] Add --with-fact-checker flag
  - [ ] Add --fact-checker-max-webfetches flag
  - [ ] Update help text to clarify which agent each flag affects

- [ ] **Integrate with RunAnalytics**
  - [ ] Add fact_check metrics tracking
  - [ ] Update iteration_metrics structure
  - [ ] Ensure parallel agent tracking works

### Phase 3: Testing & Validation (Days 6-7)

- [ ] **Unit tests**
  - [ ] Test FactCheckerAgent in isolation
  - [ ] Test parallel execution with mocked agents
  - [ ] Test severity detection logic

- [ ] **Integration tests**
  - [ ] Test full pipeline with fact-checker enabled
  - [ ] Verify both agents complete within timeout
  - [ ] Test iteration handling with dual feedback

- [ ] **Real-world validation**
  - [ ] Run on existing analyses with known citation issues
  - [ ] Verify 404 detection works
  - [ ] Test fabrication detection

### Phase 4: Documentation & Polish (Day 8)

- [ ] **Update documentation**
  - [ ] Update system-architecture.md
  - [ ] Add fact-checker section to README
  - [ ] Document new CLI flags clearly

- [ ] **Performance optimization**
  - [ ] Profile parallel execution overhead
  - [ ] Optimize WebFetch caching if needed
  - [ ] Tune timeout values

## Open Questions

1. **Should fact-checker be able to edit?**
   - Pro: Could fix minor issues automatically
   - Con: Maintains separation of concerns
   - Recommendation: Read-only for v1
   - **Answer**: No, fact-checker only submits their assessment json file

2. **Threshold for passing?**
   - Option A: Any critical issue = fail
   - Option B: Accuracy score threshold (e.g., >80%)
   - Recommendation: Critical issues = mandatory fix
   - **Answer**: Any high or medium severity issue = fail

3. **WebFetch rate limits?**
   - Need to test with high citation counts
   - May need queuing or caching strategy

   **Answer**: We give a WebFetch allowance to the fact-checker (max_webfetches=20), like we do for WebSearches with the analyst agent. This is configurable via FactCheckerConfig.

### CLI Integration

```python
# src/cli.py additions

def create_argument_parser():
    # ... existing args ...
    
    parser.add_argument(
        "--with-fact-checker",
        action="store_true",
        help="Enable parallel fact-checking with reviewer (adds 5-10min per iteration)"
    )
    
    parser.add_argument(
        "--fact-checker-max-webfetches",
        type=int,
        default=20,
        help="Maximum WebFetch calls for FactChecker agent (default: 20)"
    )
    
    parser.add_argument(
        "--fact-checker-strictness",
        choices=["lenient", "normal", "strict"],
        default="normal",
        help="FactChecker agent strictness level (affects pass/fail thresholds)"
    )
    
    # Note: Consider also updating existing flags for clarity:
    # --analyst-max-websearches (instead of --max-websearches)
    # --analyst-prompt (already named correctly)
    # This makes it crystal clear which agent each constraint applies to

# In main():
if args.with_fact_checker:
    fact_checker_config = FactCheckerConfig(
        max_webfetches=args.fact_checker_max_webfetches,
        strictness=args.fact_checker_strictness,
        prompts_dir=prompts_dir
    )
    # FactChecker always runs alongside Reviewer, never alone
    pipeline_mode = PipelineMode.ANALYZE_REVIEW_WITH_FACT_CHECK
else:
    fact_checker_config = None
    # Use existing mode logic
```

### Analytics Integration

```python
# src/core/run_analytics.py additions

class RunAnalytics:
    def __init__(self, ...):
        # ... existing init ...
        self.fact_check_count: int = 0
        self.fact_check_accuracy: float = 0.0
        self.fact_check_issues: dict[str, int] = {}
        
    def track_fact_check(self, fact_check_data: dict, iteration: int):
        """Track fact-checking metrics."""
        self.fact_check_count += 1
        
        summary = fact_check_data.get("summary", {})
        self.fact_check_accuracy = summary.get("accuracy_score", 0.0)
        
        # Track severity counts
        severity_counts = summary.get("severity_counts", {})
        for severity, count in severity_counts.items():
            key = f"fact_check_{severity}_issues"
            self.fact_check_issues[key] = count
            
        # Log to iteration metrics
        if iteration not in self.iteration_metrics:
            self.iteration_metrics[iteration] = {}
        self.iteration_metrics[iteration]["fact_check"] = {
            "accuracy": self.fact_check_accuracy,
            "issues": self.fact_check_issues,
            "recommendation": fact_check_data.get("recommendation")
        }
```

## Related Documents

- `session-logs/2025-08-26-citation-analysis-findings.md` - Evidence for this agent
- `config/prompts/experimental/analyst/citation-strict.md` - Current mitigation attempt
- `src/agents/reviewer.py` - Parallel agent pattern reference

---

*Draft specification v1 - 2025-08-26*
