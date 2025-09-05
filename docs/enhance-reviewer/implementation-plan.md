# Enhanced Reviewer Implementation Plan

**Date**: 2025-09-04  
**Objective**: Add web verification capabilities to ReviewerAgent to improve feedback quality  

## Background

Analysis of the ReviewBot case study reveals areas where the current reviewer should push harder:

### Key Weaknesses in Current Reviews

1. **Unrealistic Startup Claims** - Accepts statements like "50M+ PR interactions" without questioning how a startup could obtain this data
2. **Inconsistent Metrics** - Doesn't catch conflicting numbers (4.2% vs <5% false positives)
3. **Unsupported Projections** - Doesn't challenge aggressive growth claims ($1.5M ARR in 12 months)
4. **Incomplete Competitive Analysis** - Misses obvious competitors (Codacy, CodeClimate)
5. **Weak Evidence** - Accepts vague claims like "70% reduction" without demanding specifics
6. **Technical Feasibility Gaps** - Doesn't probe HOW the solution actually works, especially for pre-product startups

## Scope & Constraints

### What Enhanced Reviewer WILL Do

- **Contextualize Claims**: Use WebSearch to verify if statistics align with industry benchmarks and comparable companies
- **Challenge Unrealistic Assumptions**: Question claims that seem implausible for a startup's stage (e.g., massive datasets, patents, rapid scaling)
- **Identify Missing Competitors**: Search for competitors not mentioned in the analysis
- **Cross-check Internal Consistency**: Identify conflicting data points within the analysis itself
- **Demand Evidence**: Push for specific pilot data, customer testimonials, technical implementation details

### What Enhanced Reviewer WON'T Do (FactChecker's Domain)

- Line-by-line citation verification (FactChecker's role)
- Exhaustive source validation (FactChecker's role)  
- Veto power over iterations (FactChecker only)
- Focus solely on accuracy (Reviewer balances multiple criteria)

### Key Distinction

- **Reviewer**: Strategic verification to improve argument quality and realism
- **FactChecker**: Systematic verification to ensure citation accuracy

## Technical Implementation

### 1. Configuration Changes

```python
# src/core/config.py
@dataclass
class ReviewerConfig(BaseAgentConfig):
    max_iterations: int = 3
    strictness: str = "normal"
    
    # NEW: Web verification capabilities
    max_websearches: int = 8  # Match analyst limit
    
    # Updated allowed tools
    allowed_tools: list[str] = field(
        default_factory=lambda: ["WebSearch", "WebFetch", "TodoWrite"]
    )
```

### 2. Verification Strategy

The reviewer will prioritize verification of:

1. **Market Size Claims** (TAM, growth rates, industry statistics)
2. **Competitor Information** (pricing, right competitor set, features, market position)
3. **Technical Feasibility** (implementation approaches, timelines - especially for pre-product startups)
4. **Financial Projections** (CAC, LTV, burn rate, profitability)
5. **Realistic Capability Claims** (what's achievable at the startup's current stage)

### 3. Prompt Updates

The enhanced reviewer will maintain the existing template-based approach while adding strategic verification capabilities. Key principles:

- **Preserve TODO-based templates** - The feedback.json template structure stays mostly the same
- **File-based workflow** - Pipeline creates templates with TODOs, agent replaces them
- **Clear iteration logic** - Maintain existing reject/accept criteria
- **Tool documentation** - Add new tools to tools_system.md

#### Updates for Analyst Agent

Add to `config/prompts/agents/analyst/system.md` in the "Core Principles" section:

```markdown
## Core Principles

1. **10x not 10%** - Why is this radically better?
2. **Why now** - What changed to make this possible today?
3. **Data beats narrative** - Specific numbers over vague claims
4. **Intellectual honesty** - Acknowledge real challenges
5. **Evidence required** - Citations [1], [2] only for verifiable claims
6. **Startup realism** - Can a pre-product startup actually achieve these claims?

## Realism Checklist

Before finalizing, verify:
- [ ] Claims match startup stage (no "50M users" for pre-launch)
- [ ] Growth projections align with benchmarks (18-24 months to $1M ARR typical)
- [ ] Technical capabilities explained with HOW, not just what
- [ ] Comprehensive competitor landscape (search for who you might have missed)
- [ ] Resource requirements match available funding/team
```

#### File: `config/prompts/agents/reviewer/tools_system.md` (Replace Entirely)

```markdown
# Tools and Capabilities

## Available Tools

As an enhanced reviewer agent, you have strategic verification tools:

### Read
Always available for:
- Reading analysis files to review their content
- Understanding the complete document structure
- MUST be used before any Edit operation
- Essential for providing informed feedback

### Edit/MultiEdit
Always available for:
- Editing feedback template files
- Replacing TODO sections with your review
- Use single Edit operation for complete feedback
- Never edit without reading first

### WebSearch (NEW - Enhanced Reviewer)
Limited to 8 searches per review for:
- Checking if market size claims align with industry benchmarks
- Finding major competitors not mentioned in the analysis
- Verifying growth rate comparisons with similar companies
- Validating if technical claims are realistic for startup stage

### WebFetch (NEW - Enhanced Reviewer)
Limited use for:
- Spot-checking if critical citations support major claims
- Verifying competitor pricing/features when central to argument
- Checking recent market reports cited as primary evidence

### TodoWrite (NEW - Enhanced Reviewer)
Available for:
- Creating verification task lists
- Tracking which claims have been checked
- Organizing review workflow

## Strategic Verification Guidelines

With your {max_websearches} web searches, prioritize:
1. **Startup realism** - Claims that seem impossible for the stated stage
2. **Missing competitors** - Search "competitors to [solution]" once
3. **Market benchmarks** - TAM/growth rates vs industry reports
4. **Technical feasibility** - Can a startup actually build this?

You are NOT the FactChecker:
- Don't verify every citation (FactChecker's job)
- Focus on strategic gaps that affect credibility
- Use searches to strengthen feedback quality
```

#### File: `config/prompts/agents/reviewer/system.md` (Additions Only)

Add after "## Core Review Principles" section:

```markdown
## Enhanced Review with Verification (v3)

You have access to WebSearch ({max_websearches} max) and WebFetch to verify key claims strategically:

### When to Use Verification
- **Unrealistic startup claims**: "We have 50M users" (pre-launch startup)
- **Missing competitors**: Analysis only mentions 2 competitors in crowded market
- **Extreme projections**: "$0 to $10M in 6 months" without precedent
- **Technical impossibilities**: "Our AI is 100% accurate"

### When NOT to Verify
- Citation accuracy (FactChecker's role)
- Minor statistics that don't affect core argument
- Well-known facts or reasonable approximations
- Claims already well-supported in the document

### Verification Workflow
1. Identify 3-5 most critical/suspicious claims
2. Use WebSearch to check against industry norms
3. Include findings in your feedback with specifics
4. Don't exceed 8 searches - be selective

Example good verification:
"Searched 'B2B SaaS growth benchmarks 2024' - typical is $1M ARR in 18-24 months, not 6 months as claimed"

Example bad verification:
"Checked if [5] really links to TechCrunch" (that's FactChecker's job)
```

#### Feedback Template Enhancement

Going with Option 1 - add verification_notes field to feedback.json:

```json
{
  "overall_assessment": "[TODO: 2-3 sentence assessment]",
  "strengths": [
    "[TODO: List 2-4 specific strong points. Examples:",
    "- Clear problem articulation with specific user pain",
    "- Strong market timing with 2024-2025 evidence]"
  ],
  "critical_issues": [
    {
      "section": "[TODO: Section name]",
      "issue": "[TODO: What's wrong. Example: 'Claims 50M dataset without explaining data source']",
      "suggestion": "[TODO: Specific fix. Example: 'Explain data sourcing or adjust to realistic numbers']"
    }
  ],
  "improvements": [...],
  "minor_suggestions": [...],
  "iteration_recommendation": "[TODO: 'approve' or 'reject']",
  "iteration_reason": "[TODO: 1-2 sentence explanation]",
  "verification_notes": "[TODO: Key findings from web searches. Example: 'WebSearch for competitors found Codacy, CodeClimate not mentioned. Industry benchmarks show 18-24 months typical to $1M ARR.']"
}

#### User Prompt Additions

Add to existing review user prompt (`config/prompts/agents/reviewer/user/review.md`):

```markdown
## Verification Priorities for This Review

Given your {max_websearches} search limit, prioritize verifying:
1. The most ambitious/unrealistic claim
2. Completeness of competitive landscape (one search)
3. Market size if it seems inflated
4. Technical feasibility if claims seem impossible
5. Growth benchmarks if projections are extreme

Remember: You're enhancing review quality, not fact-checking every statement.
```

### 4. Code Changes Required

No architectural changes - just configuration updates:

1. **ReviewerConfig** - Add `max_websearches` field and tools
2. **ReviewerAgent** - Already handles tools via base class
3. **Pipeline** - No changes needed, already passes tools through
4. **User prompt formatting** - Add `max_websearches` variable substitution

## Testing Strategy

### Unit Tests

Similar to FactChecker tests - mock the web tools and test config changes:

1. Test ReviewerConfig with `max_websearches` field
2. Mock WebSearch/WebFetch responses
3. Verify tools are passed correctly

### Integration Test

Use `test_pipeline_live.py` approach:

1. Replace `tests/fixtures/analyses/ai-tutoring-platform.md` with ReviewBot's iteration_1.md
2. Run `test_parallel_reviewer_factchecker` with enhanced reviewer
3. Verify enhanced reviewer catches the unrealistic claims
4. Check that verification_notes field is populated

## Implementation Steps

### Phase 1: Basic Integration

1. Add `max_websearches: int = 8` to ReviewerConfig
2. Update `allowed_tools` list
3. Update reviewer prompts (system.md, tools_system.md)
4. Test with modified fixture

### Phase 2: Polish

1. Add verification_notes to feedback template
2. Update user prompt with {max_websearches} variable
3. Ensure analyst addresses realism feedback

## Success Criteria

1. **Catches Major Issues**: Identifies unrealistic startup claims in ReviewBot
2. **Efficient Verification**: Uses ≤8 searches effectively
3. **Actionable Feedback**: Provides specific, verifiable improvement suggestions
4. **Performance**: Reviews complete within reasonable time (~5 minutes)

## Example Enhanced Feedback

Using the current template structure with Option 1 enhancement:

<!-- FEEDBACK: let's bake examples like this in the template. I think it will help the reviewer -->
```json
{
  "overall_assessment": "Analysis has strong narrative but claims capabilities unrealistic for pre-product startup. Missing major competitors.",
  "strengths": [
    "Clear problem articulation",
    "Good market timing explanation"
  ],
  "critical_issues": [
    {
      "section": "The Solution",
      "issue": "Claims 'graph neural networks trained on 50M+ PR interactions' without explaining data access",
      "suggestion": "Either explain how you'll obtain this data or adjust to realistic capabilities"
    },
    {
      "issue": "Incomplete competitive landscape",
      "details": "Missing major competitors like Codacy ($15M raised), CodeClimate (1M+ repos), PullRequest",
      "verification": "WebSearch for 'AI code review tools' identified 5+ direct competitors not mentioned",
      "suggestion": "Add comprehensive competitor analysis including Codacy, CodeClimate, PullRequest, Codefresh, CodeRabbit"
    },
    {
      "issue": "Growth projections misaligned with industry benchmarks",
      "details": "$0 to $1.5M ARR in 12 months requires 125 paying teams from day one",
      "verification": "WebSearch shows comparable B2B dev tools take 18-24 months to reach $1M ARR (e.g., Linear, Vercel)",
      "suggestion": "Provide specific go-to-market strategy or adjust to realistic 18-24 month timeline for $1M ARR"
    },
    {
      "issue": "Internal inconsistency in metrics",
      "details": "Claims both '4.2% false positive rate' and '<5% false positives' for same metric",
      "verification": "Internal document check - conflicting numbers in paragraphs 3 and 7",
      "suggestion": "Use consistent metric throughout; explain methodology for measuring false positives"
    }
  ]
}
```

## Risks & Mitigations

### Risk: Over-verification slows reviews

**Mitigation**: Strict 8-search limit, prioritize high-impact claims

### Risk: Conflicts with FactChecker role

**Mitigation**: Clear delineation - Reviewer for strategic verification, FactChecker for systematic accuracy

### Risk: False positives from web search

**Mitigation**: Use verification to raise questions, not make definitive judgments

## Next Steps

1. [ ] Update ReviewerConfig with `max_websearches` field
2. [ ] Update reviewer prompts (system.md, tools_system.md, user/review.md)  
3. [ ] Add verification_notes to feedback.json template
4. [ ] Replace test fixture with ReviewBot iteration_1
5. [ ] Run integration test to verify enhanced feedback quality

---

*This plan focuses on strategic verification to improve review quality while maintaining clear separation from FactChecker responsibilities.*
