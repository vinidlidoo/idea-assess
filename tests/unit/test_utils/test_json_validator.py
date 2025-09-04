"""Tests for JSON validator utilities."""

import tempfile
from pathlib import Path

import pytest

from src.utils.json_validator import FeedbackValidator


class TestFeedbackValidator:
    """Test the FeedbackValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return FeedbackValidator()

    @pytest.fixture
    def valid_feedback(self):
        """Create valid feedback structure."""
        return {
            "overall_assessment": "The analysis is comprehensive and well-structured.",
            "iteration_recommendation": "approve",
            "iteration_reason": "Analysis meets quality standards",
            "critical_issues": [],
            "improvements": [],
            "minor_suggestions": [
                {
                    "section": "Metrics",
                    "issue": "Limited quantitative data",
                    "suggestion": "Consider adding more metrics",
                }
            ],
        }

    def test_validate_correct_feedback(self, validator, valid_feedback):
        """Test that valid feedback passes validation."""
        is_valid, error = validator.validate(valid_feedback)
        assert is_valid is True
        assert error is None

    def test_validate_missing_recommendation(self, validator):
        """Test that missing required field is caught."""
        feedback = {
            "overall_assessment": "Test assessment",
            "iteration_reason": "Some reason",
            "critical_issues": [],
            "improvements": [],
        }
        is_valid, error = validator.validate(feedback)
        assert is_valid is False
        assert (
            "iteration_recommendation" in error.lower()
            or "overall_assessment" in error.lower()
        )

    def test_validate_invalid_recommendation_value(self, validator):
        """Test that wrong enum value is rejected."""
        feedback = {
            "overall_assessment": "Test assessment",
            "iteration_recommendation": "maybe",  # Invalid - must be approve/reject
            "iteration_reason": "Some reason",
            "critical_issues": [],
            "improvements": [],
        }
        is_valid, error = validator.validate(feedback)
        assert is_valid is False
        assert "not one of" in error.lower() or "enum" in error.lower()

    def test_validate_file_not_found(self, validator):
        """Test handling of missing file."""
        non_existent = Path("/tmp/does_not_exist_feedback.json")
        is_valid, error = validator.validate_file(non_existent)
        assert is_valid is False
        assert "not found" in error.lower()

    def test_validate_invalid_json(self, validator):
        """Test handling of malformed JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{broken json}")
            temp_path = Path(f.name)

        try:
            is_valid, error = validator.validate_file(temp_path)
            assert is_valid is False
            assert "invalid json" in error.lower() or "decode" in error.lower()
        finally:
            temp_path.unlink(missing_ok=True)

    def test_fix_common_issues_missing_fields(self, validator):
        """Test auto-adding required fields."""
        feedback = {}  # Empty feedback
        fixed = validator.fix_common_issues(feedback)

        # Should have all required arrays
        assert "critical_issues" in fixed
        assert "improvements" in fixed
        assert "minor_suggestions" in fixed
        assert isinstance(fixed["critical_issues"], list)
        assert isinstance(fixed["improvements"], list)
        assert isinstance(fixed["minor_suggestions"], list)

    def test_fix_iteration_to_recommendation_mapping(self, validator):
        """Test legacy field conversion."""
        feedback = {
            "overall_assessment": "Test assessment",
            "iteration_recommendation": "accept",  # Legacy value
            "iteration_reason": "Test reason",
            "critical_issues": [],
        }
        fixed = validator.fix_common_issues(feedback)

        assert fixed["iteration_recommendation"] == "approve"  # Mapped from accept
        assert "iteration_reason" in fixed

    def test_fix_critical_issues_string_to_dict(self, validator):
        """Test converting string issues to proper structure."""
        feedback = {
            "overall_assessment": "Test assessment",
            "iteration_recommendation": "reject",
            "iteration_reason": "Test reason",
            "critical_issues": [
                "Missing market analysis",  # String format
                {  # Already proper format
                    "issue": "No competitive analysis",
                    "suggestion": "Add competitor section",
                    "priority": "critical",
                },
            ],
        }
        fixed = validator.fix_common_issues(feedback)

        # First issue should be converted to dict
        assert isinstance(fixed["critical_issues"][0], dict)
        assert fixed["critical_issues"][0]["issue"] == "Missing market analysis"
        assert fixed["critical_issues"][0]["priority"] == "critical"
        assert "suggestion" in fixed["critical_issues"][0]

        # Second issue should remain unchanged
        assert fixed["critical_issues"][1]["issue"] == "No competitive analysis"

    def test_fix_improvements_structure(self, validator):
        """Test handling section/area fields in improvements."""
        feedback = {
            "overall_assessment": "Test assessment",
            "iteration_recommendation": "reject",
            "iteration_reason": "Test reason",
            "improvements": [
                {
                    "area": "Market Analysis",
                    "suggestion": "Add more data",
                },  # area field
                {"suggestion": "Improve formatting"},  # Missing section
                "Add more examples",  # String format
            ],
        }
        fixed = validator.fix_common_issues(feedback)

        # First improvement: area → section
        assert fixed["improvements"][0]["section"] == "Market Analysis"
        assert (
            "area" not in fixed["improvements"][0]
            or fixed["improvements"][0]["area"] == "Market Analysis"
        )

        # Second improvement: add default section
        assert fixed["improvements"][1]["section"] == "General"

        # Third improvement: convert string to dict
        assert isinstance(fixed["improvements"][2], dict)
        assert fixed["improvements"][2]["suggestion"] == "Add more examples"

    def test_validator_instance_reuse(self, validator, valid_feedback):
        """Test multiple validations with same instance."""
        # First validation
        is_valid1, _ = validator.validate(valid_feedback)
        assert is_valid1 is True

        # Modify and validate again
        invalid_feedback = valid_feedback.copy()
        invalid_feedback["iteration_recommendation"] = "invalid"
        is_valid2, _ = validator.validate(invalid_feedback)
        assert is_valid2 is False

        # Original should still validate
        is_valid3, _ = validator.validate(valid_feedback)
        assert is_valid3 is True

    def test_complex_feedback_structure(self, validator):
        """Test validation of complex, fully-populated feedback."""
        complex_feedback = {
            "overall_assessment": "The analysis has potential but needs significant improvements.",
            "iteration_recommendation": "reject",
            "iteration_reason": "Multiple critical issues need addressing",
            "critical_issues": [
                {
                    "issue": "Market size not validated",
                    "suggestion": "Add TAM/SAM/SOM analysis with sources",
                    "priority": "critical",
                },
                {
                    "issue": "No competitive moat identified",
                    "suggestion": "Explain unique value proposition",
                    "priority": "high",
                },
            ],
            "improvements": [
                {
                    "section": "Business Model",
                    "issue": "Revenue streams unclear",
                    "suggestion": "Detail pricing strategy and revenue projections",
                    "priority": "high",
                }
            ],
            "minor_suggestions": [
                {
                    "section": "Executive Summary",
                    "issue": "Typo present",
                    "suggestion": "Fix typo in executive summary",
                },
                {
                    "section": "Risks",
                    "issue": "Missing regulatory discussion",
                    "suggestion": "Add regulatory risk discussion",
                },
            ],
            "strengths": [
                "Strong technical feasibility analysis",
                "Good understanding of target market",
            ],
        }

        is_valid, error = validator.validate(complex_feedback)
        assert is_valid is True
        assert error is None

    def test_recommendation_value_normalization(self, validator):
        """Test that various recommendation values are normalized correctly."""
        test_cases = [
            ("accept", "approve"),
            ("Accept", "approve"),
            ("ACCEPT", "approve"),
            ("approve", "approve"),
            ("pass", "approve"),
            ("reject", "reject"),
            ("Reject", "reject"),
            ("fail", "reject"),
            ("revise", "reject"),
        ]

        for input_val, expected_val in test_cases:
            feedback = {
                "overall_assessment": "Test assessment",
                "iteration_recommendation": input_val,
                "iteration_reason": "Test reason",
                "critical_issues": [],
            }
            fixed = validator.fix_common_issues(feedback)
            assert fixed["iteration_recommendation"] == expected_val, (
                f"Failed for input: {input_val}"
            )
