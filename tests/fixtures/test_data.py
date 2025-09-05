"""Centralized test data for consistency across all tests."""

from __future__ import annotations

from pathlib import Path


# Test business ideas with various characteristics
TEST_IDEAS = {
    "simple": "AI fitness app",
    "complex": "Blockchain-based supply chain optimization platform for pharmaceutical cold chain logistics with IoT sensor integration",
    "with_special_chars": "AI-powered café & restaurant finder (with reviews)",
    "with_numbers": "24/7 virtual assistant for SMB customer support",
    "invalid": "",
    "whitespace_only": "   ",
}

# Sample analyses for testing
SAMPLE_ANALYSES = {
    "minimal": """# Business Analysis

## Market Opportunity
The market exists.

## Competition
There are competitors.
""",
    "reviewbot_iteration1": """# ReviewBot: AI Code Review That Learns Your Team's Standards

## What We Do

ReviewBot is like having a senior engineer review every pull request instantly. We're building AI that learns how your team actually codes - your naming conventions, architecture patterns, and unwritten rules. Instead of generic linting, ReviewBot catches the stuff that matters to YOUR team. It reviews code in seconds, not days, and gets smarter with every PR.

## The Problem

Engineering teams are drowning in code review delays, with pull requests becoming the number one bottleneck in development cycle time [1]. A tech lead at a 50-person startup told us: "My best engineers spend 30% of their time reviewing code instead of shipping features. Junior devs wait days for feedback, then have to context-switch back to fix issues they barely remember writing."

The numbers are brutal: 58% of developers lose more than 5 hours weekly to unproductive work, with code review delays as a primary culprit [2]. At Meta, the median engineer spends 13 hours to merge a single PR, mostly waiting [3]. Meanwhile, bugs that slip through cost 10-100x more to fix in production. Generic linters catch syntax but miss architectural violations, security patterns, and team-specific conventions. DeepSource and SonarQube generate mountains of false positives because they don't understand YOUR codebase's patterns.

## The Solution

Here's the magic: connect ReviewBot to your GitHub, and it immediately analyzes your last 1,000 merged PRs to learn your team's actual standards. When a new PR comes in, ReviewBot reviews it in under 30 seconds, commenting directly on lines with issues specific to your codebase - not generic rules.

We cut review wait time from days to 30 seconds - instant feedback instead of context-switching hell. A 20-person team saved 160 engineering hours weekly. Our AI achieves <5% false positive rate by learning from your accepted PRs, compared to 40%+ for generic tools [4]. ReviewBot catches subtle issues like "this violates our service layer pattern" or "we always use dependency injection here" - stuff that takes years of context to know. Early pilots show 70% reduction in post-merge bugs and 3x faster PR throughput.

## Market Size

The AI code tools market is exploding to $6.11B in 2024, growing 27% annually to reach $26B by 2030 [5]. With 27 million developers worldwide spending 30% of time on code review, that's 8.1 million developer-years annually. At $150K average developer cost, we're looking at a $1.2 trillion inefficiency problem.

Bottom-up: 500,000 engineering teams globally × $2,000/month average spend = $12B addressable market just for automated review. GitHub alone has 100M+ developers creating 350M+ pull requests annually. The shift to AI-assisted development is accelerating - 73% of developers already use AI tools daily [6].

## Business Model

$49/developer/month for teams under 50; $39/developer/month for larger teams. A 20-developer team pays $11,760/year while saving $480,000 in engineering time (160 hours/week × 50 weeks × $60/hour). That's 40:1 ROI.

CAC is $2,000 through developer communities and content marketing. LTV is $15,000+ (25-month retention × $600/developer). With 70% gross margins after compute costs, we reach $100M ARR at 14,000 customers (280,000 developers). Comparable tool Codacy charges similar prices with inferior technology. Our viral growth comes from developers demanding ReviewBot at their next job.

## Why Now?

GPT-4 class models (2023) finally enabled understanding code semantics, not just syntax. Before, AI couldn't grasp architectural patterns or team conventions. Now, with retrieval-augmented generation on your codebase history, we can learn and enforce YOUR specific patterns.

GitHub just launched Copilot code review (October 2024), validating the massive market need [7]. But they're generic - we're personalized. The rise of remote work created urgency: distributed teams can't do informal knowledge transfer, making automated standards enforcement critical. 64% of developers already use AI for code production - review is the obvious next step [8].

## Competition & Moat

GitHub Copilot does generic reviews but doesn't learn team patterns. DeepSource/SonarQube use static rules with 40%+ false positives, while we achieve <5% by learning from your codebase. They charge by lines of code (costs explode with growth); we charge per developer (predictable).

Our moat: 1) Network effects - more PRs reviewed means better pattern recognition for that team, 2) Switching costs - ReviewBot becomes your team's institutional knowledge, 3) Data advantage - we're building the largest dataset of team-specific code patterns. Unlike generic tools, we get better for YOUR team over time. GitHub could copy us, but they're focused on individual developer productivity, not team standards. We're building the multiplayer version.

## Key Risks & Mitigation

Risk 1: GitHub builds team-learning features. Mitigation: Move faster, focus on enterprises GitHub ignores, build additional workflow tools beyond review.

Risk 2: AI costs make unit economics negative. Mitigation: Custom models reduce costs 80% vs GPT-4; caching similar patterns; tiered compute based on PR complexity.

Risk 3: Security concerns about code access. Mitigation: SOC2 from day one, on-premise option for enterprises, code never trains base models. The hidden risk others miss: developer adoption requires near-zero false positives - that's why we optimize for precision over recall initially.

## Milestones

- 30 days: 10 paid pilot teams actively using ReviewBot daily
- 90 days: $25K MRR from 50 teams, <10% weekly churn
- 6 months: $200K MRR, 500 teams, launch enterprise tier
- 12 months: $1.5M ARR, 2,000 teams, Series A metrics achieved

## References

[1] LinearB. "Why Estimated Review Time Improves Pull Requests." 2024. Pull requests are the #1 bottleneck in cycle time. <https://linearb.io/blog/why-estimated-review-time-improves-pull-requests-and-reduces-cycle-time>

[2] Cortex. "The 2024 State of Developer Productivity Report." 2024. 58% of developers lose 5+ hours weekly to unproductive work. <https://www.cortex.io/report/the-2024-state-of-developer-productivity>

[3] Meta Engineering. "Move faster, wait less: Improving code review time at Meta." 2024. Median 13 hours to merge a pull request. <https://engineering.fb.com/2022/11/16/culture/meta-code-review-time-improving/>

[4] DeepSource. "SonarQube Alternatives." 2024. DeepSource achieves <5% false positives vs competitors' high rates. <https://deepsource.com/sonarqube-alternatives>

[5] Grand View Research. "AI Code Tools Market Size Report." 2024. Market at $6.11B in 2024, reaching $26B by 2030. <https://www.grandviewresearch.com/industry-analysis/ai-code-tools-market-report>

[6] Codacy. "State of Software Quality Survey." 2024. 73% of developers use AI tools daily for coding. <https://blog.codacy.com/best-practices-for-coding-with-ai>

[7] GitHub Blog. "GitHub Copilot code review in GitHub.com." October 2024. Copilot launches automated PR review features. <https://github.blog/changelog/2024-10-29-github-copilot-code-review-in-github-com-private-preview/>

[8] Codacy. "State of Software Quality." 2024. 64% have integrated AI into code production, 62% use AI for review. <https://blog.codacy.com/best-practices-for-coding-with-ai>
""",
    "complete": """# Comprehensive Business Analysis

## Executive Summary
A detailed executive summary providing key insights into market opportunity, competitive landscape, and business viability. This analysis evaluates the potential for success based on current market conditions and emerging trends.

## Market Opportunity
The total addressable market (TAM) is estimated at $50B with 15% annual growth rate. Recent market research indicates strong demand driven by digital transformation initiatives and changing consumer preferences. The serviceable addressable market (SAM) represents approximately $15B, with realistic capture potential of 2-3% within 5 years.

## Competition Analysis
Three main competitors have been identified in this space:
1. **Competitor A** - Market leader with 35% market share, strong brand recognition
2. **Competitor B** - Fast-growing startup with innovative features, 15% market share
3. **Competitor C** - Traditional player pivoting to digital, 20% market share

Our competitive advantage lies in superior technology, better user experience, and targeted go-to-market strategy.

## Business Model
Subscription-based SaaS model with three tiers:
- **Starter**: $29/month for basic features
- **Professional**: $99/month with advanced capabilities
- **Enterprise**: Custom pricing with dedicated support

Revenue projections indicate path to profitability within 18-24 months.

## Go-to-Market Strategy
Multi-channel approach combining:
- Direct sales for enterprise accounts
- Product-led growth for SMB segment
- Strategic partnerships for distribution
- Content marketing for brand awareness

## Technical Feasibility
The proposed solution leverages proven technologies with moderate implementation complexity. Key technical requirements include cloud infrastructure, API integrations, and mobile applications. Development timeline estimated at 6-9 months for MVP.

## Financial Projections
- Year 1: $2M revenue, -$3M net (investment phase)
- Year 2: $8M revenue, -$1M net (growth phase)
- Year 3: $20M revenue, $3M net (profitability)
- Break-even expected in Month 22

## Risks and Mitigation
Key risks identified with corresponding mitigation strategies:
1. **Market Risk**: Slower adoption than projected
   - Mitigation: Flexible pricing model, freemium option
2. **Competition Risk**: Aggressive response from incumbents
   - Mitigation: Focus on differentiation, rapid iteration
3. **Execution Risk**: Technical or operational challenges
   - Mitigation: Experienced team, phased rollout approach
""",
    "poor_quality": """# Analysis

This is not a very good analysis.

## Market
Small market.

## Competition
Too many competitors.

## Model
Unclear.
""",
}

# Sample reviewer feedback
SAMPLE_FEEDBACK = {
    "approve": {
        "recommendation": "approve",
        "critical_issues": [],
        "improvement_suggestions": [
            "Consider adding more detail on regulatory considerations",
            "Include customer acquisition cost analysis",
        ],
        "strengths": [
            "Comprehensive market analysis with clear TAM/SAM/SOM breakdown",
            "Well-researched competitive landscape",
            "Realistic financial projections with clear path to profitability",
            "Identified risks with actionable mitigation strategies",
        ],
        "overall_assessment": "This is a well-researched and comprehensive analysis that provides clear insights into the business opportunity.",
        "priority": "low",
    },
    "reject": {
        "recommendation": "reject",
        "critical_issues": [
            "Missing market size analysis - no TAM/SAM/SOM provided",
            "No competitive advantages identified",
            "Business model lacks detail on pricing and revenue streams",
            "No go-to-market strategy outlined",
        ],
        "improvement_suggestions": [
            "Add detailed market sizing with supporting data",
            "Identify and analyze at least 3 main competitors",
            "Develop clear pricing tiers and revenue projections",
            "Create comprehensive go-to-market strategy",
            "Include financial projections for 3-year period",
        ],
        "strengths": ["Clear problem statement", "Target market identified"],
        "overall_assessment": "The analysis lacks critical business planning elements and needs substantial revision before approval.",
        "priority": "high",
    },
    "conditional": {
        "recommendation": "reject",
        "critical_issues": [
            "Incomplete competitive analysis",
            "Weak financial projections",
        ],
        "improvement_suggestions": [
            "Expand competitive analysis to include market positioning",
            "Add more detail to financial model with assumptions",
            "Include customer validation data",
        ],
        "strengths": [
            "Good market opportunity assessment",
            "Clear business model",
            "Technical feasibility well addressed",
        ],
        "overall_assessment": "The analysis shows promise but needs refinement in key areas before approval.",
        "priority": "medium",
    },
}


# Test file paths
def get_test_file_path(name: str, base_dir: Path) -> Path:
    """Get a test file path within the base directory."""
    return base_dir / f"test_{name}.md"


# Test slugs
TEST_SLUGS = {
    "simple": "ai-fitness-app",
    "complex": "blockchain-based-supply-chain-optimization-platform",
    "with_special": "ai-powered-cafe-restaurant-finder-with-reviews",
    "with_numbers": "24-7-virtual-assistant-for-smb-customer-support",
}


def load_test_prompt(name: str) -> str:
    """Load a test prompt file from test_prompts directory."""
    test_prompts_dir = Path(__file__).parent / "test_prompts"
    prompt_file = test_prompts_dir / f"{name}.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    return f"# Test Prompt: {name}\n\nThis is a test prompt."


# Expected outputs for validation
EXPECTED_SECTIONS = [
    "Executive Summary",
    "Market Opportunity",
    "Competition Analysis",
    "Business Model",
    "Risks and Mitigation",
]

# Websearch queries for testing
TEST_WEBSEARCH_QUERIES = [
    "fitness app market size 2024",
    "AI fitness app competitors",
    "fitness technology trends",
    "mobile health app revenue models",
]
