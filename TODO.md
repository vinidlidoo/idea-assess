# Project-level TODO List

TODO:

- [ ] Add the capability to feed a list of ideas in a text file into the system, starting with the Analyze.py file.
- [x] ReFactor Analyze.py to reduce its length and offload utilities and other functions to different files. Prepare the repo for adding the next agent to the mix (COMPLETED 2025-08-14)
- [x] Update the startsession hook to also clean up the logs folder
- [x] Debug why reviewer agent receives UserMessages in response stream (RESOLVED: SDK designed for human interaction)
- [x] Investigate if reviewer prompt complexity causes JSON generation issues (RESOLVED: File-based approach works)  
- [x] Test reviewer with non-alcohol business ideas to rule out content policy issues (TESTED: Works with education platform)
- [x] Clean up old reviewer implementations (COMPLETED 2025-08-14)
- [x] Clean up old pipeline.py (COMPLETED 2025-08-14)
- [x] Update imports in __init__.py files after cleanup (COMPLETED 2025-08-14)
- [ ] Consider future migration to Anthropic API for cleaner agent communication
- [ ] Fix critical FeedbackProcessor import bug (see assessment doc for details)
