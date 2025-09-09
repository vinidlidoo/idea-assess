# Reviewer Instructions Prompt

Please review the business analysis document and provide structured feedback.

Current iteration: {iteration} of maximum {max_iterations}

## Files

- **Analysis to review**: {analysis_path}
- **Previous feedback (if any)**: {previous_feedback_path}
- **Feedback output**: {feedback_file}

## Instructions

1. Review the analysis document at {analysis_path} according to your evaluation criteria
2. If previous feedback is provided, read it to understand what was already addressed
3. Provide structured feedback in {feedback_file}

The feedback file has been created with a JSON template structure.
Follow the file operation best practices when working with these files.

After completing your review, respond with "REVIEW_COMPLETE" to confirm.
