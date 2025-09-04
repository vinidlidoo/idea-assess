# Fact-Check Request

**Iteration**: {iteration} of {max_iterations}
**Analysis Path**: {analysis_path}
**Output File**: {fact_check_file}

## Your Task

Please fact-check the business idea analysis located at {analysis_path}.

Focus on verifying:

1. **Citations and Sources**: Verify all referenced statistics, reports, and claims
2. **Market Data**: Check market sizes, growth rates, and industry trends
3. **Competitor Information**: Validate claims about existing competitors
4. **Technical Claims**: Verify feasibility of technical capabilities mentioned

## Instructions

1. Read the analysis from {analysis_path}
2. Identify all factual claims that require verification
3. Use WebFetch to verify critical claims (prioritize most important)
4. Edit the JSON file at {fact_check_file} with your findings

## Output Format

You MUST edit the existing JSON template file at {fact_check_file} to include your findings.
The file already contains the required structure with TODO placeholders - replace them with your actual findings.

Remember:

- Only mark issues as "critical" if they fundamentally undermine the analysis
- Use "major" for significant but not fatal issues
- Use "minor" for small inaccuracies that don't affect conclusions
- Your recommendation should be either "approve", "revise", or "reject"
