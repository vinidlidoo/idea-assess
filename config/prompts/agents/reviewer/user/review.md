# Reviewer Instructions Prompt

Please review the business analysis document and provide structured feedback.

Current iteration: {iteration} of maximum {max_iterations}

ANALYSIS FILE TO REVIEW: {analysis_path}

INSTRUCTIONS (FOLLOW IN EXACT ORDER):

1. FIRST: Use the Read tool to read the analysis document at: {analysis_path}
   (This is the CURRENT iteration file you need to review)

2. SECOND: Review the analysis according to your system instructions

3. THIRD: Use the Read tool to read the feedback file at: {feedback_file}
   (This file already exists with empty JSON: {{}})

4. FOURTH: Use the Edit tool on {feedback_file} to replace "{{}}" with your complete feedback JSON

CRITICAL REMINDERS:

- You MUST read each file before editing it
- Read the EXACT paths provided above - don't guess file names
- NEVER use the Write tool - all files are pre-created
- If Edit fails, it means you didn't Read the file first

The feedback JSON should follow the format specified in your system prompt.
After editing the feedback file, respond with "REVIEW_COMPLETE" to confirm.
