# Project-level TODO List

## Infra

- [ ] Install Codecov CLI and write a script to upload the test output .xml file to Codecov account
- [ ] Expand on the pyproject.toml to use a unified setup file for linter config, managing dependencies, etc.
- [ ] Auto-archive all logs/runs/* into logs/runs/archive/ except the latest 5 runs sub-folders. Pair it to run it every time run_analytics runs.
- [ ] Invest in making run_analytics output easier to read and analyze. Evaluate developing a log management services using tools like DuckDB, Streamlit/Evidence.dev, Axiom/Better Stack.
- [ ] Solve against the duplication of artifacts and message content printed in messages.jsonl by run_analytics
- [ ] Consider mutation testing to verify test quality
- [ ] Add caching for WebFetch calls to avoid repeated verifications
- [ ] Reduce duplicative code by consolidating shared modules (e.g., reviewer.py and fact_checker.py share a lot of the same code)
- [ ] Migrate project constants to centralized `src/core/constants.py` file

## Features

- [ ] Resume the analyst-reviewer loop with additional iterations when running the CLI on the same idea slug
- [ ] Enable the insertion of human feedback into the review iteration cycle
- [x] Add capability for the reviewer to do WebSearch tool uses to improve feedback; improve prompt to raise quality bar
- [x] Add capability for the CLI to run multiple pipelines on different ideas at once; where each idea is loaded from a file ✅ COMPLETE
- [ ] Add analysis cost in the metadata at the bottom of the analysis fie
- [ ] Add retry logic for failed ideas in batch processing
- [ ] Generate batch processing statistics/summary report
- [ ] Consider adding a --continue flag to resume interrupted batch processing

## Bugs

- [ ] **WebFetch timeout issue** (IN PROGRESS): WebFetch tool calls can hang indefinitely, blocking pipeline progress. Implementation plan complete, ready to implement timeout with recovery mechanism
- [ ] The allowed-tools Claude Code Options field doesn't seem to work as expected. Investigate and adjust as appropriate
- [ ] Failed to parse search results JSON error in run_analytics - add better error handling for malformed JSON
