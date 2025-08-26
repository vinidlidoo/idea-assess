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
