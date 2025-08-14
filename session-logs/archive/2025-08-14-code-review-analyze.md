# Code Review: analyze.py - Comprehensive Analysis and Refactoring Recommendations

## Overall Assessment

The `analyze.py` file represents a well-implemented Phase 1 prototype that successfully accomplishes its core objectives. The code demonstrates solid engineering practices with clean dataclass usage, comprehensive error handling, and thoughtful async/await patterns. However, as the system prepares to expand into a multi-agent architecture, several structural improvements and refactoring opportunities will significantly ease Phase 2 implementation.

**Strengths:** Well-structured monolithic implementation, excellent debug logging, robust signal handling, and clean CLI interface.

**Primary Concerns:** Monolithic structure will impede multi-agent expansion, high complexity in the main analysis function, and some hard-coded configurations that should be externalized.

## Critical Issues

### 1. **Monolithic Function Complexity** (Lines 204-487)

The `analyze_idea()` function is 283 lines long and handles multiple responsibilities:
- SDK client management
- Message processing and parsing
- Debug logging coordination
- Signal handling
- Result aggregation
- Progress tracking

**Impact:** This will make it extremely difficult to extract reusable components for other agents.

**Recommendation:** Break into specialized functions:
```python
async def setup_analysis_session(idea: str, options: AnalysisOptions) -> AnalysisSession:
    """Initialize analysis session with client and logging"""

async def process_claude_messages(client: ClaudeSDKClient, logger: DebugLogger) -> AnalysisResult:
    """Handle message stream processing"""

def extract_content_from_messages(messages: List[Message]) -> str:
    """Extract and aggregate text content from message stream"""
```

### 2. **Hard-coded Agent Logic** (Lines 245-270, 275-280)

The prompt construction and tool configuration are hard-coded for the Analyst agent:
```python
prompt_file = f"analyst_{prompt_version}.md"
allowed_tools = ["WebSearch"] if use_websearch else []
```

**Impact:** Every new agent will require code changes to this core module.

**Recommendation:** Extract to agent-specific configuration system.

### 3. **Missing Validation for Critical Outputs** (Lines 417-446)

The function returns `AnalysisResult` without validating that the content meets basic quality thresholds:
- No minimum word count verification
- No structure validation (headings, sections)
- No content quality checks

**Impact:** Could allow empty or malformed analyses to pass through.

## Architecture & Design Feedback

### 1. **Recommended Module Structure for Phase 2**

Current monolithic approach should evolve to:

```
src/
├── core/
│   ├── __init__.py
│   ├── agent_base.py      # BaseAgent class
│   ├── client_manager.py  # SDK client lifecycle
│   ├── message_processor.py  # Message parsing logic
│   └── config.py         # Configuration management
├── agents/
│   ├── __init__.py
│   ├── analyst.py        # Current analyze_idea logic
│   ├── reviewer.py       # Phase 2
│   ├── judge.py         # Phase 3
│   └── synthesizer.py   # Phase 4
├── utils/
│   ├── __init__.py
│   ├── debug_logging.py  # DebugLogger extraction
│   ├── file_operations.py  # save_analysis, etc.
│   └── text_processing.py  # create_slug, etc.
└── cli/
    ├── __init__.py
    └── main.py           # CLI entry points
```

### 2. **Agent Communication Interface**

Design a consistent interface all agents can implement:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

class AgentResult:
    """Standard result container for all agents"""
    content: str
    metadata: Dict[str, Any]
    output_path: Optional[Path]
    success: bool
    error_message: Optional[str]

class BaseAgent(ABC):
    """Base class for all business idea evaluation agents"""
    
    def __init__(self, name: str, config: AgentConfig):
        self.name = name
        self.config = config
        self.working_dir = Path(f"analyses/{name}")
        
    @abstractmethod
    async def process(self, input_data: Any) -> AgentResult:
        """Process input and return structured result"""
        
    @abstractmethod
    def get_prompt_template(self) -> str:
        """Return agent-specific prompt template"""
        
    def get_allowed_tools(self) -> List[str]:
        """Return tools this agent needs"""
        return ["Read", "Write"]  # Default
```

### 3. **Configuration Management Overhaul**

Extract hard-coded values to configuration:

```python
# config/agent_configs.py
@dataclass
class AgentConfig:
    name: str
    prompt_file: str
    allowed_tools: List[str]
    max_turns: int = 15
    word_limits: Optional[Dict[str, int]] = None
    
AGENT_CONFIGS = {
    "analyst": AgentConfig(
        name="analyst",
        prompt_file="analyst_v3.md",
        allowed_tools=["Read", "Write", "WebSearch"],
        max_turns=15,
        word_limits={"min": 1500, "target": 2500, "max": 3000}
    ),
    "reviewer": AgentConfig(
        name="reviewer", 
        prompt_file="reviewer.md",
        allowed_tools=["Read", "Write"],
        max_turns=10
    )
    # ... other agents
}
```

## Code Quality Improvements

### 1. **Type Hints Enhancement** (Throughout file)

Current type hints are good but can be more specific:

```python
# Current (Line 204)
async def analyze_idea(
    idea: str, 
    debug: bool = False,
    use_websearch: bool = True,
    prompt_version: str = "v2"
) -> Optional[AnalysisResult]:

# Improved
from typing import Literal
from enum import Enum

class PromptVersion(Enum):
    V1 = "v1"
    V2 = "v2" 
    V3 = "v3"

async def analyze_idea(
    idea: str,
    debug: bool = False,
    use_websearch: bool = True,
    prompt_version: PromptVersion = PromptVersion.V3
) -> Optional[AnalysisResult]:
```

### 2. **Magic Numbers Elimination** (Lines 38-46)

Several magic numbers should be constants:

```python
# Current scattered throughout
if len(msg_content) > 500:
    content_preview.append(msg_content[:500] + "...")

# Improved
class Constants:
    CONTENT_PREVIEW_MAX_LENGTH = 500
    PREVIEW_TRUNCATION_SUFFIX = "..."
    MIN_ANALYSIS_LENGTH = 100
    WEBSEARCH_TIMEOUT_WARNING = "WebSearch may take 30-120s per search"
    
if len(msg_content) > Constants.CONTENT_PREVIEW_MAX_LENGTH:
    preview = msg_content[:Constants.CONTENT_PREVIEW_MAX_LENGTH]
    content_preview.append(preview + Constants.PREVIEW_TRUNCATION_SUFFIX)
```

### 3. **Error Message Improvements** (Lines 467-473)

Current error handling could be more informative:

```python
# Current
except Exception as e:
    print(f"\n❌ Error during analysis: {e}")
    
# Improved  
except ClaudeSDKError as e:
    print(f"\n❌ Claude SDK Error: {e}")
    logger.log_event(f"SDK Error: {e}", {"error_type": "sdk", "recoverable": e.is_retryable})
except WebSearchTimeoutError as e:
    print(f"\n⏱️ WebSearch Timeout: {e}")
    logger.log_event(f"WebSearch timeout: {e}", {"error_type": "websearch_timeout"})
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    logger.log_event(f"Unexpected error: {e}", {"error_type": "unexpected"})
    if debug:
        import traceback
        traceback.print_exc()
```

### 4. **Documentation Gaps** (Various functions)

Several functions lack comprehensive docstrings:

```python
# Current (Line 176)
def extract_session_id(message: Any) -> Optional[str]:
    """Extract session ID from a SystemMessage."""

# Improved
def extract_session_id(message: Any) -> Optional[str]:
    """
    Extract Claude SDK session ID from a SystemMessage for debug tracking.
    
    Searches for session_id in the message data attribute using regex matching.
    This ID is used to correlate debug logs with specific Claude conversations.
    
    Args:
        message: Any message object, typically SystemMessage from Claude SDK
        
    Returns:
        Session ID string if found in message data, None if not found or 
        if message is not a SystemMessage
        
    Example:
        >>> msg = SystemMessage(data="{'session_id': 'abc-123'}")
        >>> extract_session_id(msg)
        'abc-123'
    """
```

## Maintainability Improvements

### 1. **Message Processing Complexity** (Lines 296-404)

The message processing loop is extremely complex and handles multiple message types with deeply nested conditional logic. This needs refactoring:

```python
# Proposed refactor
class MessageProcessor:
    """Handles processing of Claude SDK message streams"""
    
    def __init__(self, logger: DebugLogger, use_websearch: bool):
        self.logger = logger
        self.use_websearch = use_websearch
        self.handlers = {
            "UserMessage": self._handle_user_message,
            "ResultMessage": self._handle_result_message,
            "SystemMessage": self._handle_system_message
        }
    
    async def process_message_stream(self, client: ClaudeSDKClient) -> MessageProcessingResult:
        """Process entire message stream and return aggregated results"""
        result_text = []
        message_count = 0
        search_count = 0
        
        async for message in client.receive_response():
            message_count += 1
            message_type = type(message).__name__
            
            handler = self.handlers.get(message_type, self._handle_unknown_message)
            processing_result = await handler(message, message_count)
            
            result_text.extend(processing_result.text_content)
            search_count += processing_result.search_count
            
            if processing_result.is_final:
                break
                
        return MessageProcessingResult(
            text_content="".join(result_text),
            message_count=message_count,
            search_count=search_count
        )
```

### 2. **Configuration Dependencies** (Lines 32-46)

Hard-coded paths and configuration create maintenance burdens:

```python
# Current
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "config" / "prompts"
ANALYSES_DIR = PROJECT_ROOT / "analyses"
LOGS_DIR = PROJECT_ROOT / "logs"

# Improved - Make configurable
@dataclass
class ProjectPaths:
    root: Path
    prompts: Path
    analyses: Path
    logs: Path
    
    @classmethod
    def from_config(cls, config_path: Optional[Path] = None) -> "ProjectPaths":
        if config_path and config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return cls(**config["paths"])
        
        # Default paths
        root = Path(__file__).parent.parent
        return cls(
            root=root,
            prompts=root / "config" / "prompts",
            analyses=root / "analyses", 
            logs=root / "logs"
        )
```

### 3. **Testability Issues**

Current structure makes unit testing difficult:
- Global variables and path dependencies
- Large functions with multiple responsibilities
- No dependency injection

**Recommendation:** Use dependency injection pattern:

```python
class AnalysisService:
    """Main service for conducting business idea analyses"""
    
    def __init__(
        self,
        client_factory: Callable[[], ClaudeSDKClient],
        file_service: FileService,
        config_service: ConfigService,
        logger_factory: Callable[[str], DebugLogger]
    ):
        self.client_factory = client_factory
        self.file_service = file_service
        self.config = config_service
        self.logger_factory = logger_factory
        
    async def analyze_idea(self, request: AnalysisRequest) -> AnalysisResult:
        """Main analysis method with injected dependencies"""
```

## Scalability for Phase 2

### 1. **Agent Registry Pattern**

Prepare for multiple agents with a registry system:

```python
# core/agent_registry.py
class AgentRegistry:
    """Central registry for all available agents"""
    
    def __init__(self):
        self._agents = {}
    
    def register_agent(self, name: str, agent_class: Type[BaseAgent]):
        """Register an agent implementation"""
        self._agents[name] = agent_class
    
    def get_agent(self, name: str, config: AgentConfig) -> BaseAgent:
        """Get configured agent instance"""
        if name not in self._agents:
            raise ValueError(f"Unknown agent: {name}")
        return self._agents[name](config)
    
    def list_available(self) -> List[str]:
        """List all registered agent names"""
        return list(self._agents.keys())

# Usage in main
registry = AgentRegistry()
registry.register_agent("analyst", AnalystAgent)
registry.register_agent("reviewer", ReviewerAgent)  # Phase 2
registry.register_agent("judge", JudgeAgent)        # Phase 3
```

### 2. **Pipeline Orchestration Interface**

Design pipeline that can chain agents:

```python
# core/pipeline.py
class Pipeline:
    """Orchestrates multi-agent business idea evaluation workflow"""
    
    def __init__(self, registry: AgentRegistry, config: PipelineConfig):
        self.registry = registry
        self.config = config
        
    async def execute(self, idea: str) -> PipelineResult:
        """Execute full evaluation pipeline"""
        context = PipelineContext(original_idea=idea)
        
        # Phase 1: Analysis
        analyst = self.registry.get_agent("analyst", self.config.analyst)
        analysis_result = await analyst.process(idea)
        context.add_result("analysis", analysis_result)
        
        # Phase 2: Review iterations (when implemented)
        if self.config.enable_review:
            reviewer = self.registry.get_agent("reviewer", self.config.reviewer)
            for iteration in range(self.config.max_review_iterations):
                review_result = await reviewer.process(context.get_latest("analysis"))
                context.add_result(f"review_{iteration}", review_result)
                
                if review_result.metadata.get("satisfied", False):
                    break
                    
                # Analyst revision
                revision_prompt = self._build_revision_prompt(context, review_result)
                analysis_result = await analyst.process(revision_prompt)
                context.add_result("analysis", analysis_result)
        
        return PipelineResult(context=context, success=True)
```

### 3. **Common Utilities Extraction**

Extract utilities that all agents will need:

```python
# utils/claude_helpers.py
class ClaudeClientManager:
    """Manages Claude SDK client lifecycle and common operations"""
    
    @staticmethod
    async def create_client(config: AgentConfig) -> ClaudeSDKClient:
        """Create configured Claude client for an agent"""
        options = ClaudeCodeOptions(
            system_prompt=load_prompt(config.prompt_file),
            max_turns=config.max_turns,
            allowed_tools=config.allowed_tools,
        )
        return ClaudeSDKClient(options=options)
    
    @staticmethod
    async def execute_with_retries(
        client: ClaudeSDKClient,
        prompt: str,
        max_retries: int = 3
    ) -> Any:
        """Execute query with automatic retry logic"""
        
# utils/validation.py  
class ContentValidator:
    """Validates agent outputs meet quality requirements"""
    
    @staticmethod
    def validate_analysis(content: str, requirements: Dict[str, Any]) -> ValidationResult:
        """Validate analysis content meets requirements"""
        
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """Validate JSON output matches expected schema"""
```

## Performance & Reliability

### 1. **Memory Usage Optimization** (Lines 388-404)

The current approach stores all message content in memory:

```python
result_text.append(block.text)  # Potentially large strings
```

**Recommendation:** Use streaming file writing for large analyses:

```python
class StreamingWriter:
    """Write analysis content directly to file as it arrives"""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.file_handle = None
    
    async def __aenter__(self):
        self.file_handle = open(self.output_path, 'w')
        return self
        
    async def append_content(self, content: str):
        self.file_handle.write(content)
        self.file_handle.flush()  # Ensure immediate writing
```

### 2. **WebSearch Timeout Handling** (Lines 292-295, 390-395)

Current WebSearch handling could be improved:

```python
# Add timeout and retry logic
class WebSearchManager:
    def __init__(self, timeout: int = 120, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def execute_search_with_timeout(self, query: str) -> Optional[Dict[str, Any]]:
        """Execute WebSearch with timeout and retry"""
        for attempt in range(self.max_retries + 1):
            try:
                async with asyncio.timeout(self.timeout):
                    # Execute search
                    return await self._perform_search(query)
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None  # All retries failed
```

### 3. **Signal Handling Enhancement** (Lines 233-242)

Current signal handling could be more robust:

```python
class GracefulShutdownManager:
    """Handles graceful shutdown with state preservation"""
    
    def __init__(self, logger: DebugLogger):
        self.logger = logger
        self.shutdown_requested = False
        self.cleanup_tasks = []
    
    def register_cleanup_task(self, coro):
        """Register cleanup task to run on shutdown"""
        self.cleanup_tasks.append(coro)
    
    async def handle_shutdown(self, signum, frame):
        """Handle shutdown signal with cleanup"""
        self.logger.log_event(f"Shutdown signal received: {signum}")
        self.shutdown_requested = True
        
        # Run cleanup tasks
        for task in self.cleanup_tasks:
            try:
                await task()
            except Exception as e:
                self.logger.log_event(f"Cleanup error: {e}")
```

## Specific Refactoring Recommendations

### Priority 1: Critical for Phase 2

1. **Extract BaseAgent Class** (Week 1)
   - Move common SDK client management to base class
   - Standardize agent interface with `process()` method
   - Create agent result containers

2. **Separate Message Processing** (Week 1)
   - Extract MessageProcessor class from analyze_idea()
   - Create message type handlers
   - Standardize message content extraction

3. **Configuration System** (Week 1)
   - Move hard-coded values to config files
   - Create AgentConfig dataclasses
   - Implement environment-based configuration

### Priority 2: Important for Maintainability

4. **Utility Module Extraction** (Week 2)
   - Move DebugLogger to utils/debug_logging.py
   - Extract file operations to utils/file_operations.py
   - Create claude_helpers.py for common SDK patterns

5. **Error Handling Standardization** (Week 2)
   - Create custom exception hierarchy
   - Standardize error messages and logging
   - Add retry logic for transient failures

6. **Testing Infrastructure** (Week 2)
   - Add dependency injection for testability
   - Create mock factories for Claude SDK
   - Implement integration test framework

### Priority 3: Nice to Have

7. **Performance Optimizations** (Week 3)
   - Implement streaming content writing
   - Add memory usage monitoring
   - Optimize WebSearch timeout handling

8. **CLI Enhancement** (Week 3)
   - Replace argparse with Click for better UX
   - Add progress bars and status indicators
   - Implement configuration file CLI options

## Suggested New File Structure

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent_base.py          # BaseAgent abstract class
│   ├── agent_registry.py      # Agent discovery and instantiation
│   ├── client_manager.py      # Claude SDK client lifecycle
│   ├── config.py             # Configuration management
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── message_processor.py  # Message stream handling
│   └── pipeline.py           # Multi-agent orchestration
├── agents/
│   ├── __init__.py
│   ├── analyst.py           # Extracted from current analyze_idea()
│   ├── reviewer.py          # Phase 2 - feedback agent
│   ├── judge.py            # Phase 3 - evaluation agent
│   └── synthesizer.py      # Phase 4 - comparative reports
├── utils/
│   ├── __init__.py
│   ├── debug_logging.py     # DebugLogger class
│   ├── file_operations.py   # save_analysis, create directories
│   ├── text_processing.py   # create_slug, content validation
│   ├── claude_helpers.py    # Common Claude SDK patterns
│   └── validation.py        # Content and structure validation
├── cli/
│   ├── __init__.py
│   └── commands.py          # CLI command implementations
└── analyze.py               # Legacy compatibility wrapper
```

## Module Dependencies and Interfaces

```python
# Dependency flow for new structure
cli.commands 
    -> core.pipeline 
    -> core.agent_registry 
    -> agents.* 
    -> core.agent_base 
    -> core.client_manager 
    -> utils.*

# Key interfaces
class AgentInterface(Protocol):
    async def process(self, input_data: Any) -> AgentResult: ...
    def get_config(self) -> AgentConfig: ...

class PipelineInterface(Protocol):
    async def execute(self, idea: str) -> PipelineResult: ...
    def add_agent(self, name: str, agent: BaseAgent): ...
```

## Next Steps

### Immediate Actions (This Week)

1. **Create BaseAgent Class**
   - Extract common patterns from analyze_idea()
   - Define standard agent interface
   - Test with current analyst functionality

2. **Separate Configuration**
   - Move hard-coded values to YAML config
   - Create AgentConfig dataclasses
   - Test configuration loading

3. **Extract Message Processing**
   - Create MessageProcessor class
   - Refactor analyze_idea() to use processor
   - Validate no functionality is lost

### Phase 2 Preparation (Next Week)

4. **Set Up Agent Registry**
   - Implement agent discovery system
   - Create pipeline orchestration framework
   - Design agent communication protocol

5. **Begin Reviewer Agent**
   - Use new BaseAgent as foundation
   - Implement feedback loop logic
   - Test analyst-reviewer integration

The current code is solid for Phase 1 but needs these refactoring changes to scale effectively. The monolithic structure served its purpose well, but breaking it into focused, reusable components will dramatically simplify adding the remaining agents and create a more maintainable system overall.
