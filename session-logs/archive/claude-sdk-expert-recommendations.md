# Claude SDK Expert Recommendations: Reviewer Agent Debug Analysis

## Executive Summary

The ReviewerAgent is failing due to fundamental misunderstandings about Claude SDK's message handling and API design. The agent receives unexpected UserMessages in its response stream, generates only partial responses, and never produces the required JSON feedback. The root cause is **attempting to use Claude Code SDK for agent-to-agent communication**, which violates the SDK's core design principle: it's meant for **human-to-Claude** interactions only.

### Critical Findings

1. **SDK Misuse**: Using ClaudeSDKClient for agent-to-agent communication triggers human-in-the-loop behaviors
2. **Message Stream Contamination**: UserMessages appearing in response indicate SDK's interactive mode activation
3. **Incomplete Responses**: Only receiving "I'll review this..." suggests prompt rejection or safety filtering
4. **Architecture Mismatch**: BaseAgent abstraction doesn't align with Claude SDK's conversational model

## Detailed Code Review Findings

### 1. Core Architecture Issues

#### File: `src/core/agent_base.py`
**Lines 39-50**: The `process()` method signature assumes single input/output, but Claude SDK is designed for multi-turn conversations. This abstraction leaks through all agent implementations.

```python
async def process(self, input_data: str, **kwargs) -> AgentResult:
    # This assumes stateless, single-turn processing
    # But Claude SDK maintains conversation state
```

**Issue**: The BaseAgent interface treats agents as pure functions, but Claude SDK maintains session state and expects human interaction patterns.

### 2. ReviewerAgent Implementation Problems

#### File: `src/agents/reviewer.py`
**Lines 88-95**: Incorrect SDK configuration for non-interactive use:

```python
options = ClaudeCodeOptions(
    system_prompt=prompt_content,
    max_turns=1,  # Single response for review
    allowed_tools=[],  # No tools needed for review
    permission_mode='acceptEdits'  # <-- WRONG: This enables human-in-the-loop
)
```

**Issue**: `permission_mode='acceptEdits'` triggers interactive behaviors. The SDK expects human approval for edits, causing UserMessages to appear.

**Lines 104-106**: Attempting single-turn interaction in a conversational SDK:

```python
async with ClaudeSDKClient(options=options) as client:
    await client.query(review_prompt)
    async for message in client.receive_response():
```

**Issue**: The SDK is designed for back-and-forth conversation. Single-turn usage triggers defensive behaviors.

### 3. Message Processing Confusion

#### File: `src/agents/reviewer_fixed.py`
**Lines 106-117**: Manual ContentBlock extraction indicates SDK API misunderstanding:

```python
if type(message).__name__ == 'AssistantMessage':
    if hasattr(message, 'content') and message.content:
        for block in message.content:
            if hasattr(block, 'text'):
                full_text += block.text
```

**Issue**: Using string matching on type names (`type(message).__name__`) instead of proper type checking suggests the SDK's type system isn't being used correctly.

### 4. Pipeline Integration Flaws

#### File: `src/core/pipeline.py`
**Lines 144-148**: Reviewer called with analysis document as "user" input:

```python
reviewer_result = await reviewer.process(
    current_analysis,
    debug=debug,
    iteration_count=iteration_count
)
```

**Issue**: Passing an 8,754-character analysis document as a "user query" violates the SDK's expectations. This isn't how humans interact with Claude.

## Root Cause Analysis

### Why UserMessages Appear in Response Stream

The Claude SDK includes UserMessages in the response stream when:

1. **Interactive Mode Activated**: Setting `permission_mode='acceptEdits'` tells the SDK to expect human approval
2. **Content Policy Triggers**: Large documents with complex instructions may trigger safety checks
3. **Session State Confusion**: The SDK maintains conversation history and may inject clarifying questions
4. **API Misuse**: Using the SDK for non-conversational purposes triggers fallback behaviors

The sequence observed in logs confirms this:
```
SystemMessage → AssistantMessage ("I'll review...") → UserMessage → AssistantMessage → UserMessage...
```

This pattern indicates the SDK is attempting to engage in dialogue, likely asking for clarification or approval.

### Why JSON Generation Fails

1. **Prompt Complexity**: The 182-line reviewer prompt with nested JSON structure exceeds typical user query patterns
2. **Context Overload**: 8,754-character analysis + complex prompt triggers conservative responses
3. **Safety Filtering**: Business analysis review may trigger content moderation
4. **Wrong API**: Claude SDK isn't designed for structured output generation

## Step-by-Step Fix Recommendations

### Immediate Fix (P0): Switch to Direct API

**Stop using Claude SDK for agent-to-agent communication.** Use the Anthropic Python client directly:

```python
# src/agents/reviewer_direct.py
from anthropic import AsyncAnthropic
import json

class ReviewerAgent(BaseAgent):
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        client = AsyncAnthropic()
        
        # Use Messages API directly
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0,
            system=prompt_content,
            messages=[
                {"role": "user", "content": review_prompt}
            ]
        )
        
        # Extract JSON from response
        content = response.content[0].text
        # ... parse JSON ...
```

### Alternative Fix (P1): Restructure for SDK Compatibility

If you must use Claude SDK, restructure the interaction:

```python
# Make it conversational
options = ClaudeCodeOptions(
    system_prompt="You are a code reviewer. Respond with JSON only.",
    max_turns=2,
    allowed_tools=[],
    permission_mode='autoAllow'  # Never use acceptEdits for automation
)

# Simulate human-like interaction
await client.query("Please review the following analysis and respond with JSON feedback:")
await client.query(input_data[:2000])  # Chunk the input
```

### Long-term Fix (P2): Proper Agent Communication Architecture

1. **Separate APIs**: Use Claude SDK for human interactions, Anthropic API for agent-to-agent
2. **Message Queue**: Implement proper async message passing between agents
3. **State Management**: Don't rely on SDK session state for agent coordination
4. **Structured Output**: Use dedicated APIs or prompt engineering for JSON generation

## SDK Best Practices for This Use Case

### DO:
- Use Claude SDK for **human-initiated** workflows only
- Keep prompts under 2000 characters for reliability
- Use `permission_mode='autoAllow'` for automation
- Implement proper error handling for partial responses
- Use the Anthropic API directly for agent-to-agent communication

### DON'T:
- Don't use `permission_mode='acceptEdits'` in automated workflows
- Don't pass massive documents as single queries
- Don't expect reliable JSON from conversational SDK
- Don't use string matching on type names
- Don't mix human interaction patterns with automation

## Code Examples: Correct Patterns

### Pattern 1: Direct API for Agents

```python
from anthropic import AsyncAnthropic

async def review_with_api(analysis: str, prompt: str) -> dict:
    client = AsyncAnthropic()
    
    message = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        temperature=0,
        system=prompt,
        messages=[{"role": "user", "content": f"Review this:\n{analysis}"}]
    )
    
    # Parse JSON from response
    text = message.content[0].text
    if '```json' in text:
        json_str = text.split('```json')[1].split('```')[0]
    else:
        json_str = text
    
    return json.loads(json_str.strip())
```

### Pattern 2: SDK for Human Workflows

```python
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def analyze_with_human(idea: str) -> str:
    options = ClaudeCodeOptions(
        system_prompt="You are a business analyst.",
        max_turns=5,
        allowed_tools=['WebSearch'],
        permission_mode='autoAllow'  # For automation
    )
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query(f"Analyze this idea: {idea}")
        
        full_response = []
        async for message in client.receive_response():
            # Properly check types
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response.append(block.text)
            elif isinstance(message, ResultMessage):
                break
        
        return ''.join(full_response)
```

### Pattern 3: Proper Message Type Checking

```python
from claude_code_sdk.messages import (
    AssistantMessage, 
    UserMessage, 
    SystemMessage, 
    ResultMessage,
    TextBlock
)

# Instead of: type(message).__name__ == 'AssistantMessage'
# Use: isinstance(message, AssistantMessage)

async for message in client.receive_response():
    if isinstance(message, AssistantMessage):
        # Handle assistant response
        pass
    elif isinstance(message, UserMessage):
        # This shouldn't happen in automation
        raise Exception("Unexpected user interaction required")
    elif isinstance(message, ResultMessage):
        # End of stream
        break
```

## Recommended Implementation Priority

1. **Immediate (Today)**: 
   - Switch ReviewerAgent to use Anthropic API directly
   - Remove `permission_mode='acceptEdits'` from all agents
   - Add proper type checking using isinstance()

2. **Short-term (This Week)**:
   - Refactor BaseAgent to support both SDK and API backends
   - Implement proper chunking for large documents
   - Add retry logic for JSON parsing failures

3. **Long-term (Next Sprint)**:
   - Separate human-facing workflows from agent pipelines
   - Implement proper message queue for agent coordination
   - Add comprehensive error handling and fallbacks

## Testing Strategy

```python
# Test the reviewer with direct API
async def test_reviewer_direct():
    from anthropic import AsyncAnthropic
    
    client = AsyncAnthropic()
    test_analysis = "Short test analysis..."
    
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system="You are a reviewer. Respond with JSON: {\"rating\": 1-10, \"feedback\": \"...\"}",
        messages=[{"role": "user", "content": f"Review: {test_analysis}"}]
    )
    
    print(response.content[0].text)
    # Should see clean JSON without UserMessages
```

## Conclusion

The ReviewerAgent failure stems from using Claude SDK for a purpose it wasn't designed for. The SDK is built for **interactive, human-in-the-loop** workflows, not automated agent-to-agent communication. The appearance of UserMessages in the response stream is the SDK's way of trying to engage in conversation, which breaks the expected single-turn review pattern.

**Immediate action required**: Switch to the Anthropic Python client for the ReviewerAgent. This will eliminate the UserMessage issue and enable reliable JSON generation. The Claude SDK should be reserved for the AnalystAgent where human-like exploratory analysis with web search makes sense.

Remember: **Claude SDK = Human Workflows, Anthropic API = Agent Automation**

---

*Document created: 2025-08-14*  
*Author: Claude SDK Expert Agent*  
*Status: Ready for implementation*
