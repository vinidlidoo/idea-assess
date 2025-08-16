"""JSON schema validation for reviewer feedback."""

import json
from pathlib import Path
from typing import Any
from jsonschema import validate, ValidationError


# Define the schema for reviewer feedback
REVIEWER_FEEDBACK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "iteration_recommendation",
        "iteration_reason",
        "critical_issues",
        "improvements",
        "minor_suggestions",
    ],
    "properties": {
        "iteration_recommendation": {
            "type": "string",
            "enum": ["accept", "reject"],
            "description": "Whether to accept or reject the current analysis",
        },
        "iteration_reason": {
            "type": "string",
            "minLength": 10,
            "description": "Explanation for the recommendation",
        },
        "critical_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["issue", "suggestion", "priority"],
                "properties": {
                    "issue": {
                        "type": "string",
                        "minLength": 5,
                        "description": "Description of the critical issue",
                    },
                    "suggestion": {
                        "type": "string",
                        "minLength": 5,
                        "description": "Specific suggestion to address the issue",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high"],
                        "description": "Priority level of the issue",
                    },
                },
            },
            "description": "List of critical issues that must be addressed",
        },
        "improvements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["area", "suggestion"],
                "properties": {
                    "area": {
                        "type": "string",
                        "minLength": 3,
                        "description": "Area needing improvement",
                    },
                    "suggestion": {
                        "type": "string",
                        "minLength": 5,
                        "description": "Specific improvement suggestion",
                    },
                },
            },
            "description": "List of improvements to enhance quality",
        },
        "minor_suggestions": {
            "type": "array",
            "items": {"type": "string", "minLength": 5},
            "description": "List of minor suggestions for polish",
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string", "minLength": 5},
            "description": "Positive aspects of the analysis (optional)",
        },
    },
}


class FeedbackValidator:
    """Validates reviewer feedback against JSON schema."""

    def __init__(self):
        """Initialize the validator with the feedback schema."""
        self.schema: dict[str, Any] = REVIEWER_FEEDBACK_SCHEMA

    def validate(self, feedback: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate feedback against schema.

        Args:
            feedback: The feedback dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if feedback is valid
            - error_message: Error description if invalid, None if valid
        """
        try:
            validate(instance=feedback, schema=self.schema)
            return True, None
        except ValidationError as e:
            # Format error message for clarity
            error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            error_msg = f"Validation error at '{error_path}': {e.message}"
            return False, error_msg
        except Exception as e:
            return False, f"Unexpected validation error: {str(e)}"

    def validate_file(self, feedback_file: Path) -> tuple[bool, str | None]:
        """
        Validate feedback from a JSON file.

        Args:
            feedback_file: Path to the feedback JSON file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(feedback_file, "r") as f:
                feedback = json.load(f)
            return self.validate(feedback)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
        except FileNotFoundError:
            return False, f"Feedback file not found: {feedback_file}"
        except Exception as e:
            return False, f"Error reading feedback file: {str(e)}"

    def fix_common_issues(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """
        Attempt to fix common schema issues in feedback.

        Args:
            feedback: The feedback dictionary to fix

        Returns:
            Fixed feedback dictionary
        """
        # Ensure all required fields exist
        if "critical_issues" not in feedback:
            feedback["critical_issues"] = []
        if "improvements" not in feedback:
            feedback["improvements"] = []
        if "minor_suggestions" not in feedback:
            feedback["minor_suggestions"] = []

        # Fix iteration_recommendation values
        if "iteration_recommendation" in feedback:
            rec_raw = feedback.get("iteration_recommendation", "")
            if isinstance(rec_raw, str):
                rec = rec_raw.lower()
                if rec in ["accept", "approve", "pass"]:
                    feedback["iteration_recommendation"] = "accept"
                elif rec in ["reject", "fail", "revise"]:
                    feedback["iteration_recommendation"] = "reject"

        # Ensure iteration_reason exists
        if "iteration_reason" not in feedback or not feedback["iteration_reason"]:
            if feedback.get("iteration_recommendation") == "accept":
                feedback["iteration_reason"] = "Analysis meets quality standards"
            else:
                feedback["iteration_reason"] = "Analysis needs improvements"

        # Fix critical_issues structure
        if isinstance(feedback.get("critical_issues"), list):
            fixed_issues = []
            for issue in feedback["critical_issues"]:
                if isinstance(issue, str):
                    # Convert string to proper structure
                    fixed_issues.append(
                        {
                            "issue": issue,
                            "suggestion": "Address this issue",
                            "priority": "critical",
                        }
                    )
                elif isinstance(issue, dict):
                    # Ensure required fields
                    if "priority" not in issue:
                        issue["priority"] = "critical"
                    if "suggestion" not in issue:
                        issue["suggestion"] = issue.get("issue", "Address this issue")
                    fixed_issues.append(issue)
            feedback["critical_issues"] = fixed_issues

        # Fix improvements structure
        if isinstance(feedback.get("improvements"), list):
            fixed_improvements = []
            for improvement in feedback["improvements"]:
                if isinstance(improvement, str):
                    # Convert string to proper structure
                    fixed_improvements.append(
                        {"area": "General", "suggestion": improvement}
                    )
                elif isinstance(improvement, dict):
                    # Ensure required fields
                    if "area" not in improvement:
                        improvement["area"] = "General"
                    fixed_improvements.append(improvement)
            feedback["improvements"] = fixed_improvements

        return feedback
