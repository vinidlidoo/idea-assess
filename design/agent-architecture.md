# Agent Architecture Design

## Overview

Four specialized agents working sequentially to evaluate business ideas, implemented using Claude SDK with MCP for external tools.

## System Architecture

```text
User Input (CLI)
    ↓
Pipeline Controller (Python)
    ↓
┌─────────────────────────────────┐
│  1. ANALYST AGENT               │
│  Input: One-liner idea          │
│  Output: Full analysis document │
│  Tools: Web search, research    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  2. REVIEWER AGENT              │
│  Input: Analysis document       │
│  Output: Improved analysis      │
│  Tools: Read, critique          │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  3. JUDGE AGENT                 │
│  Input: Final analysis          │
│  Output: Grades (A-D)           │
│  Tools: Evaluation framework    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  4. SYNTHESIZER AGENT           │
│  Input: All analyses + grades   │
│  Output: Comparative report     │
│  Tools: Data aggregation        │
└─────────────────────────────────┘
    ↓
Output Files (Markdown/JSON)
```

## Agent Specifications

### 1. Analyst Agent

**Role**: Transform one-liner ideas into comprehensive business analyses

**Capabilities**:

- Market research via MCP web search
- Competitor analysis
- TAM/SAM/SOM calculation
- Technical feasibility assessment
- Revenue model exploration

**Input**: String (e.g., "AI-powered fitness app for seniors")

**Output**: Structured markdown document (2000-2500 words)

**Tools Required**:

- MCP web search server
- File write (for saving research)
- Structured data extraction

### 2. Reviewer Agent

**Role**: Improve analysis quality through critical review

**Capabilities**:

- Identify gaps in analysis
- Fact-check claims
- Suggest additional considerations
- Improve narrative flow
- Ensure evidence-based reasoning

**Input**: Analysis markdown from Analyst

**Output**: Enhanced analysis markdown (same structure, better content)

**Tools Required**:

- File read/write
- Diff generation for tracking changes

### 3. Judge Agent

**Role**: Evaluate analyses against fixed criteria

**Evaluation Criteria** (A-D grades):

1. Market Opportunity
2. Technical Feasibility
3. Competitive Advantage
4. Revenue Potential
5. Risk Assessment
6. Team/Resource Requirements
7. Innovation Level

**Input**: Final analysis document

**Output**: JSON with grades and justifications

**Tools Required**:

- Structured evaluation framework
- JSON output formatting

### 4. Synthesizer Agent

**Role**: Create comparative reports across multiple ideas

**Capabilities**:

- Rank ideas by overall grade
- Identify patterns across evaluations
- Generate executive summary
- Create comparison tables
- Highlight top opportunities

**Input**: Collection of analyses and grades

**Output**: Comparative report markdown

**Tools Required**:

- File aggregation
- Data visualization (tables)
- Statistical analysis

## Implementation Details

### File Structure

```text
idea-assess/
├── src/
│   ├── __init__.py
│   ├── cli.py                 # Main CLI entry point
│   ├── pipeline.py            # Pipeline controller
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py           # Base agent class
│   │   ├── analyst.py        # Analyst implementation
│   │   ├── reviewer.py       # Reviewer implementation
│   │   ├── judge.py          # Judge implementation
│   │   └── synthesizer.py    # Synthesizer implementation
│   └── mcp/
│       ├── __init__.py
│       └── web_search.py     # MCP web search server
├── prompts/                   # Agent prompt templates
│   ├── analyst.md
│   ├── reviewer.md
│   ├── judge.md
│   └── synthesizer.md
├── config/
│   └── settings.yml          # Configuration
└── tests/
    └── test_agents.py
```

### Base Agent Class

```python
from claude_code_sdk import query, ClaudeCodeOptions
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str, system_prompt_file: str):
        self.name = name
        self.system_prompt = self.load_prompt(system_prompt_file)
        
    @abstractmethod
    async def process(self, input_data: dict) -> dict:
        """Process input and return output"""
        pass
    
    def load_prompt(self, file_path: str) -> str:
        """Load prompt from markdown file"""
        with open(file_path, 'r') as f:
            return f.read()
```

### Pipeline Controller

```python
class Pipeline:
    def __init__(self):
        self.analyst = AnalystAgent()
        self.reviewer = ReviewerAgent()
        self.judge = JudgeAgent()
        self.synthesizer = SynthesizerAgent()
    
    async def evaluate_idea(self, idea: str) -> dict:
        """Run full evaluation pipeline"""
        # Step 1: Analyze
        analysis = await self.analyst.process({"idea": idea})
        
        # Step 2: Review
        reviewed = await self.reviewer.process({"analysis": analysis})
        
        # Step 3: Judge
        grades = await self.judge.process({"analysis": reviewed})
        
        # Save outputs
        self.save_results(idea, reviewed, grades)
        
        return {"analysis": reviewed, "grades": grades}
```

### MCP Web Search Server

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WebSearch")

@mcp.tool()
async def search_market(query: str, max_results: int = 5) -> list:
    """Search for market information"""
    # Implementation using httpx or similar
    pass

@mcp.tool()
async def analyze_competitors(company: str) -> dict:
    """Analyze competitor landscape"""
    pass

@mcp.tool()
async def get_industry_data(industry: str) -> dict:
    """Get industry statistics and trends"""
    pass
```

## State Management

### Checkpointing

Each agent saves intermediate state:

```python
def save_checkpoint(self, stage: str, data: dict):
    checkpoint_path = f"checkpoints/{self.idea_slug}/{stage}.json"
    with open(checkpoint_path, 'w') as f:
        json.dump(data, f)
```

### Resume Capability

Pipeline can resume from any stage:

```python
def resume_from_checkpoint(self, idea_slug: str) -> str:
    """Find last completed stage and resume"""
    stages = ["analyst", "reviewer", "judge"]
    for stage in reversed(stages):
        if os.path.exists(f"checkpoints/{idea_slug}/{stage}.json"):
            return stage
    return None
```

## Error Handling

### Retry Logic

```python
async def process_with_retry(self, input_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await self.process(input_data)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Partial Failure Handling

- Each agent validates its input
- Malformed outputs trigger re-processing
- Failed web searches use cached data
- Graceful degradation for missing data

## Configuration

### settings.yml

```yaml
claude:
  model: "claude-3-opus-20240229"
  max_tokens: 4000
  temperature: 0.7

agents:
  analyst:
    word_limit: 2500
    research_depth: "comprehensive"
  reviewer:
    critique_level: "thorough"
  judge:
    grading_scale: "A-D"
  synthesizer:
    comparison_limit: 10

mcp:
  web_search:
    enabled: true
    rate_limit: 10  # requests per minute

output:
  format: "markdown"
  save_intermediates: true
```

## Testing Strategy

### Unit Tests

- Test each agent independently
- Mock Claude SDK responses
- Validate output formats

### Integration Tests

- Test full pipeline flow
- Test checkpoint/resume
- Test error recovery

### Example Test

```python
async def test_analyst_agent():
    analyst = AnalystAgent()
    result = await analyst.process({"idea": "AI tutoring platform"})
    
    assert "market_analysis" in result
    assert len(result["content"]) > 2000
    assert result["content"].count("#") >= 5  # Has sections
```

## Performance Considerations

### Token Optimization

- Reuse context between agents where possible
- Compress intermediate outputs
- Use structured formats (JSON) for data transfer

### Parallel Processing (P1)

Future enhancement for parallel execution:

```python
async def evaluate_multiple(self, ideas: list):
    """Evaluate multiple ideas in parallel"""
    tasks = [self.evaluate_idea(idea) for idea in ideas]
    return await asyncio.gather(*tasks)
```

## Security Considerations

- Sanitize all file paths
- Validate idea input length
- Rate limit API calls
- No execution of arbitrary code
- Secure storage of API keys

## Monitoring

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics

- Processing time per agent
- Token usage per evaluation
- Success/failure rates
- Average grades distribution

## Next Steps

1. Create prompt templates for each agent
2. Implement base agent class
3. Set up MCP web search server
4. Build CLI interface
5. Implement pipeline controller
6. Add testing framework
