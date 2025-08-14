"""Integration tests for the analysis pipeline."""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.core.pipeline import AnalysisPipeline
from src.core.config import AnalysisConfig
from src.core.agent_base import AgentResult


class TestPipelineIntegration:
    """Test the full analysis pipeline flow."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create a test configuration."""
        config = Mock(spec=AnalysisConfig)
        config.prompts_dir = Path("config/prompts")
        config.analyses_dir = tmp_path / "analyses"
        config.logs_dir = tmp_path / "logs"
        
        # Create directories
        config.analyses_dir.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        
        return config
    
    @pytest.fixture
    def pipeline(self, config):
        """Create a pipeline instance."""
        return AnalysisPipeline(config)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_basic_pipeline_flow(self, pipeline, config, tmp_path):
        """Test basic pipeline execution with mocked agents."""
        # Mock the analyst agent
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(return_value=AgentResult(
            success=True,
            content="# Test Analysis\n\nThis is a test analysis.",
            metadata={"duration": 1.0}
        ))
        
        # Mock the reviewer agent
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(return_value=AgentResult(
            success=True,
            content=json.dumps({
                "decision": "accept",
                "feedback": {
                    "positive": ["Good structure"],
                    "critical": [],
                    "suggestions": []
                }
            }),
            metadata={"duration": 0.5}
        ))
        
        # Register mocked agents
        pipeline.register_agent("analyst", mock_analyst)
        pipeline.register_agent("reviewer", mock_reviewer)
        
        # Run the pipeline
        with patch('src.core.pipeline.AnalystAgent', return_value=mock_analyst), \
             patch('src.core.pipeline.ReviewerAgent', return_value=mock_reviewer):
            
            result = await pipeline.run_analyst_reviewer_loop(
                idea="Test business idea",
                max_iterations=1,
                debug=False,
                use_websearch=False
            )
        
        # Verify result structure
        assert result["success"] is True
        assert "final_analysis" in result
        assert "iteration_count" in result
        assert result["iteration_count"] == 1
        
        # Verify agents were called
        mock_analyst.process.assert_called_once()
        mock_reviewer.process.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_reviewer_rejection(self, pipeline, config, tmp_path):
        """Test pipeline when reviewer rejects and requests revision."""
        # Mock analyst with improving responses
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(side_effect=[
            AgentResult(
                success=True,
                content="# Initial Analysis\n\nShort and incomplete.",
                metadata={"duration": 1.0}
            ),
            AgentResult(
                success=True,
                content="# Improved Analysis\n\nMuch more detailed and complete analysis.",
                metadata={"duration": 1.5}
            )
        ])
        
        # Mock reviewer that rejects first, accepts second
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(side_effect=[
            AgentResult(
                success=True,
                content=json.dumps({
                    "decision": "reject",
                    "feedback": {
                        "positive": ["Good start"],
                        "critical": ["Too short", "Missing market analysis"],
                        "suggestions": ["Add more detail", "Include competition"]
                    }
                }),
                metadata={"duration": 0.5}
            ),
            AgentResult(
                success=True,
                content=json.dumps({
                    "decision": "accept",
                    "feedback": {
                        "positive": ["Much improved", "Good detail"],
                        "critical": [],
                        "suggestions": []
                    }
                }),
                metadata={"duration": 0.5}
            )
        ])
        
        # Register mocked agents
        pipeline.register_agent("analyst", mock_analyst)
        pipeline.register_agent("reviewer", mock_reviewer)
        
        # Run the pipeline
        with patch('src.core.pipeline.AnalystAgent', return_value=mock_analyst), \
             patch('src.core.pipeline.ReviewerAgent', return_value=mock_reviewer):
            
            result = await pipeline.run_analyst_reviewer_loop(
                idea="Test business idea",
                max_iterations=3,
                debug=False,
                use_websearch=False
            )
        
        # Verify iterations
        assert result["success"] is True
        assert result["iteration_count"] == 2
        assert "Improved Analysis" in result["final_analysis"]
        
        # Verify agents were called correct number of times
        assert mock_analyst.process.call_count == 2
        assert mock_reviewer.process.call_count == 2
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_max_iterations(self, pipeline, config, tmp_path):
        """Test pipeline stops at max iterations."""
        # Mock analyst
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(return_value=AgentResult(
            success=True,
            content="# Analysis\n\nSome content.",
            metadata={"duration": 1.0}
        ))
        
        # Mock reviewer that always rejects
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(return_value=AgentResult(
            success=True,
            content=json.dumps({
                "decision": "reject",
                "feedback": {
                    "positive": [],
                    "critical": ["Still not good enough"],
                    "suggestions": ["Keep trying"]
                }
            }),
            metadata={"duration": 0.5}
        ))
        
        # Register mocked agents
        pipeline.register_agent("analyst", mock_analyst)
        pipeline.register_agent("reviewer", mock_reviewer)
        
        # Run the pipeline with max 2 iterations
        with patch('src.core.pipeline.AnalystAgent', return_value=mock_analyst), \
             patch('src.core.pipeline.ReviewerAgent', return_value=mock_reviewer):
            
            result = await pipeline.run_analyst_reviewer_loop(
                idea="Test business idea",
                max_iterations=2,
                debug=False,
                use_websearch=False
            )
        
        # Verify it stopped at max iterations
        assert result["success"] is True
        assert result["iteration_count"] == 2
        assert mock_analyst.process.call_count == 2
        assert mock_reviewer.process.call_count == 2
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_error_handling(self, pipeline, config, tmp_path):
        """Test pipeline handles agent errors gracefully."""
        # Mock analyst that fails
        mock_analyst = AsyncMock()
        mock_analyst.process = AsyncMock(return_value=AgentResult(
            success=False,
            content="",
            error="API rate limit exceeded",
            metadata={"duration": 0.1}
        ))
        
        # Register mocked agent
        pipeline.register_agent("analyst", mock_analyst)
        
        # Run the pipeline
        with patch('src.core.pipeline.AnalystAgent', return_value=mock_analyst):
            
            result = await pipeline.run_analyst_reviewer_loop(
                idea="Test business idea",
                max_iterations=1,
                debug=False,
                use_websearch=False
            )
        
        # Verify error handling
        assert result["success"] is False
        assert "error" in result
        assert "API rate limit" in result["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_pipeline_file_creation(self, pipeline, config, tmp_path):
        """Test that pipeline creates appropriate files."""
        # Create test idea slug
        idea_slug = "test-business-idea"
        idea_dir = config.analyses_dir / idea_slug
        idea_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial analysis file
        analysis_file = idea_dir / "analysis.md"
        analysis_file.write_text("# Initial Analysis\n\nTest content.")
        
        # Mock reviewer
        mock_reviewer = AsyncMock()
        mock_reviewer.process = AsyncMock(return_value=AgentResult(
            success=True,
            content=json.dumps({
                "decision": "accept",
                "feedback": {
                    "positive": ["Good"],
                    "critical": [],
                    "suggestions": []
                }
            }),
            metadata={"duration": 0.5}
        ))
        
        # Test that reviewer can read the file
        from src.agents.reviewer import ReviewerAgent
        reviewer = ReviewerAgent(config)
        
        # Validate the path works
        validated_path = reviewer._validate_analysis_path(str(idea_dir))
        assert validated_path.exists()
        assert (validated_path / "analysis.md").exists()