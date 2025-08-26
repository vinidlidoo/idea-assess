# Old Tests Backup

This folder contains the original unit tests that were backed up during the Phase 1 test overhaul.

## Backed up on: 2025-08-25

### Files

- `test_interrupt.py` - Original interrupt handling tests
- `test_logger.py` - Logger utility tests  
- `test_pipeline_helpers.py` - Pipeline helper tests
- `test_prompt_extraction.py` - Prompt extraction tests
- `test_prompt_includes.py` - Prompt include system tests
- `test_run_analytics.py` - Run analytics tests
- `test_security.py` - Security validation tests

## Current Status

These tests have been replaced by the new Phase 1 test structure:

- New base test classes in `../base_test.py`
- New agent tests in `../test_agents/`
- New SDK error handling tests in `../test_sdk_errors.py`
- New interrupt handling tests in `../test_interrupt_handling.py`

These old tests can be referenced for:

1. Understanding original test coverage
2. Migrating any missing test cases
3. Historical reference
