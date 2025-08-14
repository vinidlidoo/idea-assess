"""Constants used throughout the idea assessment system."""

# Review iteration limits
MAX_REVIEW_ITERATIONS = 3  # Maximum number of review-revision cycles
MIN_REVIEW_ITERATIONS = 1  # Minimum iterations before accepting

# Content size limits
PREVIEW_CHAR_LIMIT = 200  # Characters to show in content preview
MAX_CONTENT_SIZE = 10_000_000  # Maximum content size in bytes (10MB)
MAX_IDEA_LENGTH = 500  # Maximum length for idea input

# Timing constants
DEFAULT_TIMEOUT_SECONDS = 300  # Default timeout for agent operations (5 minutes)
WEBSEARCH_TIMEOUT_SECONDS = 120  # Timeout for web search operations (2 minutes)
PROGRESS_UPDATE_INTERVAL = 2  # Update progress every N messages

# File operation constants
FILE_LOCK_TIMEOUT = 30  # Seconds to wait for file lock
MAX_FILE_READ_RETRIES = 3  # Maximum retries for file read operations
FILE_RETRY_DELAY = 1.0  # Initial delay for file operation retries (seconds)

# Agent configuration
DEFAULT_MAX_TURNS = 30  # Default maximum turns for agent interactions
REVIEWER_MAX_TURNS = 3  # Maximum turns for reviewer agent
ANALYST_MAX_TURNS = 30  # Maximum turns for analyst agent

# Analysis word limits
MIN_ANALYSIS_WORDS = 900  # Minimum words for analysis
MAX_ANALYSIS_WORDS = 1200  # Maximum words for analysis
SECTION_WORD_LIMITS = {
    "executive_summary": 150,
    "market_opportunity": 250,
    "competition_analysis": 200,
    "business_model": 200,
    "risks_challenges": 200,
    "next_steps": 100,
}