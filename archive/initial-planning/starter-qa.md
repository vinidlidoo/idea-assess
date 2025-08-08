# Discussion on requirements

## Q&A

This is a Q&A with Claude Code to clarifying requirements before we move to design and implementation planning.

Once you answer these, I can significantly improve the work plan with specific implementation details, proper evaluation schemas, and a more robust architecture.

### 1. Idea Input Format & Depth

- How detailed should each business idea file be? A paragraph? A page? Structured sections (problem, solution, target market)?

A: 1 page with the proper outline, including, yes, problem, solution, target market, and any other sections or subsections that would make sense if we were to fit the narrative into a single page. Since we'll use markdown files, let's limit the number of words or characters instead of using the concept of page. We should allow for another document, let's call it the supplemental doc that will serve as an Appendix with additional data points and other details.

- Should we enforce a template to ensure consistency, or accept free-form text?

A: We should enforce a template with required sections and subsections. Anything else can go into a supplemental document.

### 2. Evaluation Specifics

- For "market potential" - are you thinking TAM estimation, growth trends, or something else?

A: I'm looking for data on metrics such as total addressable market, growth, and trends. Overall, I need a narrative, so market potential should be a section or subsection in the output document I referenced in question one.  

- For "competitive landscape" - do you want to identify actual competitors, or just assess difficulty of entry?

A: The competitive landscape can include a short summary of the main competitors or companies active in the market. It can also assess barriers to entry for companies not already involved, or explain why large companies might not enter the market. This includes the innovator's dilemma, where embracing new technology might cannibalize a company's own sales. This type of analysis would also fit under the competitive landscape umbrella.

- Should the system provide concrete evidence/reasoning, or just scores?

A: The narrative is at the center of the output and should be provided using business-savvy reasoning supported by evidence, including quotes and sources. For each component, market potential and competitive landscape should begin with a score. This score could be subjective, given by an agent or sub-agent in the system.

### 3. Budget & Model Choice

- Which Claude model were you planning to use? (Haiku for speed/cost, Sonnet for balance, Opus for depth?)

The best model for the task at hand. Since I'm planning for the system to be asynchronous we should bias toward apply too much compute vs not enough.

- Any budget constraints for API costs? This affects how thorough each evaluation can be.

Assume we're using the Claude Max plan (5x).

### 4. Output Goals

- Do you want a simple ranked list, or detailed comparative analysis between top ideas?

The summary output document (also 1 page) should include both the ranked list in a table and a narrative summarize the top business candidates and how they compare with each other.

- Should the system explain WHY certain ideas ranked higher?

Absolutely.

### 5. Scale & Source

- Roughly how many ideas are we talking about? 10? 100? 1000?

I'm thinking around 10-15 active ideas at a time.

- Where are these ideas coming from? Your own brainstorming? External sources?

Assume the ideas are given as input first. As a second priority we can think about creating a module that generates new ideas based on external sources, but not in the first version of the prototype.

## Additional Questions from Claude

### 6. Evaluation Framework & Scoring

- What specific criteria should we evaluate beyond market potential and competitive landscape? (e.g., technical feasibility, capital requirements, regulatory risks, team fit?)

A: Based on our discussion, here are the evaluation criteria for P0:

- Market Potential (TAM, growth rate, trends)
- Competitive Landscape (competitors, barriers to entry, disruption potential)
- Technical Feasibility (complexity, technology readiness, development timeline)
- Capital Requirements (initial investment, burn rate, path to profitability)
- Regulatory Risks (compliance requirements, legal barriers, licensing needs)
- Execution Difficulty (operational complexity, supply chain, distribution challenges)
- Evidence Quality (strength of supporting data and citations)

- For scoring, what scale should we use? (1-10, 1-100, letter grades, or something else?)

A: Letter grade is probably the right granularity to start with. A, B, C, or D

- Should different criteria have different weights in the final ranking?

A: Yes, but as a second priority.

### 7. Data Sources & Research

- Should the system use web search/scraping for market data, or rely solely on LLM knowledge?

A: both web search/scraping and LLM-based reasoning.

- How important is citing real sources vs. synthesized analysis?

A: Come to think of it, the degree to which cited sources are doing a good job at backing up the analysis should be an evaluation criteria.

- Should we integrate with specific APIs (e.g., market research databases, patent searches)?

A: Let's add that as a second priority. Not in this initial prototype.

### 8. Workflow & Processing

- Do you envision running evaluations one at a time or batch processing all ideas simultaneously?

A: One at a time at first. Parallel batch processing as a second priority. Not in the initial prototype.

- Should the system be able to re-evaluate ideas if market conditions change or new information becomes available?

A: This in an important feature. Second priority though.

- Do you want version control/history of evaluations?

A: Yes, I'm thinking we should simply use git to keep track of changes in the analysis.

### 9. Template Structure

- For the required template, what specific sections are must-haves? (Problem, Solution, Target Market, Business Model, Go-to-Market Strategy, Team Requirements?)

A: Problem. Solution. Target Market. Business Model. GTM Strategy. Capital Requirements. Technology Requirements. Skills Requirements (to execute on the idea).

- Should we enforce word limits for each section?

A: Yes. This will force bringing clarity to the analysis.

- How should the supplemental document be structured/linked?

A: Let's start with free form in the supplemental document. We can add constraints as a second priority.

### 10. Output & Reporting

- Besides the 1-page evaluation per idea and the summary document, do you need any other outputs? (CSV export, dashboard, API endpoints?)

A: No, not initially.

- Should evaluations include specific action items or next steps for promising ideas?

A: Yes, we should add next steps for someone who would want to start taking steps toward executing on the idea.

- Do you want risk assessments or SWOT analysis included?

A: Risks should be a section yes. SWOT analysis or other analysis framework not needed for now.

### 11. Architecture & Technical Approach

- Should this be a CLI tool, web app, or both?

A: Initially, we should start with a simple CLI. It should be able to execute an analysis on a selected ideas, or all. It should also be able to grade the idea based on the analysis. And finally, generate the summary report with ranked ideas and a comparative analysis between ideas.

- Do you prefer a pipeline architecture (sequential processing) or parallel evaluation with multiple agents?

A: sequential processing at first. Parallelization is something we should plan to do a second priority. In the requirements doc, we should label P0 the requirements for the initial phase and P1 everything I have called out as a second priority.

- How should we handle agent orchestration - simple coordinator or more complex workflow engine?

A: that's an important consideration but I think we should make that decision in the design phase, after we're done drafting the requirements.

## Additional thoughts

1. Another objective for this project is to learn how to leverage the latest features of Claude Code: Claude SDK, hooks, slash commands, sub agents. In the design phase, we should thoroughly research the latest Anthropic documentation and how other devs are currently leveraging the tooling offered by Anthropic.

2. The prototype should include at least two agents: the *analyst*, who owns making and writing the analysis, and the *reviewer*, who owns providing feedback to improve the quality of the analysis, and the *judge*, who owns drafting the evaluations of each analyses.
