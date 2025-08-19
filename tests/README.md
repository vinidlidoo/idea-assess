# Testing Strategy for idea-assess

## Overview

This document outlines our testing philosophy and approach for the idea-assess project, balancing pragmatism with maintainability.

## Testing Philosophy

### Core Principles

1. **Pragmatic Coverage**: We prioritize testing critical business logic and integration points over achieving 100% coverage
2. **Integration Over Isolation**: For SDK-dependent code, integration tests provide more value than complex mocking
3. **Test What Matters**: Focus on behavior and outcomes rather than implementation details
4. **Maintainability**: Tests should be easy to understand and update as the codebase evolves

## Testing Layers

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test isolated business logic and utilities

**Good Candidates for Unit Testing**:

- Pure functions (e.g., `create_slug`, `count_words`)
- Data validation logic (e.g., `FeedbackValidator`)
- Configuration loading and merging
- Utility functions with minimal dependencies

**Poor Candidates for Unit Testing**:

- SDK-dependent code requiring complex mocks (e.g., `RunAnalytics` message processing)
- Agent implementations that primarily orchestrate SDK calls
- Pipeline orchestration that coordinates multiple components

**Example**:

```python
def test_create_slug():
    assert create_slug("AI-Powered Tool") == "ai-powered-tool"
    assert create_slug("Test!!!123") == "test123"
```

### 2. Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions and SDK integrations

**What We Test**:

- Agent-to-agent communication via files
- Pipeline orchestration flows
- SDK message processing and artifact extraction
- File I/O operations in context

**Approach**:

- Use real file system (temp directories)
- Mock only external services (Claude API)
- Test complete workflows end-to-end

### 3. End-to-End Tests (`test_locally.sh`)

**Purpose**: Validate complete system behavior with real Claude API

**Coverage**:

- Simple analysis pipeline
- Reviewer feedback loop
- WebSearch integration
- Error handling and recovery
- Different configuration variants

## Handling SDK Dependencies

### The Challenge

The Claude SDK uses complex type hierarchies that are difficult to mock effectively:

- `TextBlock`, `ToolUseBlock`, etc. are SDK-specific types
- `isinstance()` checks fail with simple `Mock()` objects
- Creating proper mock hierarchies is fragile and maintenance-heavy

### Our Approach

1. **Don't Mock SDK Types**: Accept that SDK-dependent code is tested via integration tests
2. **Extract Business Logic**: Where possible, separate pure business logic from SDK interactions
3. **Use Real SDK Objects**: In tests that must use SDK types, create real instances rather than mocks
4. **Focus on Outcomes**: Test that the system produces correct outputs rather than how it processes SDK messages

### Example: RunAnalytics Testing

**What We Don't Test (Unit)**:

```python
# DON'T: Complex mocking of SDK types
def test_track_text_block():
    mock_block = Mock(spec=TextBlock)  # Won't pass isinstance checks
    # This approach is fragile and provides limited value
```

**What We Do Test (Integration)**:

```python
# DO: Test the complete flow with real data
def test_runanalytics_integration():
    # Run actual analysis with test data
    # Verify output files are created correctly
    # Check aggregated statistics are accurate
```

## Test Organization

### Directory Structure

```
tests/
├── README.md               # This file
├── unit/                   # Isolated unit tests
│   ├── test_utils.py      # Pure function tests
│   ├── test_config.py     # Configuration tests
│   └── test_validators.py # Validation logic tests
├── integration/            # Component integration tests
│   ├── test_pipeline.py   # Pipeline orchestration
│   └── test_agents.py     # Agent interactions
└── fixtures/              # Test data and fixtures
    ├── prompts/           # Test prompt files
    └── analyses/          # Sample analysis outputs
```

### Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<what_is_being_tested>`
- Fixtures: `<name>_fixture`

## Running Tests

### Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Integration Tests Only

```bash
pytest tests/integration/ -v
```

### All Tests

```bash
pytest tests/ -v
```

### With Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### End-to-End Tests

```bash
./test_locally.sh
```

## Guidelines for New Tests

### Before Writing a Test, Ask

1. **Is this testing business logic or SDK orchestration?**
   - Business logic → Unit test
   - SDK orchestration → Integration test

2. **Would mocking make the test fragile?**
   - Yes → Integration test
   - No → Unit test

3. **What am I actually validating?**
   - Implementation details → Reconsider the test
   - Behavior/outcomes → Good test

### Writing Good Tests

1. **Arrange-Act-Assert**: Clear test structure
2. **Single Responsibility**: One test, one behavior
3. **Descriptive Names**: Test name should explain what and why
4. **Minimal Setup**: Use fixtures and helpers to reduce boilerplate
5. **Fast Execution**: Unit tests should run in milliseconds

## Known Limitations

### Current Gaps

1. **RunAnalytics Unit Tests**: Complex SDK dependencies make isolated testing impractical
2. **Agent Unit Tests**: Primarily SDK orchestration, limited unit test value
3. **Pipeline Unit Tests**: Better tested via integration tests

### Future Improvements

1. **Dependency Injection**: Refactor components to accept SDK clients as parameters
2. **Interface Abstraction**: Create interfaces between business logic and SDK
3. **Test Utilities**: Build helpers for creating test SDK objects
4. **Performance Testing**: Add benchmarks for critical paths

## Decision Log

### 2025-08-19: RunAnalytics Testing Strategy

- **Decision**: Skip complex unit tests for RunAnalytics
- **Rationale**: SDK type dependencies make mocking impractical
- **Alternative**: Rely on integration tests and production validation
- **Trade-off**: Less granular testing, but more maintainable test suite

## Maintenance

This document should be updated when:

- New testing patterns are established
- Testing tools or frameworks change
- Significant testing decisions are made
- Test organization changes

---

*Last Updated: 2025-08-19*
*Maintainer: Development Team*
