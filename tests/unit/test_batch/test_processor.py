"""Unit tests for the batch processor module."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.batch.processor import BatchProcessor, show_progress
from src.core.config import SystemConfig, AnalystConfig, ReviewerConfig, FactCheckerConfig
from src.core.types import PipelineMode, PipelineResult


@pytest.fixture
def mock_configs():
    """Create mock configurations for testing."""
    system_config = Mock(spec=SystemConfig)
    analyst_config = Mock(spec=AnalystConfig)
    reviewer_config = Mock(spec=ReviewerConfig)
    fact_checker_config = Mock(spec=FactCheckerConfig)
    
    return system_config, analyst_config, reviewer_config, fact_checker_config


@pytest.fixture
def batch_processor(mock_configs):
    """Create a BatchProcessor instance for testing."""
    system_config, analyst_config, reviewer_config, fact_checker_config = mock_configs
    return BatchProcessor(
        system_config=system_config,
        analyst_config=analyst_config,
        reviewer_config=reviewer_config,
        fact_checker_config=fact_checker_config,
        mode=PipelineMode.ANALYZE,
        max_concurrent=2
    )


class TestBatchProcessor:
    """Test the BatchProcessor class."""
    
    def test_initialization(self, mock_configs):
        """Test BatchProcessor initialization."""
        system_config, analyst_config, reviewer_config, fact_checker_config = mock_configs
        
        processor = BatchProcessor(
            system_config=system_config,
            analyst_config=analyst_config,
            reviewer_config=reviewer_config,
            fact_checker_config=fact_checker_config,
            mode=PipelineMode.ANALYZE_AND_REVIEW,
            max_concurrent=3
        )
        
        assert processor.system_config == system_config
        assert processor.analyst_config == analyst_config
        assert processor.reviewer_config == reviewer_config
        assert processor.fact_checker_config == fact_checker_config
        assert processor.mode == PipelineMode.ANALYZE_AND_REVIEW
        assert processor.max_concurrent == 3
        assert processor.semaphore._value == 3
        assert processor.results == {}
        assert processor.start_times == {}
        assert processor.end_times == {}
        assert processor.progress == {}
    
    @pytest.mark.asyncio
    async def test_process_with_semaphore_success(self, batch_processor):
        """Test successful processing of a single idea."""
        # Mock the AnalysisPipeline
        with patch('src.batch.processor.AnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            
            # Create expected result
            expected_result: PipelineResult = {
                "success": True,
                "analysis_path": "/path/to/analysis.md",
                "feedback_path": None,
                "idea_slug": "test-idea",
                "iterations": 1,
                "message": None
            }
            mock_pipeline.process.return_value = expected_result
            
            # Process idea
            slug, result = await batch_processor.process_with_semaphore(
                "Test Idea", 
                "Description of the test idea"
            )
            
            # Verify results
            assert slug == "test-idea"
            assert result == expected_result
            assert batch_processor.progress[slug] == "completed"
            assert slug in batch_processor.start_times
            assert slug in batch_processor.end_times
    
    @pytest.mark.asyncio
    async def test_process_with_semaphore_failure(self, batch_processor):
        """Test handling of processing failure."""
        with patch('src.batch.processor.AnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            
            # Simulate an exception
            mock_pipeline.process.side_effect = Exception("Test error")
            
            # Process idea
            slug, result = await batch_processor.process_with_semaphore(
                "Failed Idea",
                "This will fail"
            )
            
            # Verify error result
            assert slug == "failed-idea"
            assert result["success"] is False
            assert result["message"] == "Test error"
            assert result["iterations"] == 0
            assert batch_processor.progress[slug] == "failed"
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, batch_processor):
        """Test that semaphore properly limits concurrent processing."""
        batch_processor.max_concurrent = 2
        batch_processor.semaphore = asyncio.Semaphore(2)
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0
        
        async def mock_process():
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate processing time
            concurrent_count -= 1
            return {
                "success": True,
                "analysis_path": "/path.md",
                "feedback_path": None,
                "idea_slug": "test",
                "iterations": 1,
                "message": None
            }
        
        with patch('src.batch.processor.AnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.process.side_effect = mock_process
            
            # Create multiple tasks
            tasks = [
                batch_processor.process_with_semaphore(f"Idea {i}", f"Desc {i}")
                for i in range(5)
            ]
            
            # Process all tasks
            await asyncio.gather(*tasks)
            
            # Verify concurrency was limited
            assert max_concurrent_seen <= 2
    
    @pytest.mark.asyncio
    async def test_process_batch_empty_list(self, batch_processor):
        """Test processing an empty list of ideas."""
        results = await batch_processor.process_batch([])
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_process_batch_with_file_management(self, batch_processor, tmp_path):
        """Test batch processing with file management."""
        pending_file = tmp_path / "pending.md"
        completed_file = tmp_path / "completed.md"
        failed_file = tmp_path / "failed.md"
        
        ideas = [
            ("Success Idea", "Will succeed"),
            ("Failure Idea", "Will fail")
        ]
        
        with patch('src.batch.processor.AnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            
            # First idea succeeds, second fails
            mock_pipeline.process.side_effect = [
                {
                    "success": True,
                    "analysis_path": "/success.md",
                    "feedback_path": None,
                    "idea_slug": "success-idea",
                    "iterations": 1,
                    "message": None
                },
                Exception("Test failure")
            ]
            
            with patch('src.batch.processor.move_idea_to_completed') as mock_move_completed:
                with patch('src.batch.processor.move_idea_to_failed') as mock_move_failed:
                    results = await batch_processor.process_batch(
                        ideas,
                        pending_file=pending_file,
                        completed_file=completed_file,
                        failed_file=failed_file
                    )
                    
                    # Verify file management calls
                    mock_move_completed.assert_called_once_with(
                        "Success Idea", "Will succeed", 
                        pending_file, completed_file
                    )
                    mock_move_failed.assert_called_once()
                    
                    # Verify results
                    assert len(results) == 2
                    assert results["success-idea"]["success"] is True
                    assert results["failure-idea"]["success"] is False
    
    def test_display_summary(self, batch_processor, capsys):
        """Test the display_summary method."""
        # Set up test data
        batch_processor.results = {
            "idea-1": {
                "success": True,
                "analysis_path": "/path1.md",
                "feedback_path": None,
                "idea_slug": "idea-1",
                "iterations": 2,
                "message": None
            },
            "idea-2": {
                "success": False,
                "analysis_path": None,
                "feedback_path": None,
                "idea_slug": "idea-2",
                "iterations": 0,
                "message": "Test error message that is very long and should be truncated"
            }
        }
        
        batch_processor.start_times = {
            "idea-1": datetime.now(),
            "idea-2": datetime.now()
        }
        batch_processor.end_times = {
            "idea-1": datetime.now(),
            "idea-2": datetime.now()
        }
        
        # Call display_summary
        batch_processor.display_summary()
        
        # Check output
        captured = capsys.readouterr()
        assert "BATCH PROCESSING SUMMARY" in captured.out
        assert "idea-1" in captured.out
        assert "✓ Success" in captured.out
        assert "idea-2" in captured.out
        assert "✗ Failed" in captured.out
        assert "Total: 2 ideas" in captured.out
        assert "Successful: 1" in captured.out
        assert "Failed: 1" in captured.out


class TestShowProgress:
    """Test the show_progress function."""
    
    @pytest.mark.asyncio
    async def test_show_progress_stops_when_done(self, batch_processor, capsys):
        """Test that show_progress stops when no tasks are running."""
        # Set up progress data
        batch_processor.progress = {
            "idea-1": "completed",
            "idea-2": "failed",
            "idea-3": "completed"
        }
        
        # Run show_progress with very short interval
        await show_progress(batch_processor, update_interval=0.01)
        
        # Check output
        captured = capsys.readouterr()
        assert "[Batch Progress]" in captured.out
        assert "Running: 0" in captured.out
        assert "Completed: 2" in captured.out
        assert "Failed: 1" in captured.out
        assert "Total: 3" in captured.out
    
    @pytest.mark.asyncio
    async def test_show_progress_updates_periodically(self, batch_processor, capsys):
        """Test that show_progress updates periodically while running."""
        # Set up initial progress
        batch_processor.progress = {
            "idea-1": "running",
            "idea-2": "running"
        }
        
        async def update_progress():
            """Simulate progress updates."""
            await asyncio.sleep(0.02)
            batch_processor.progress["idea-1"] = "completed"
            await asyncio.sleep(0.02)
            batch_processor.progress["idea-2"] = "completed"
        
        # Run show_progress and updater concurrently
        progress_task = asyncio.create_task(show_progress(batch_processor, update_interval=0.01))
        updater_task = asyncio.create_task(update_progress())
        
        await asyncio.gather(progress_task, updater_task)
        
        # Check that output was generated
        captured = capsys.readouterr()
        assert "[Batch Progress]" in captured.out