"""Tests for text_processing utilities."""

import pytest

from src.utils.text_processing import create_slug


class TestCreateSlug:
    """Test the create_slug function."""

    def test_create_slug_basic(self):
        """Test normal idea to slug conversion."""
        assert create_slug("AI fitness app") == "ai-fitness-app"
        assert create_slug("B2B SaaS Platform") == "b2b-saas-platform"
        assert create_slug("Online Learning") == "online-learning"

    def test_create_slug_special_chars(self):
        """Test removal of special characters."""
        assert create_slug("AI-powered fitness app!") == "ai-powered-fitness-app"
        assert create_slug("B2B SaaS Platform!!!") == "b2b-saas-platform"
        assert create_slug("Online @ Learning #1") == "online-learning-1"
        assert create_slug("Test & Demo") == "test-demo"
        assert create_slug("50% off sale") == "50-off-sale"

    def test_create_slug_max_length(self):
        """Test that slug respects max_length parameter."""
        long_idea = "AI powered fitness coaching app for seniors with mobility issues"
        # Default max_length is 50
        slug = create_slug(long_idea)
        assert len(slug) <= 50
        # The function cuts at exactly 50 chars, not at word boundaries
        assert slug == "ai-powered-fitness-coaching-app-for-seniors-with-m"

        # Custom max_length
        slug_short = create_slug(long_idea, max_length=20)
        assert len(slug_short) <= 20
        assert slug_short == "ai-powered-fitness-c"

    def test_create_slug_empty_input(self):
        """Test handling of empty string."""
        assert create_slug("") == ""
        assert create_slug("   ") == ""
        assert create_slug("\n\t") == ""

    def test_create_slug_only_special_chars(self):
        """Test when all characters are removed."""
        assert create_slug("@#$%^&*()") == ""
        assert create_slug("!!!???...") == ""
        # Note: underscores are kept by \w pattern
        assert create_slug("___") == "___"

    def test_create_slug_unicode(self):
        """Test non-ASCII character handling."""
        # Note: Python 3's \w includes Unicode word characters
        assert create_slug("Über app") == "über-app"
        assert create_slug("café marketplace") == "café-marketplace"
        assert create_slug("AI 日本 platform") == "ai-日本-platform"
        assert create_slug("naïve solution") == "naïve-solution"

    def test_create_slug_multiple_spaces(self):
        """Test space normalization."""
        assert create_slug("AI    fitness    app") == "ai-fitness-app"
        assert create_slug("  leading spaces") == "leading-spaces"
        assert create_slug("trailing spaces  ") == "trailing-spaces"
        assert (
            create_slug("  multiple   spaces   everywhere  ")
            == "multiple-spaces-everywhere"
        )

    @pytest.mark.parametrize(
        "idea,expected",
        [
            ("Test-Case-With-Dashes", "test-case-with-dashes"),
            ("123 Numbers First", "123-numbers-first"),
            ("UPPERCASE IDEA", "uppercase-idea"),
            ("CamelCaseIdea", "camelcaseidea"),
        ],
    )
    def test_create_slug_case_handling(self, idea, expected):
        """Test case conversion and number handling."""
        assert create_slug(idea) == expected

    def test_create_slug_edge_cases(self):
        """Test various edge cases."""
        # Single character
        assert create_slug("A") == "a"

        # Numbers only
        assert create_slug("12345") == "12345"

        # Mixed case preservation (converted to lowercase)
        assert create_slug("CamelCaseIdea") == "camelcaseidea"

        # Consecutive hyphens reduced
        assert create_slug("test--multiple---hyphens") == "test-multiple-hyphens"

        # Strip trailing hyphens
        assert (
            create_slug("ends-with-special-@@@", max_length=20) == "ends-with-special"
        )
