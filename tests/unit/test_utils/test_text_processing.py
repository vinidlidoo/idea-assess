"""Tests for text_processing utilities."""

from src.utils.text_processing import create_slug


class TestCreateSlug:
    """Test the create_slug function."""

    def test_create_slug_basic(self):
        """Test normal idea to slug conversion."""
        assert create_slug("AI fitness app") == "ai-fitness-app"
        assert create_slug("B2B SaaS Platform") == "b2b-saas-platform"

    def test_create_slug_special_chars(self):
        """Test removal of special characters and edge cases."""
        assert create_slug("AI-powered fitness app!") == "ai-powered-fitness-app"
        assert create_slug("50% off sale") == "50-off-sale"
        assert create_slug("@#$%^&*()") == ""  # All special chars removed

    def test_create_slug_max_length(self):
        """Test that slug respects max_length parameter."""
        long_idea = "AI powered fitness coaching app for seniors with mobility issues"
        slug = create_slug(long_idea, max_length=20)
        assert len(slug) <= 20
        assert slug == "ai-powered-fitness-c"

    def test_create_slug_unicode(self):
        """Test non-ASCII character handling."""
        assert create_slug("café marketplace") == "café-marketplace"
        assert create_slug("AI 日本 platform") == "ai-日本-platform"

    def test_create_slug_empty_input(self):
        """Test handling of empty/whitespace strings."""
        assert create_slug("") == ""
        assert create_slug("   ") == ""
