"""Unit tests for pipeline helper methods."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

from src.core.pipeline import AnalysisPipeline
from src.core.config import AnalysisConfig


class TestPipelineHelpers:
    """Test the extracted helper methods in AnalysisPipeline."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Mock(spec=AnalysisConfig)
        config.prompts_dir = Path("config/prompts")
        return config

    @pytest.fixture
    def pipeline(self, config):
        """Create a pipeline instance."""
        return AnalysisPipeline(config)

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_initialize_logging_debug_mode(self, pipeline):
        """Test _initialize_logging in debug mode."""
        with patch.dict("os.environ", {"TEST_HARNESS_RUN": ""}, clear=False):
            with patch("src.core.pipeline.Logger") as mock_logger_class:
                mock_logger = MagicMock()
                mock_logger_class.return_value = mock_logger

                logger, run_id, slug = pipeline._initialize_logging(
                    "Test Business Idea",
                    debug=True,
                    max_iterations=3,
                    use_websearch=True,
                )

                # Verify logger was created
                assert logger == mock_logger
                mock_logger_class.assert_called_once()

                # Verify slug creation
                assert slug == "test-business-idea"

                # Verify run_id format (YYYYMMDD_HHMMSS)
                assert len(run_id) == 15
                assert run_id[8] == "_"

                # Verify logging calls
                mock_logger.info.assert_called_with(
                    "🎯 Pipeline started - Max iterations: 3"
                )

    def test_initialize_logging_production_mode(self, pipeline):
        """Test _initialize_logging in production mode (no debug)."""
        logger, run_id, slug = pipeline._initialize_logging(
            "Test Business Idea", debug=False
        )

        # In production mode with debug=False, logger should be None
        assert logger is None
        assert slug == "test-business-idea"
        assert len(run_id) == 15

    def test_initialize_logging_test_harness_mode(self, pipeline):
        """Test _initialize_logging when TEST_HARNESS_RUN is set."""
        with patch.dict("os.environ", {"TEST_HARNESS_RUN": "1"}):
            logger, run_id, slug = pipeline._initialize_logging(
                "Test Business Idea", debug=True
            )

            # Should return None even in debug mode
            assert logger is None
            assert slug == "test-business-idea"

    def test_setup_directories_creates_structure(self, pipeline, temp_dir):
        """Test _setup_directories creates the expected directory structure."""
        with patch("src.core.pipeline.Path") as mock_path:
            # Mock the Path("analyses") call to use our temp directory
            mock_analyses_path = temp_dir / "analyses"
            mock_path.return_value = mock_analyses_path

            # Mock archive manager
            pipeline.archive_manager.archive_current_analysis = Mock()

            analysis_dir, iterations_dir = pipeline._setup_directories(
                "test-idea", debug=True
            )

            # Verify archive was called with correct run_type
            pipeline.archive_manager.archive_current_analysis.assert_called_once()
            call_args = pipeline.archive_manager.archive_current_analysis.call_args
            assert call_args[1]["run_type"] == "test"

    def test_setup_directories_production_vs_test(self, pipeline):
        """Test _setup_directories uses correct run_type."""
        pipeline.archive_manager.archive_current_analysis = Mock()

        # Test mode
        pipeline._setup_directories("test-idea", debug=True)
        assert (
            pipeline.archive_manager.archive_current_analysis.call_args[1]["run_type"]
            == "test"
        )

        # Production mode
        pipeline._setup_directories("test-idea", debug=False)
        assert (
            pipeline.archive_manager.archive_current_analysis.call_args[1]["run_type"]
            == "production"
        )

    def test_find_feedback_file_exists_in_iterations(self, pipeline, temp_dir):
        """Test _find_feedback_file when file exists in iterations directory."""
        iterations_dir = temp_dir / "iterations"
        iterations_dir.mkdir()
        analysis_dir = temp_dir

        # Create the expected feedback file
        expected_file = iterations_dir / "reviewer_feedback_iteration_1.json"
        expected_file.write_text('{"test": "data"}')

        result = pipeline._find_feedback_file(
            iterations_dir, iteration_count=2, analysis_dir=analysis_dir, logger=None
        )

        assert result == expected_file

    def test_find_feedback_file_fallback_to_main(self, pipeline, temp_dir):
        """Test _find_feedback_file falls back to main feedback file."""
        iterations_dir = temp_dir / "iterations"
        iterations_dir.mkdir()
        analysis_dir = temp_dir

        # Create only the main feedback file
        main_feedback = analysis_dir / "reviewer_feedback.json"
        main_feedback.write_text('{"test": "data"}')

        mock_logger = Mock()
        result = pipeline._find_feedback_file(
            iterations_dir,
            iteration_count=2,
            analysis_dir=analysis_dir,
            logger=mock_logger,
        )

        assert result == main_feedback
        # Verify warning was logged
        mock_logger.warning.assert_called()
        assert "Feedback file missing" in str(mock_logger.warning.call_args)

    def test_find_feedback_file_not_found(self, pipeline, temp_dir):
        """Test _find_feedback_file when no feedback file exists."""
        iterations_dir = temp_dir / "iterations"
        iterations_dir.mkdir()
        analysis_dir = temp_dir

        mock_logger = Mock()
        result = pipeline._find_feedback_file(
            iterations_dir,
            iteration_count=2,
            analysis_dir=analysis_dir,
            logger=mock_logger,
        )

        assert result is None
        # Verify error was logged
        mock_logger.error.assert_called_once()

    def test_save_analysis_files_creates_both_files(self, pipeline, temp_dir):
        """Test _save_analysis_files creates iteration and main files."""
        analysis_dir = temp_dir
        iterations_dir = temp_dir / "iterations"
        iterations_dir.mkdir()

        test_content = "# Test Analysis\n\nThis is test content."
        mock_logger = Mock()

        result = pipeline._save_analysis_files(
            test_content,
            iteration_count=1,
            analysis_dir=analysis_dir,
            iterations_dir=iterations_dir,
            logger=mock_logger,
        )

        # Check iteration file
        iteration_file = iterations_dir / "iteration_1.md"
        assert iteration_file.exists()
        assert iteration_file.read_text() == test_content
        assert result == iteration_file

        # Check main file
        main_file = analysis_dir / "analysis.md"
        assert main_file.exists()
        assert main_file.read_text() == test_content

        # Verify logging
        mock_logger.debug.assert_called_with(f"Analysis saved: {iteration_file}")

    def test_save_analysis_files_overwrites_main(self, pipeline, temp_dir):
        """Test _save_analysis_files overwrites the main analysis file."""
        analysis_dir = temp_dir
        iterations_dir = temp_dir / "iterations"
        iterations_dir.mkdir()

        # Create existing main file
        main_file = analysis_dir / "analysis.md"
        main_file.write_text("Old content")

        new_content = "New content"
        result = pipeline._save_analysis_files(
            new_content,
            iteration_count=2,
            analysis_dir=analysis_dir,
            iterations_dir=iterations_dir,
            logger=None,
        )

        # Main file should be overwritten
        assert main_file.read_text() == new_content

        # Iteration file should be unique
        iteration_file = iterations_dir / "iteration_2.md"
        assert iteration_file.exists()
        assert iteration_file.read_text() == new_content

    def test_helper_methods_integration(self, pipeline, temp_dir):
        """Test that helper methods work together correctly."""
        with patch("src.core.pipeline.Path") as mock_path:
            mock_path.return_value = temp_dir / "analyses"

            # Initialize logging
            logger, run_id, slug = pipeline._initialize_logging(
                "Complex Test Idea", debug=True
            )

            # Setup directories
            pipeline.archive_manager.archive_current_analysis = Mock()
            analysis_dir, iterations_dir = pipeline._setup_directories(slug, debug=True)

            # Save first iteration
            iteration_1_file = pipeline._save_analysis_files(
                "First analysis", 1, analysis_dir, iterations_dir, logger
            )

            # Create feedback file
            feedback_file = iterations_dir / "reviewer_feedback_iteration_1.json"
            feedback_file.write_text('{"recommendation": "reject"}')

            # Find feedback for iteration 2
            found_feedback = pipeline._find_feedback_file(
                iterations_dir, 2, analysis_dir, logger
            )

            assert found_feedback == feedback_file

            # Save second iteration
            iteration_2_file = pipeline._save_analysis_files(
                "Revised analysis", 2, analysis_dir, iterations_dir, logger
            )

            # Verify both iteration files exist
            assert (iterations_dir / "iteration_1.md").exists()
            assert (iterations_dir / "iteration_2.md").exists()

            # Verify main file has latest content
            assert (analysis_dir / "analysis.md").read_text() == "Revised analysis"
