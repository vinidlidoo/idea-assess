# Agent Architecture Design

## Overview

Four specialized agents working sequentially to evaluate business ideas, implemented using **claude-code-sdk-python** for simplified agent development with built-in tool support.

**SDK Decision (Revised)**: We use `claude-code-sdk-python` because:

- **50% less code** - Built-in file operations and tool handling
- **Faster development** - Tools like Read, Write, WebSearch work out of the box
- **Simpler orchestration** - Clean context manager pattern for agents
- **Perfect fit** - Designed for exactly this kind of agent-based system
- **Learning focus** - Optimizes for rapid iteration over production concerns

## System Architecture

```text
User Input (CLI)
    ↓
Pipeline Controller (Python + claude-code-sdk)
    ↓
┌─────────────────────────────────┐
│  1. ANALYST AGENT               │
│  Input: One-liner idea          │
│  Output: analysis_v1.md         │
│  Tools: Read, Write, WebSearch  │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  2. REVIEWER AGENT              │
│  Input: analysis_v{n}.md        │
│  Output: feedback_v{n}.json     │
│  Tools: Read, Write             │
└─────────────────────────────────┘
    ↓ (feedback loop, max 3 iterations)
┌─────────────────────────────────┐
│  ANALYST AGENT (iteration)      │
│  Input: Previous + feedback     │
│  Output: analysis_v{n+1}.md     │
│  Tools: Read, Write, WebSearch  │
└─────────────────────────────────┘
    ↓ (after final iteration)
┌─────────────────────────────────┐
│  3. JUDGE AGENT                 │
│  Input: final_analysis.md       │
│  Output: evaluation.json        │
│          (grades per criterion) │
│  Tools: Read, Write             │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  4. SYNTHESIZER AGENT           │
│  Input: All evaluations         │
│  Output: summary_report.md      │
│          + overall rankings     │
│  Tools: Read, Write             │
└─────────────────────────────────┘
    ↓
Output Files (work/{agent}/*.md|*.json)
```

## Agent Specifications

### 1. Analyst Agent

**Role**: Transform one-liner ideas into comprehensive business analyses

**Capabilities**:

- Market research via WebSearch tool
- Competitor analysis
- TAM/SAM/SOM calculation
- Technical feasibility assessment
- Revenue model exploration

**Input**: String (e.g., "AI-powered fitness app for seniors")

**Output**: Structured markdown document (2000-2500 words)

**Tools Required**:

- `Read` - Read files from other agents' outputs
- `Write` - Save analysis drafts and final outputs
- `WebSearch` - Research market data (built-in claude-code-sdk tool)

### 2. Reviewer Agent

**Role**: Provide constructive feedback to improve analysis quality

**Capabilities**:

- Identify gaps in analysis
- Fact-check claims
- Suggest additional considerations
- Critique narrative flow and clarity
- Ensure evidence-based reasoning
- Point out unsupported assumptions

**Input**: Analysis markdown draft from Analyst

**Output**: JSON feedback file (`feedback_v{n}.json`) containing:

```json
{
  "satisfied": false,  // Key decision field for iteration control
  "critical_gaps": ["missing competitor analysis", "no TAM calculation"],
  "improvements": ["expand technical feasibility section"],
  "questions": ["How does this differ from existing solutions?"],
  "quality_score": 7.5,  // 1-10 scale
  "iteration": 1,
  "strengths": ["good market overview", "clear value proposition"],
  "narrative_issues": ["weak conclusion", "needs better flow in section 3"]
}
```

**Tools Required**:

- `Read` - Read analysis drafts from analyst
- `Write` - Save structured feedback as JSON

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

**Output Format**: JSON structure with:

```json
{
  "executive_summary": "paragraph",
  // NOTE: No overall_grade here - that's computed by Synthesizer
  "criteria_grades": {
    "market_opportunity": {"grade": "A-D", "justification": "..."},
    "technical_feasibility": {"grade": "A-D", "justification": "..."},
    "competitive_advantage": {"grade": "A-D", "justification": "..."},
    "revenue_potential": {"grade": "A-D", "justification": "..."},
    "risk_assessment": {"grade": "A-D", "justification": "..."},
    "team_resources": {"grade": "A-D", "justification": "..."},
    "innovation_level": {"grade": "A-D", "justification": "..."}
  },
  "strengths": [...],
  "weaknesses": [...],
  "recommendation": "Yes/No/Maybe",
  "confidence_level": "High/Medium/Low"
}
```

**Tools Required**:

- `Read` - Read final analysis from analyst
- `Write` - Save evaluation as JSON

### 4. Synthesizer Agent

**Role**: Create comparative reports across multiple ideas and compute overall grades

**Capabilities**:

- **Compute overall grades** from Judge's criteria grades (weighted average)
- Rank ideas by computed overall grade
- Identify patterns across evaluations
- Generate executive summary
- Create comparison tables
- Highlight top opportunities
- Statistical analysis of grade distributions

**Input**: Collection of evaluation JSONs from Judge

**Output**:

- Comparative report markdown (`summary_report.md`)
- Rankings JSON with computed overall grades

**Grade Computation**:

```python
weights = {
    "market_opportunity": 0.25,
    "revenue_potential": 0.20,
    "competitive_advantage": 0.15,
    "technical_feasibility": 0.15,
    "innovation_level": 0.10,
    "risk_assessment": 0.10,
    "team_resources": 0.05
}
```

**Tools Required**:

- `Read` - Read all evaluation JSONs from judge
- `Write` - Save summary report and rankings

## Iteration Logic and Stopping Conditions

### Review Iteration Process

The Analyst-Reviewer feedback loop operates as follows:

1. **Initial Draft**: Analyst produces v1 based on the one-liner
2. **Review Round**: Reviewer provides structured feedback
3. **Iteration Decision**: System checks stopping conditions
4. **Revision**: If continuing, Analyst incorporates feedback into v2/v3

### Stopping Conditions

The review process stops when ANY of these conditions are met:

1. **Reviewer Satisfaction**: Reviewer marks analysis as "satisfied"
2. **Maximum Iterations**: Reached configured limit (default: 3)
3. **Diminishing Returns**: Feedback becomes minor/cosmetic only

### Feedback Structure

Reviewer outputs the JSON structure defined in Section 2 (`feedback_v{n}.json`) with `satisfied` field controlling iteration flow.

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
│   │   ├── base.py           # Lightweight base class
│   │   ├── analyst.py        # Analyst agent
│   │   ├── reviewer.py       # Reviewer agent  
│   │   ├── judge.py          # Judge agent
│   │   └── synthesizer.py    # Synthesizer agent
├── work/                      # Agent working directories (auto-created)
│   ├── analyst/
│   ├── reviewer/
│   ├── judge/
│   └── synthesizer/
├── prompts/                   # Agent system prompts
│   ├── analyst.md
│   ├── reviewer.md
│   ├── judge.md
│   └── synthesizer.md
├── config/
│   └── settings.yml          # Configuration
└── tests/
    └── test_agents.py
```

### Base Agent Implementation

```python
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from pathlib import Path
import json
from typing import Dict, Any, Optional

class BaseAgent:
    """Base class for all agents using claude-code-sdk"""
    
    def __init__(self, name: str, prompt_file: str, allowed_tools: list = None):
        self.name = name
        self.system_prompt = Path(f"prompts/{prompt_file}").read_text()
        self.allowed_tools = allowed_tools or ["Read", "Write"]
        self.working_dir = f"work/{name}"
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
    
    async def run(self, prompt: str) -> None:
        """Execute agent with given prompt"""
        options = ClaudeCodeOptions(
            system_prompt=self.system_prompt,
            allowed_tools=self.allowed_tools,
            working_directory=self.working_dir,
            max_turns=10,
            permission_mode='acceptEdits'  # Auto-accept file operations
        )
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            # Files are automatically saved by the agent
    
    def get_output(self, filename: str) -> Any:
        """Read output file produced by agent"""
        output_path = Path(self.working_dir) / filename
        if output_path.suffix == '.json':
            return json.loads(output_path.read_text())
        return output_path.read_text()
```

### Pipeline Controller

```python
import asyncio
from pathlib import Path
import shutil

class Pipeline:
    def __init__(self, config: dict):
        self.config = config
        self.max_iterations = config.get('max_review_iterations', 3)
        
        # Initialize agents with appropriate tools
        self.analyst = AnalystAgent(
            allowed_tools=["Read", "Write", "WebSearch"]
        )
        self.reviewer = ReviewerAgent(
            allowed_tools=["Read", "Write"]
        )
        self.judge = JudgeAgent(
            allowed_tools=["Read", "Write"]
        )
        self.synthesizer = SynthesizerAgent(
            allowed_tools=["Read", "Write"]
        )
    
    async def evaluate_idea(self, idea: str) -> dict:
        """Run full evaluation pipeline with iterative review"""
        
        # Step 1: Initial analysis
        await self.analyst.run(f"""
            Analyze this business idea: {idea}
            
            Use WebSearch to research the market.
            Write a comprehensive 2000-word analysis.
            Save it as 'analysis_v1.md'
        """)
        
        # Step 2: Iterative review process
        for iteration in range(1, self.max_iterations + 1):
            # Review current version
            await self.reviewer.run(f"""
                Read 'analysis_v{iteration}.md' from ../analyst directory.
                
                Review it thoroughly and provide structured feedback.
                Save feedback as 'feedback_v{iteration}.json' with:
                - satisfied: boolean
                - critical_gaps: list of missing elements
                - improvements: list of suggestions
                - quality_score: float (1-10)
            """)
            
            # Check if satisfied
            feedback = self.reviewer.get_output(f'feedback_v{iteration}.json')
            if feedback.get('satisfied', False):
                break
            
            # Analyst revises
            await self.analyst.run(f"""
                Original idea: {idea}
                
                Read your previous draft 'analysis_v{iteration}.md'
                Read the feedback from '../reviewer/feedback_v{iteration}.json'
                
                Revise the analysis addressing all feedback.
                Save the improved version as 'analysis_v{iteration + 1}.md'
            """)
        
        # Copy final version for judge
        final_version = f'analysis_v{iteration}.md'
        shutil.copy(
            Path(self.analyst.working_dir) / final_version,
            Path(self.judge.working_dir) / 'final_analysis.md'
        )
        
        # Step 3: Judge evaluates
        await self.judge.run("""
            Read 'final_analysis.md' and evaluate it.
            
            Grade each of our 7 criteria (A-D) with justifications.
            Save evaluation as 'evaluation.json' with all grades and reasoning.
        """)
        
        evaluation = self.judge.get_output('evaluation.json')
        
        return {
            'analysis_path': Path(self.analyst.working_dir) / final_version,
            'evaluation': evaluation
        }
```

### WebSearch Integration

With claude-code-sdk, WebSearch is a built-in tool that agents can use directly:

```python
class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="analyst",
            prompt_file="analyst.md",
            allowed_tools=["Read", "Write", "WebSearch"]
        )
```

If WebSearch isn't available in your Claude Code setup, the agent will gracefully fall back to knowledge-based analysis.

## State Management

### Working Directory Structure

```text
work/
├── analyst/
│   ├── analysis_v1.md         # First draft
│   ├── analysis_v2.md         # After first review
│   ├── analysis_v3.md         # After second review
│   └── .checkpoint.json       # Agent state
├── reviewer/
│   ├── feedback_v1.json      # First review
│   ├── feedback_v2.json      # Second review
│   └── .checkpoint.json      # Agent state
├── judge/
│   ├── final_analysis.md     # Copy for evaluation
│   ├── evaluation.json       # Grades and justifications
│   └── .checkpoint.json      # Agent state
└── synthesizer/
    ├── summary_report.md     # Comparative report
    ├── rankings.json         # Overall grades
    └── .checkpoint.json      # Agent state
```

### Pipeline State Tracking

```python
class Pipeline:
    def __init__(self, config: dict):
        self.state_file = Path("work/.pipeline_state.json")
        self.state = self.load_state()
    
    def load_state(self) -> dict:
        """Load or initialize pipeline state"""
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {
            "current_idea": None,
            "current_stage": None,
            "iteration": 0,
            "ideas_processed": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def save_state(self):
        """Persist current pipeline state"""
        self.state_file.write_text(json.dumps(self.state, indent=2))
    
    def checkpoint(self, stage: str, data: dict):
        """Save checkpoint for current stage"""
        self.state["current_stage"] = stage
        self.state["timestamp"] = datetime.now().isoformat()
        self.state.update(data)
        self.save_state()
```

### Resume Capability

```python
class Pipeline:
    async def resume(self, idea: str) -> dict:
        """Resume pipeline from last checkpoint"""
        self.state = self.load_state()
        
        if self.state["current_idea"] != idea:
            # Different idea, start fresh
            return await self.evaluate_idea(idea)
        
        stage = self.state["current_stage"]
        iteration = self.state.get("iteration", 1)
        
        # Resume from appropriate stage
        if stage == "analyst":
            # Check if analysis exists
            analysis_file = Path(f"work/analyst/analysis_v{iteration}.md")
            if analysis_file.exists():
                # Move to review stage
                return await self._continue_from_review(idea, iteration)
            else:
                # Restart analysis
                return await self.evaluate_idea(idea)
        
        elif stage == "reviewer":
            # Check if feedback exists
            feedback_file = Path(f"work/reviewer/feedback_v{iteration}.json")
            if feedback_file.exists():
                feedback = json.loads(feedback_file.read_text())
                if feedback.get("satisfied"):
                    # Move to judge
                    return await self._continue_from_judge(idea, iteration)
                else:
                    # Continue iteration
                    return await self._continue_analyst_revision(idea, iteration + 1)
            else:
                # Re-run review
                return await self._continue_from_review(idea, iteration)
        
        elif stage == "judge":
            # Check if evaluation exists
            eval_file = Path("work/judge/evaluation.json")
            if eval_file.exists():
                return json.loads(eval_file.read_text())
            else:
                return await self._continue_from_judge(idea, iteration)
        
        # Default: start fresh
        return await self.evaluate_idea(idea)
```

### Crash Recovery

The pipeline automatically recovers from crashes:

```python
@click.command()
@click.argument('idea')
@click.option('--resume/--fresh', default=True, help='Resume from checkpoint')
def analyze(idea, resume):
    """Analyze a business idea with automatic recovery"""
    pipeline = Pipeline(config)
    
    if resume:
        # Check for existing work
        state_file = Path("work/.pipeline_state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            if state.get("current_idea") == idea:
                console.print(f"Resuming from {state['current_stage']}...")
                result = asyncio.run(pipeline.resume(idea))
            else:
                result = asyncio.run(pipeline.evaluate_idea(idea))
        else:
            result = asyncio.run(pipeline.evaluate_idea(idea))
    else:
        # Clear previous work
        shutil.rmtree("work", ignore_errors=True)
        result = asyncio.run(pipeline.evaluate_idea(idea))
```

## Error Handling

### Error Handling with claude-code-sdk

```python
class BaseAgent:
    async def run_with_retry(self, prompt: str, max_retries: int = 3) -> None:
        """Run agent with automatic retry on failure"""
        for attempt in range(max_retries):
            try:
                await self.run(prompt)
                return
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed
                    self.logger.error(f"All {max_retries} attempts failed")
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                self.logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
```

### Validation and Recovery

```python
class Pipeline:
    def validate_output(self, agent_name: str, expected_file: str) -> bool:
        """Validate agent output exists and is valid"""
        output_path = Path(f"work/{agent_name}/{expected_file}")
        
        if not output_path.exists():
            self.logger.error(f"Missing output: {output_path}")
            return False
        
        # Validate JSON files
        if output_path.suffix == '.json':
            try:
                data = json.loads(output_path.read_text())
                # Check required fields based on agent
                if agent_name == "reviewer":
                    required = ["satisfied", "critical_gaps", "quality_score"]
                    return all(field in data for field in required)
                elif agent_name == "judge":
                    return "criteria_grades" in data
            except json.JSONDecodeError:
                self.logger.error(f"Invalid JSON: {output_path}")
                return False
        
        # Validate markdown files have content
        elif output_path.suffix == '.md':
            content = output_path.read_text()
            if len(content) < 100:  # Minimum content check
                self.logger.error(f"Output too short: {output_path}")
                return False
        
        return True
```

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
    max_iterations: 3
  judge:
    grading_scale: "A-D"
  synthesizer:
    comparison_limit: 10

pipeline:
  max_review_iterations: 3

mcp:
  web_search:
    enabled: true
    rate_limit: 10  # requests per minute

output:
  format: "markdown"
  save_intermediates: true
```

## Implementation Requirements

### Prerequisites

```bash
# Install Node.js and Claude Code CLI (one-time setup)
npm install -g @anthropic-ai/claude-code

# Python dependencies
pip install claude-code-sdk click pyyaml rich python-dotenv
```

### Dependencies

```toml
# pyproject.toml
[project]
name = "idea-assess"
version = "0.1.0"
dependencies = [
    "claude-code-sdk>=0.1.0",
    "click>=8.1.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
]

```

### Required Imports

```python
# Core SDK imports
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

# Standard library
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

# Third-party
import click
import yaml
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv
```

## Testing Strategy

### Unit Tests

Test each agent with mocked claude-code-sdk:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

@pytest.mark.asyncio
async def test_analyst_agent():
    """Test analyst produces valid output"""
    with patch('claude_code_sdk.ClaudeSDKClient') as mock_client:
        # Mock the context manager
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.query = AsyncMock()
        
        # Create test output
        Path("work/analyst").mkdir(parents=True, exist_ok=True)
        Path("work/analyst/analysis_v1.md").write_text(
            "# Market Analysis\n\n## Overview\n\nTest content..."
        )
        
        analyst = AnalystAgent()
        await analyst.run("Analyze: AI tutoring platform")
        
        # Verify query was called
        mock_instance.query.assert_called_once()
        
        # Verify output exists
        output = analyst.get_output("analysis_v1.md")
        assert "Market Analysis" in output
        assert len(output) > 100

@pytest.mark.asyncio
async def test_reviewer_feedback_structure():
    """Test reviewer produces valid JSON feedback"""
    reviewer = ReviewerAgent()
    
    # Create test analysis to review
    Path("work/analyst/analysis_v1.md").write_text("Test analysis")
    
    # Mock and run
    with patch('claude_code_sdk.ClaudeSDKClient'):
        # Create expected output
        feedback = {
            "satisfied": False,
            "critical_gaps": ["missing TAM"],
            "quality_score": 6.5,
            "iteration": 1
        }
        Path("work/reviewer").mkdir(parents=True, exist_ok=True)
        Path("work/reviewer/feedback_v1.json").write_text(
            json.dumps(feedback)
        )
        
        result = reviewer.get_output("feedback_v1.json")
        
        # Validate structure
        assert "satisfied" in result
        assert "critical_gaps" in result
        assert isinstance(result["quality_score"], (int, float))
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete pipeline flow"""
    config = {"max_review_iterations": 2}
    pipeline = Pipeline(config)
    
    with patch('claude_code_sdk.ClaudeSDKClient'):
        # Mock outputs at each stage
        mock_outputs()
        
        result = await pipeline.evaluate_idea("AI tutoring platform")
        
        assert "analysis_path" in result
        assert "evaluation" in result
        assert result["evaluation"]["criteria_grades"]

@pytest.mark.asyncio
async def test_resume_capability():
    """Test pipeline can resume from checkpoint"""
    pipeline = Pipeline({})
    
    # Create partial state
    state = {
        "current_idea": "AI tutoring",
        "current_stage": "reviewer",
        "iteration": 1
    }
    Path("work/.pipeline_state.json").write_text(json.dumps(state))
    
    with patch('claude_code_sdk.ClaudeSDKClient'):
        result = await pipeline.resume("AI tutoring")
        
        # Should resume from reviewer stage
        assert pipeline.state["current_stage"] in ["judge", "completed"]
```

### Testing WebSearch Integration

```python
@pytest.mark.asyncio
async def test_websearch_fallback():
    """Test graceful degradation when WebSearch fails"""
    analyst = AnalystAgent()
    
    with patch('claude_code_sdk.ClaudeSDKClient') as mock_client:
        # First call fails with WebSearch error
        mock_instance = AsyncMock()
        mock_instance.query.side_effect = [
            Exception("WebSearch tool not available"),
            None  # Second call succeeds
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        await analyst.run_with_fallback("Analyze with WebSearch: AI tutoring")
        
        # Should have been called twice (once with, once without WebSearch)
        assert mock_instance.query.call_count == 2
```

## Agent Implementations

```python
# src/agents/analyst.py
from .base import BaseAgent

class AnalystAgent(BaseAgent):
    def __init__(self, allowed_tools=None):
        super().__init__(
            name="analyst",
            prompt_file="analyst.md",
            allowed_tools=allowed_tools or ["Read", "Write", "WebSearch"]
        )

# src/agents/reviewer.py  
class ReviewerAgent(BaseAgent):
    def __init__(self, allowed_tools=None):
        super().__init__(
            name="reviewer",
            prompt_file="reviewer.md",
            allowed_tools=allowed_tools or ["Read", "Write"]
        )

# src/agents/judge.py
class JudgeAgent(BaseAgent):
    def __init__(self, allowed_tools=None):
        super().__init__(
            name="judge",
            prompt_file="judge.md",
            allowed_tools=allowed_tools or ["Read", "Write"]
        )

# src/agents/synthesizer.py
class SynthesizerAgent(BaseAgent):
    def __init__(self, allowed_tools=None):
        super().__init__(
            name="synthesizer",
            prompt_file="synthesizer.md",
            allowed_tools=allowed_tools or ["Read", "Write"]
        )
```

## CLI Implementation

```python
# src/cli.py
import click
import asyncio
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from .pipeline import Pipeline
from .config import load_config

console = Console()

@click.group()
@click.option('--config', default='config/settings.yml', help='Config file path')
@click.pass_context
def cli(ctx, config):
    \"\"\"Business Idea Evaluator CLI\"\"\"
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)

@cli.command()
@click.argument('idea')
@click.option('--output-dir', default='analyses', help='Output directory')
@click.pass_context
def analyze(ctx, idea, output_dir):
    \"\"\"Analyze a business idea\"\"\"
    config = ctx.obj['config']
    
    with console.status(f"Analyzing: {idea}"):
        pipeline = Pipeline(config)
        result = asyncio.run(pipeline.evaluate_idea(idea))
    
    # Save results
    output_path = Path(output_dir) / f"{idea[:30].replace(' ', '-')}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result['analysis'])
    
    console.print(f"✅ Analysis saved to {output_path}")

@cli.command()
@click.option('--limit', default=10, help='Number of ideas to compare')
@click.pass_context
def generate_summary(ctx, limit):
    \"\"\"Generate comparative summary report\"\"\"
    config = ctx.obj['config']
    
    with console.status("Generating summary report..."):
        pipeline = Pipeline(config)
        report = asyncio.run(pipeline.generate_summary(limit))
    
    # Save report
    report_path = Path('reports') / f"summary-{datetime.now():%Y%m%d-%H%M%S}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    
    console.print(f"✅ Report saved to {report_path}")

if __name__ == '__main__':
    cli()
```

## Next Steps

1. Create prompt templates for each agent
2. Implement base agent class  
3. Build CLI interface
4. Implement pipeline controller
5. Add testing framework

## References and Resources

### Official Documentation

1. **Claude Code SDK Python** (PRIMARY)
   - GitHub: <https://github.com/anthropics/claude-code-sdk-python>
   - Docs: <https://docs.anthropic.com/en/docs/claude-code/sdk#python>
   - Best Practices: <https://www.anthropic.com/engineering/claude-code-best-practices>

2. **Anthropic SDK Python** (Reference only)
   - GitHub: <https://github.com/anthropics/anthropic-sdk-python>
   - Docs: <https://docs.anthropic.com/en/api/client-sdks#python>
   - Tool Use Guide: <https://docs.anthropic.com/en/docs/build-with-claude/tool-use>

3. **Model Context Protocol (MCP)**
   - Python SDK: <https://github.com/modelcontextprotocol/python-sdk>
   - Documentation: <https://modelcontextprotocol.io/introduction>
   - Server Examples: <https://github.com/modelcontextprotocol/servers>

### Key Implementation Guides

1. **MCP Integration with Claude**
   - Claude Desktop MCP: <https://docs.anthropic.com/en/docs/claude-code/mcp>
   - MCP Quickstart: <https://modelcontextprotocol.io/quickstart/server>
   - FastMCP Tutorial: <https://modelcontextprotocol.io/tutorials/fastmcp>

2. **Agent Development Patterns**
   - Multi-Agent Systems: <https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns>
   - Conversation Design: <https://docs.anthropic.com/en/docs/build-with-claude/conversation-design>

### Community Resources

1. **Tutorials and Examples**
   - MCP Server Setup: <https://scottspence.com/posts/configuring-mcp-tools-in-claude-code>
   - Claude MCP Community: <https://www.claudemcp.com/>
   - DataCamp MCP Guide: <https://www.datacamp.com/tutorial/mcp-model-context-protocol>

### API Reference

1. **Core APIs**
   - Messages API: <https://docs.anthropic.com/en/api/messages>
   - Streaming API: <https://docs.anthropic.com/en/api/messages-streaming>
   - Token Counting: <https://docs.anthropic.com/en/docs/build-with-claude/token-counting>
