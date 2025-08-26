# Project-level TODO List

## Infra

- [x] Rewrite all unit tests to reflect latest architecture, leverage AsyncMock and patch from unittest.mock to mock the Claude Code API
- [ ] Install Codecov CLI and write a script to upload the test output .xml file to Codecov account
- [ ] Expand on the pyproject.toml to use a unified setup file for linter config, managing dependencies, etc.
- [x] Consolidate type definitions in a single file: types.py. Right now, results.py and context.py are separate files, making project structure more complex than needed.
- [ ] Auto-archive all logs/runs/* into logs/runs/archive/ except the latest 5 runs sub-folders. Pair it to run it every time run_analytics runs.
- [ ] Update all README.md files, root-level and others deeper in the project tree
- [ ] Distinguish the role of integrations tests vs test harness under test_locally.sh (no sure I understand the difference)
- [ ] Invest in making run_analytics output easier to read and analyze. Evaluate developing a log management services using tools like DuckDB, Streamlit/Evidence.dev, Axiom/Better Stack.
- [ ] Solve against the duplication of artifacts and message content printed in messages.jsonl by run_analytics

## Features

- [ ] Enable human feedback iteration
- [ ] Resume the analyst-reviewer loop with additional iterations when running the CLI on the same idea slug
- [x] De-couple system prompts and file edit template. Have Pipeline orchestrator create file with template instead of creating empty files

## Bugs

- [ ] The allowed-tools Claude Code Options field doesn't seem to work as expected. Investigate and adjust as appropriate
- [x] FIXED: Turn efficiency issue - agents were editing templates section-by-section instead of all at once (solved with single Edit operation instruction)
