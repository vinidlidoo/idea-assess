# Reviewer Instructions Prompt

Please review the business analysis document and provide structured feedback.

Current iteration: {iteration_count} of maximum {max_iterations}

ANALYSIS FILE TO REVIEW: {analysis_path}

INSTRUCTIONS:

1. Use the Read tool to read the analysis document at the path above
2. Review it according to your system instructions
3. Generate structured JSON feedback as specified
4. Use the Write tool to save your feedback to: {feedback_file}

The feedback JSON should follow the format specified in your system prompt.
After writing the feedback file, respond with "REVIEW_COMPLETE" to confirm.
