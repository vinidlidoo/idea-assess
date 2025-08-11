# SDK and Tools Research Findings

## Date: 2025-01-11

## Executive Summary

Research reveals multiple viable approaches for implementing our business idea evaluation system. Key findings:

1. **Avoid reinventing the wheel**: Existing frameworks like LangGraph and CrewAI provide robust multi-agent orchestration
2. **Claude SDK has strong agent support**: Native subagent patterns, tool use, and MCP integration
3. **MCP protocol is production-ready**: Python SDK 1.2.0+ with FastMCP simplifies tool/resource creation
4. **Consider hybrid approach**: Use Claude SDK for core agents, MCP for external integrations

## Existing Solutions Analysis

### Commercial Products (for reference)

- **RebeccAi**: Full business plan generation from ideas
- **VenturusAI**: SWOT, PESTEL, Porter's Five Forces analysis
- **DimeADozen.ai**: Rapid business validation reports

### Open Source Frameworks

#### 1. LangGraph (LangChain)

- **Pros**: Production-ready, supervisor/swarm patterns, AWS Bedrock integration
- **Cons**: Not Claude-native, adds complexity layer
- **Use case**: If we need complex graph-based workflows

#### 2. CrewAI

- **Pros**: Role-playing agents, minimal resource usage, highly customizable
- **Cons**: Another abstraction layer over Claude
- **Use case**: If we need sophisticated agent collaboration

#### 3. Claude Code Sub-Agents

- **Pros**: Native Claude integration, proven patterns, Anthropic-supported
- **Cons**: Limited to Claude ecosystem
- **Use case**: Our primary approach (recommended)

## Claude SDK Capabilities

### Core Features (Python SDK)

```python
from claude_code_sdk import query, ClaudeCodeOptions

options = ClaudeCodeOptions(
    system_prompt="You are a business analyst",
    allowed_tools=["Read", "Write", "WebSearch"],
    permission_mode='acceptEdits',
    max_turns=10
)
```

### Subagent Architecture

- Store as Markdown files with YAML frontmatter
- Specialized system prompts per agent
- Tool permissions per agent
- Native support for agent hand-offs

### Best Practices (from Anthropic)

1. **Research before coding**: Read files first, plan approach
2. **Use subagents for complex tasks**: Preserves context
3. **Test-driven development**: Write tests first for better results
4. **CLAUDE.md file**: Auto-loaded context for project specifics

## MCP Protocol Integration

### Setup Requirements

```bash
# Python MCP SDK 1.2.0+
uv add "mcp[cli]" httpx
```

### FastMCP Pattern

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BusinessEvaluator")

@mcp.tool()
def analyze_market(idea: str) -> dict:
    """Analyze market potential for business idea"""
    # Implementation here
    return analysis

@mcp.resource("analysis://{idea_slug}")
def get_analysis(idea_slug: str) -> str:
    """Retrieve stored analysis"""
    return content
```

### Integration with Claude Desktop

- Configure in `claude_desktop_config.json`
- Servers run as separate processes
- Tools exposed automatically to Claude

## Recommended Architecture

### Option 1: Pure Claude SDK (Simplest)

```text
CLI → Claude SDK → Subagents (Analyst, Reviewer, Judge, Synthesizer)
                 ↓
            Local Files/API calls
```

**Pros**: Simple, direct, Anthropic-supported
**Cons**: Limited to Claude's built-in capabilities

### Option 2: Claude SDK + MCP (Balanced)

```text
CLI → Claude SDK → Subagents
                 ↓
            MCP Servers → External Tools (Web search, APIs)
```

**Pros**: Extensible, clean separation, standard protocol
**Cons**: Slightly more complex setup

### Option 3: LangGraph Integration (Complex)

```text
CLI → LangGraph → Supervisor Agent
                ↓
        Claude Subagents (via SDK)
```

**Pros**: Advanced orchestration, proven patterns
**Cons**: Extra dependency, learning curve

## Decision Recommendations

### For Our Project (P0 - Sequential Processing)

1. **Use Claude SDK directly** - Simplest, fastest to implement
2. **Implement subagents as Markdown files** - Native pattern
3. **Add MCP for web search** - Standard protocol for external data
4. **Skip LangGraph/CrewAI initially** - Unnecessary complexity for P0

### ✅ DECISION MADE (2025-01-11)

**We will use Claude SDK + MCP** for the implementation. This decision is final and aligns with our aggressive timeline and learning objectives.

### For Future (P1 - Parallel Processing)

Consider LangGraph supervisor pattern for parallel agent execution

## Implementation Timeline Impact

Using existing tools can save 2-3 days:

- **Day 1**: Setup Claude SDK + MCP basics (vs 2-3 days custom)
- **Days 2-3**: Agent implementation focus
- **Days 4-5**: Integration and testing
- **Days 6-7**: Polish and edge cases

## Open Questions Resolved

1. **Q: How to structure agent prompts?**
   A: Use subagent Markdown files with YAML frontmatter

2. **Q: Best approach for web search?**
   A: MCP server with web search tool

3. **Q: Handle partial failures?**
   A: Claude SDK has built-in retry/error handling

4. **Q: Checkpoint/resume?**
   A: Use file-based state management

## Next Steps

1. Set up basic Claude SDK project structure
2. Create subagent templates for our 4 agents
3. Implement MCP server for web search
4. Build CLI wrapper for the pipeline

## Resources

- [Claude Code SDK Python](https://github.com/anthropics/claude-code-sdk-python)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [MCP Quickstart](https://modelcontextprotocol.io/quickstart/server)
