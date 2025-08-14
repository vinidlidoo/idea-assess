# Analyst Prompt Improvement Areas

## Context

This document tracks areas for improvement identified in the analyst_v1.md prompt based on reviewing generated analyses. We'll use this to guide creation of analyst_v2.md.

## Existing Analyses Reviewed

- ai-powered-fitness-app-for-seniors
- ai-powered-recipe-generator  
- smart-home-automation-platform
- sustainable-fashion-marketplace

## Areas for Improvement

### 1. Specificity and Evidence

**Current Issue:**

- Numbers often lack sources or feel estimated (e.g., "approximately $1.2 billion", "roughly 30%")
- Some statistics appear generic or rounded suspiciously (e.g., "73% willing to pay premium")
- Market sizes sometimes lack clear methodology or breakdown

**Desired Improvement:**

- Cite specific sources when possible (reports, studies, companies)
- Show calculation methodology for TAM estimates
- Use ranges when uncertain rather than false precision
- Include year and source for all statistics

### 2. Market Data and Quantification

**Current Issue:**

- CAGRs and projections feel formulaic (always seem to be 12-22%)
- Market sizes are given but not broken down by segment relevance
- Geographic breakdowns are vague ("North America leads with 40%")

**Desired Improvement:**

- Break down TAM → SAM → SOM with clear reasoning
- Explain why specific growth rates are expected
- Connect market data directly to the specific solution
- Show market penetration assumptions

### 3. Competitive Analysis Depth

**Current Issue:**

- Competitors mentioned but differentiation is generic
- Missing specific feature comparisons or pricing details
- No mention of indirect competitors or substitutes
- Doesn't explain why competitors haven't solved this problem

**Desired Improvement:**

- Include specific competitor metrics (users, revenue, funding)
- Create clear feature comparison matrix
- Address why incumbents can't/won't pivot to this solution
- Include both direct and indirect competition

### 4. Actionable Next Steps

**Current Issue:**

- Next steps are too generic (e.g., "validate demand through landing page")
- Missing specific metrics/targets (e.g., "1,000 signups" but no timeline)
- Steps don't build on each other strategically
- No cost estimates or resource requirements

**Desired Improvement:**

- Include specific timelines and success metrics for each step
- Estimate costs and resources needed
- Show dependencies between steps
- Include go/no-go decision criteria

### 5. Business Model Clarity

**Current Issue:**

- Pricing seems arbitrary (\$9.99, \$19.99 without justification)
- Unit economics are vague ("projected break-even at 50,000 subscribers")
- Missing customer acquisition cost vs lifetime value analysis
- Revenue projections lack supporting assumptions

**Desired Improvement:**

- Justify pricing based on competitor analysis or value provided
- Show detailed unit economics with assumptions
- Include CAC/LTV ratios with industry benchmarks
- Provide month-by-month projection for first year

### 6. Executive Summary Impact

**Current Issue:**

- Often reads like a template with buzzwords
- Doesn't clearly state the "why now" for this opportunity
- Information feels dated - analyses could have been written 3-5 years ago
- Problem statement could be more compelling with better data

**Desired Improvement:**

- Lead with a shocking statistic or trend that makes the opportunity obvious
- Clearly articulate what has changed to make this viable now
- Include one killer metric that captures the opportunity size

### 7. Risk Assessment Reality

**Current Issue:**

- Risks feel generic (technology adoption, competition, regulatory)
- Mitigations are often hand-wavy without specific tactics
- Missing execution risks specific to the idea

**Desired Improvement:**

- Include risks specific to this exact business model
- Provide concrete mitigation strategies with examples
- Address the "why hasn't someone done this already" question
- Include timeline/runway risks

## Testing Criteria

How we'll know v2 is better than v1:

- [ ] More specific market size estimates with sources
- [ ] Named competitors with clear differentiation
- [ ] Concrete, actionable next steps (not generic)
- [ ] Clear revenue model with pricing hints
- [ ] Evidence-based claims (not speculation)
- [ ] Compelling "why now" narrative
- [ ] Specific, measurable success metrics

## Implementation Priorities for V2

### Must Have (Core 1000 words + References)

- Add year/recency to all key statistics (2024/2025 data)
- Include 1-2 specific competitor metrics (users, funding, valuation)
- Make "why now" explicit in executive summary with recent trend
- Add concrete timelines to next steps (30/60/90 day milestones)
- Include at least one "killer metric" that makes opportunity obvious
- **References section** (additional ~150-200 words) with numbered citations

### Nice to Have (if space permits)

- Brief inline source citations (e.g., "[1]" linking to references)
- One specific pricing comparison to competitors
- TAM → SAM → SOM breakdown (even if brief)
- Confidence levels for projections (high/medium/low)

### Defer to Future Phases

- Supplementary research document with detailed analysis
- Full feature comparison matrices
- Month-by-month financial projections
- Extended competitive analysis with indirect competitors

## Notes

- Focus on improvements that will matter for the Judge agent evaluation
- Word count: 1000 words for main analysis + 150-200 for references
- Ensure improvements don't make the agent too verbose
- Prioritize recency and specificity over comprehensiveness
- References should include mix of: industry reports, company data, recent news
