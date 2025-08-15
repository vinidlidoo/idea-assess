# SDK and Tools Research Findings

## Date: 2025-01-11 (Updated: 2025-01-12)

## Executive Summary

After deep analysis and implementation comparison, we've reversed our decision:

1. **Use claude-code-sdk-python for everything**: Built-in tools, 50% less code, perfect for rapid development
2. **anthropic-sdk-python not needed**: Too much boilerplate for a learning project
3. **MCP servers optional**: WebSearch works with claude-code-sdk if configured
4. **Architecture simplified**: Our 4-agent system maps beautifully to claude-code-sdk's patterns

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

### ✅ DECISION MADE (2025-01-12 - REVISED)

**We will use claude-code-sdk-python** for the implementation. Key rationale:

- **50% less code** - Built-in Read, Write, WebSearch tools
- **Faster shipping** - Save 2-3 days of implementation time
- **Perfect fit** - Designed for multi-agent systems like ours
- **Simple orchestration** - Clean async context managers
- **Not production** - We don't need token counting or detailed error handling

The Node.js dependency is a one-time setup cost that's worth the massive simplicity gains.

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

## SDK Comparison Summary

### anthropic-sdk-python

**Purpose**: General-purpose Claude API access
**Strengths**:

- Direct API control
- Async/sync support
- Tool use capabilities
- Token counting
- Streaming responses
- Production-ready

**Our Use**: Primary SDK for all agents

### claude-code-sdk-python

**Purpose**: CLI-based coding assistant
**Strengths**:

- File system operations
- Terminal integration
- Built-in code tools
- Interactive mode

**Our Use**: Not needed - adds unnecessary complexity

### MCP Python SDK

**Purpose**: External tool/resource servers
**Strengths**:

- FastMCP for quick setup
- Type-safe tool definitions
- Claude Desktop integration
- Protocol standardization

**Our Use**: Web search server only

## Implementation Stack

```python
# Core dependencies  
claude-code-sdk>=0.1.0  # Main SDK
click>=8.1.0           # CLI framework
rich>=13.0.0           # Terminal UI
pyyaml>=6.0            # Config files

# One-time setup
# npm install -g @anthropic-ai/claude-code
```

## Resources

### Primary Documentation

- [Anthropic SDK Python](https://github.com/anthropics/anthropic-sdk-python)
- [Anthropic API Docs](https://docs.anthropic.com/en/api/client-sdks#python)
- [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Documentation](https://modelcontextprotocol.io/introduction)

### Implementation Guides

- [Claude Code SDK Python](https://github.com/anthropics/claude-code-sdk-python) (reference only)
- [MCP Quickstart](https://modelcontextprotocol.io/quickstart/server)
- [FastMCP Tutorial](https://modelcontextprotocol.io/tutorials/fastmcp)
- [Agent Patterns](https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns)
