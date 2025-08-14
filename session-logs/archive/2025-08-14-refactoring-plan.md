# Refactoring Plan: Modularizing analyze.py for Multi-Agent Architecture

## Executive Summary

Based on the comprehensive code review, this plan outlines the concrete steps to refactor `analyze.py` from a monolithic script into a modular, extensible multi-agent system ready for Phase 2.

## Immediate Priority Tasks (Today)

### Task 1: Create Core Module Structure

**Files to create:**

- `src/core/__init__.py`
- `src/core/config.py` - Configuration management
- `src/utils/__init__.py`
- `src/utils/text_processing.py` - String utilities
- `src/utils/file_operations.py` - File I/O utilities
- `src/utils/debug_logging.py` - DebugLogger class

### Task 2: Extract Utility Functions

**Move from analyze.py to utils modules:**

- `create_slug()` → `utils/text_processing.py`
- `DebugLogger` class → `utils/debug_logging.py`
- `save_analysis()` → `utils/file_operations.py`
- `show_preview()` → `utils/text_processing.py`

### Task 3: Create Configuration System

**Extract to `core/config.py`:**

```python
@dataclass
class AnalysisConfig:
    """Configuration for analysis operations"""
    project_root: Path
    prompts_dir: Path
    analyses_dir: Path
    logs_dir: Path
    max_turns: int = 15
    max_websearches: int = 5
    slug_max_length: int = 50
    preview_lines: int = 20
    progress_interval: int = 2
    default_prompt_version: str = "v3"
```

### Task 4: Create Base Agent Interface

**New file `src/core/agent_base.py`:**

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentResult:
    """Standard result container for all agents"""
    content: str
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    @abstractmethod
    async def process(self, input_data: str, **kwargs) -> AgentResult:
        """Process input and return standardized result"""
        pass
    
    @abstractmethod
    def get_prompt_file(self) -> str:
        """Return the prompt file name for this agent"""
        pass
    
    @abstractmethod
    def get_allowed_tools(self) -> List[str]:
        """Return list of allowed tools for this agent"""
        pass
```

### Task 5: Create Message Processor

**New file `src/core/message_processor.py`:**

- Extract message processing logic from `analyze_idea()`
- Separate concerns: parsing, content extraction, progress tracking
- Make reusable for all agents

## File Structure After Refactoring

```text
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent_base.py       # BaseAgent abstract class
│   ├── config.py           # Configuration management
│   └── message_processor.py # Reusable message handling
├── agents/
│   ├── __init__.py
│   └── analyst.py          # AnalystAgent class
├── utils/
│   ├── __init__.py
│   ├── debug_logging.py    # DebugLogger
│   ├── file_operations.py  # File I/O utilities
│   └── text_processing.py  # Text utilities
├── cli.py                  # New CLI entry point
└── analyze.py              # Deprecated, replaced by cli.py

config/
├── prompts/
│   ├── analyst_v1.md
│   ├── analyst_v2.md
│   ├── analyst_v3.md
│   ├── reviewer.md         # Phase 2
│   ├── judge.md           # Phase 3
│   └── synthesizer.md     # Phase 4
└── settings.yaml          # External configuration
```

## Implementation Steps (With Incremental Testing)

### Step 1: Create Utils Module (30 min)

1. Create `src/utils/` directory structure
2. Move utility functions with minimal changes
3. Update imports in analyze.py
4. **TEST**: Run `python src/analyze.py "Test idea" --no-websearch` to verify imports work

### Step 2: Create Core Module (45 min)

1. Create `src/core/` directory structure
2. Implement `config.py` with configuration dataclass
3. **TEST**: Import and instantiate config to verify structure
4. Create `agent_base.py` with abstract base class
5. Create `message_processor.py` skeleton
6. **TEST**: Run analysis again to ensure no regression

### Step 3: Create AnalystAgent (1 hour)

1. Create `src/agents/analyst.py`
2. Implement AnalystAgent inheriting from BaseAgent
3. **TEST**: Run standalone test of AnalystAgent with simple input
4. Move agent-specific logic from analyze.py
5. Keep analyze.py working as a thin wrapper
6. **TEST**: Compare output with original for "AI fitness app" (no websearch)

### Step 4: Update CLI (30 min)

1. Create new `src/cli.py` with updated structure
2. **TEST**: Run via new CLI with test idea
3. Keep backward compatibility with existing analyze.py
4. Add deprecation notice to analyze.py
5. **TEST**: Verify both entry points work correctly

### Test Command for Quick Validation

```bash
# Quick test without websearch (saves 30-120s per test)
python src/analyze.py "AI-powered fitness app" --no-websearch -p v3
```

## Benefits of This Refactoring

1. **Modularity**: Clean separation of concerns
2. **Extensibility**: Easy to add new agents
3. **Maintainability**: Smaller, focused modules
4. **Testability**: Each component can be tested independently
5. **Reusability**: Common utilities shared across agents

## Risk Mitigation

- Keep original `analyze.py` working during transition
- Test each step incrementally
- Maintain backward compatibility
- Document all breaking changes

## Success Criteria

- [ ] All utility functions extracted and working
- [ ] BaseAgent interface defined and documented
- [ ] AnalystAgent implemented using new structure
- [ ] Existing analyses can still be generated
- [ ] Code passes basic testing with 5 test ideas
- [ ] New structure ready for Reviewer agent addition

## Next Session Tasks

After completing this refactoring:

1. Implement Reviewer agent using new BaseAgent interface
2. Create agent pipeline orchestration
3. Add inter-agent communication protocol
4. Implement feedback loop between Analyst and Reviewer

---

*This plan provides a clear path from monolithic to modular architecture while maintaining system stability.*
