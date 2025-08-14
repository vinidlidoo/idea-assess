# Project-level TODO List

TODO:

- [ ] Fix @src/analyze.py Why does interrupt handling show "Command failed with exit code -2"? See @session-logs/2025-08-13-code-quality-improvements.md
- [ ] Add the capability to feed a list of ideas in a text file into the system, starting with the Analyze.py file.
- [x] ReFactor Analyze.py to reduce its length and offload utilities and other functions to different files. Prepare the repo for adding the next agent to the mix (COMPLETED 2025-08-14)
- [ ] Update the startsession hook to also clean up the logs folder
- [ ] Debug why reviewer agent receives UserMessages in response stream
- [ ] Investigate if reviewer prompt complexity causes JSON generation issues  
- [ ] Test reviewer with non-alcohol business ideas to rule out content policy issues
