# Implementation Comparison: claude-code-sdk vs anthropic-sdk

## Our Specific Use Case Requirements

1. Four agents working sequentially (Analyst → Reviewer → Judge → Synthesizer)
2. Iterative loop between Analyst and Reviewer (max 3 iterations)
3. Pass analysis documents between agents
4. Optional MCP web search for Analyst
5. Save outputs to files

## Approach 1: Using claude-code-sdk-python (SIMPLER)

```python
# main.py - Using claude-code-sdk-python
import asyncio
import json
from pathlib import Path
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def run_analyst(idea: str, iteration: int = 1, feedback: dict = None):
    """Run the Analyst agent"""
    options = ClaudeCodeOptions(
        system_prompt=Path("prompts/analyst.md").read_text(),
        allowed_tools=["Read", "Write", "WebSearch"],
        working_directory="analyses",
        max_turns=5
    )
    
    async with ClaudeSDKClient(options=options) as client:
        if feedback:
            prompt = f"""
            Original idea: {idea}
            
            Previous draft is saved in 'draft_v{iteration-1}.md'
            Feedback: {json.dumps(feedback, indent=2)}
            
            Please read the previous draft and revise it based on the feedback.
            Save the new version as 'draft_v{iteration}.md'
            """
        else:
            prompt = f"""
            Analyze this business idea: {idea}
            
            Research the market using WebSearch tool.
            Write a comprehensive 2000-word analysis.
            Save it as 'draft_v1.md'
            """
        
        await client.query(prompt)
        # The SDK handles all tool use automatically!
        # Analysis is saved to file by the agent itself

async def run_reviewer(iteration: int):
    """Run the Reviewer agent"""
    options = ClaudeCodeOptions(
        system_prompt=Path("prompts/reviewer.md").read_text(),
        allowed_tools=["Read", "Write"],
        working_directory="analyses"
    )
    
    async with ClaudeSDKClient(options=options) as client:
        prompt = f"""
        Review the analysis in 'draft_v{iteration}.md'
        
        Provide structured feedback and save it as 'feedback_v{iteration}.json'
        Include: satisfied (bool), critical_gaps (list), improvements (list)
        """
        
        await client.query(prompt)
        # Feedback is automatically saved to file

async def run_judge():
    """Run the Judge agent"""
    options = ClaudeCodeOptions(
        system_prompt=Path("prompts/judge.md").read_text(),
        allowed_tools=["Read", "Write"],
        working_directory="analyses"
    )
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query("""
        Read the final analysis in 'draft_final.md'
        
        Evaluate it against our 7 criteria and generate grades.
        Save the evaluation as 'evaluation.json'
        """)

async def run_pipeline(idea: str):
    """Complete pipeline with iterative review"""
    
    # Initial analysis
    await run_analyst(idea, iteration=1)
    
    # Iterative review loop
    for iteration in range(1, 4):  # Max 3 iterations
        await run_reviewer(iteration)
        
        # Check if reviewer is satisfied
        feedback_path = Path(f"analyses/feedback_v{iteration}.json")
        feedback = json.loads(feedback_path.read_text())
        
        if feedback.get("satisfied", False):
            break
            
        # Analyst revises based on feedback
        await run_analyst(idea, iteration + 1, feedback)
    
    # Rename final version
    Path(f"analyses/draft_v{iteration}.md").rename("analyses/draft_final.md")
    
    # Judge evaluates
    await run_judge()
    
    print("✅ Pipeline complete!")

# Run it
asyncio.run(run_pipeline("AI-powered fitness app for seniors"))
```

### Pros of claude-code-sdk approach

✅ **Built-in file operations** - Agents can read/write files directly
✅ **Automatic tool handling** - No need to parse tool use responses
✅ **Simpler code** - Less boilerplate
✅ **WebSearch works out of the box** - If configured
✅ **Working directory management** - Keeps files organized

### Cons

❌ Need Node.js + Claude Code CLI installed
❌ Less control over conversation flow
❌ Can't count tokens or track usage
❌ Harder to debug tool use

---

## Approach 2: Using anthropic-sdk-python (MORE CONTROL)

```python
# main.py - Using anthropic-sdk-python
import asyncio
import json
from pathlib import Path
from anthropic import AsyncAnthropic
from typing import Dict, Any

class BaseAgent:
    def __init__(self, name: str, prompt_file: str):
        self.name = name
        self.client = AsyncAnthropic()
        self.system_prompt = Path(f"prompts/{prompt_file}").read_text()
    
    async def query(self, messages: list, tools: list = None) -> str:
        """Query Claude and handle tool use manually"""
        kwargs = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 4000,
            "system": self.system_prompt,
            "messages": messages
        }
        
        if tools:
            kwargs["tools"] = tools
        
        response = await self.client.messages.create(**kwargs)
        
        # Handle tool use manually
        content = response.content[0]
        if hasattr(content, 'tool_use'):
            # We need to execute the tool ourselves
            tool_result = await self.execute_tool(content.tool_use)
            # Then continue the conversation with the result
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_result})
            return await self.query(messages)  # Recursive call
        
        return content.text
    
    async def execute_tool(self, tool_use):
        """Manually execute tools - lots of code needed here"""
        if tool_use.name == "WebSearch":
            # Call MCP server or search API
            pass
        elif tool_use.name == "Read":
            # Read file
            pass
        elif tool_use.name == "Write":
            # Write file
            pass
        # ... etc

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("analyst", "analyst.md")
    
    async def analyze(self, idea: str, iteration: int = 1, feedback: dict = None):
        messages = []
        
        if feedback:
            # Read previous draft manually
            prev_draft = Path(f"analyses/draft_v{iteration-1}.md").read_text()
            messages.append({
                "role": "user",
                "content": f"""
                Original idea: {idea}
                Previous draft: {prev_draft}
                Feedback: {json.dumps(feedback, indent=2)}
                Please revise the analysis.
                """
            })
        else:
            messages.append({
                "role": "user",
                "content": f"Analyze this business idea: {idea}"
            })
        
        # Define tools manually
        tools = [{
            "name": "WebSearch",
            "description": "Search the web",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }]
        
        analysis = await self.query(messages, tools)
        
        # Save manually
        Path(f"analyses/draft_v{iteration}.md").write_text(analysis)
        
        return analysis

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__("reviewer", "reviewer.md")
    
    async def review(self, iteration: int):
        # Read the draft manually
        draft = Path(f"analyses/draft_v{iteration}.md").read_text()
        
        messages = [{
            "role": "user",
            "content": f"Review this analysis:\n\n{draft}\n\nProvide structured feedback."
        }]
        
        feedback_text = await self.query(messages)
        
        # Parse and structure the feedback manually
        # This is error-prone and requires parsing logic
        feedback = self.parse_feedback(feedback_text)
        
        # Save manually
        Path(f"analyses/feedback_v{iteration}.json").write_text(
            json.dumps(feedback, indent=2)
        )
        
        return feedback
    
    def parse_feedback(self, text: str) -> dict:
        """Parse unstructured text into structured feedback"""
        # Complex parsing logic needed here
        # Error-prone without guaranteed structure
        pass

# ... Similar for Judge and Synthesizer agents

async def run_pipeline(idea: str):
    """Pipeline with manual orchestration"""
    analyst = AnalystAgent()
    reviewer = ReviewerAgent()
    judge = JudgeAgent()
    
    # Initial analysis
    await analyst.analyze(idea)
    
    # Review loop
    for iteration in range(1, 4):
        feedback = await reviewer.review(iteration)
        
        if feedback.get("satisfied", False):
            break
            
        await analyst.analyze(idea, iteration + 1, feedback)
    
    # ... rest of pipeline
```

### Pros of anthropic-sdk approach

✅ Full control over conversation flow
✅ Token counting and usage tracking
✅ No Node.js dependency
✅ Better error handling
✅ Can customize every aspect

### Cons of anthropic-sdk approach

❌ **Much more code to write** - Tool execution, file I/O, parsing
❌ **Error-prone** - Manual parsing of responses
❌ **No built-in tools** - Must implement Read, Write, WebSearch ourselves
❌ **Complex tool handling** - Recursive calls for tool use

---

## The Verdict: Why claude-code-sdk is Actually Better for This Project

After implementing both approaches, I'm changing my recommendation. **claude-code-sdk-python is the better choice** for your project because:

1. **Dramatic Simplicity**: The claude-code-sdk version is ~50% less code
2. **Built-in Tools**: Read, Write, and WebSearch just work
3. **Automatic Tool Handling**: No manual parsing or execution needed
4. **File Management**: Working directory feature keeps things organized
5. **You Don't Need Production Features**: Token counting, detailed error handling aren't critical

## The "Gaps" Aren't Actually Problems

Looking at the gaps I highlighted:

| "Gap" | Why It's Not a Problem |
|-------|------------------------|
| No direct conversation control | The context manager + query pattern is sufficient |
| No token counting | Not needed for non-production |
| Requires Node.js | One-time setup, worth the simplicity |
| Async-only | Python async/await is standard now |
| No production error handling | You explicitly don't need production-ready |
| Can't maintain separate contexts | Each agent gets its own client - works fine |

## Revised Recommendation

**Use claude-code-sdk-python**. The simplicity gains far outweigh the minor limitations. You'll ship faster and have less code to maintain.

The anthropic-sdk approach would make sense if you needed:

- Detailed token tracking
- Custom retry logic
- Complex conversation branching
- Integration with existing systems

But for a learning project with 4 agents doing sequential processing, claude-code-sdk is the clear winner.
