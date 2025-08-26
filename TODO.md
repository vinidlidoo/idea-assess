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
- [ ] Consider adding property-based testing with Hypothesis for validators
- [ ] Add integration tests for full pipeline with real files
- [ ] Consider mutation testing to verify test quality
- [ ] Add performance benchmarks for large analyses

## Features

- [x] Invite the analyst to use the WebFetch tool and to further dive results from the WebSearch tool
- [x] Invite the analyst to the TodoWrite tool to produce better results
- [x] Invite the analyst to Thinking mode to produce better results (noted: future Claude feature)
- [ ] Tweak prompt to make references/citations more accurate
- [ ] Resume the analyst-reviewer loop with additional iterations when running the CLI on the same idea slug
- [ ] Enable human feedback iteration
- [ ] Add capability for the CLI to run multiple pipelines on different ideas at once
- [ ] Add analysis cost in the metadata at the bottom of the analysis file
- [x] De-couple system prompts and file edit template. Have Pipeline orchestrator create file with template instead of creating empty files

## Bugs

- [ ] The allowed-tools Claude Code Options field doesn't seem to work as expected. Investigate and adjust as appropriate
