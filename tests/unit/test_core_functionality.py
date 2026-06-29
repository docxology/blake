#!/usr/bin/env python3
"""
Unit tests for core Blake functionality.

Tests the main orchestrator and core components with real methods.
No mocks - tests actual functionality.
"""

import pytest
import asyncio
from pathlib import Path

from blake.core import BlakeWorks
from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType


class TestBlakeWorks:
    """Test the main BlakeWorks orchestrator."""
    
    @pytest.fixture
    def blake_works(self, tmp_path):
        """Create a BlakeWorks instance for testing."""
        return BlakeWorks(tmp_path)
    
    def test_initialization(self, blake_works, tmp_path):
        """Test BlakeWorks initialization."""
        assert blake_works.data_dir == tmp_path
        assert blake_works.downloader is not None
        assert blake_works.analyzer is not None
        assert blake_works.gui is not None
        assert blake_works.exporter is not None
        assert blake_works.visualization is not None
    
    def test_has_downloader(self, blake_works):
        """Test that BlakeWorks has a downloader component."""
        assert hasattr(blake_works, 'downloader')
        assert blake_works.downloader is not None
    
    def test_has_analyzer(self, blake_works):
        """Test that BlakeWorks has an analyzer component."""
        assert hasattr(blake_works, 'analyzer')
        assert blake_works.analyzer is not None
    
    def test_has_exporter(self, blake_works):
        """Test that BlakeWorks has an exporter component."""
        assert hasattr(blake_works, 'exporter')
        assert blake_works.exporter is not None
    
    def test_has_visualization(self, blake_works):
        """Test that BlakeWorks has a visualization component."""
        assert hasattr(blake_works, 'visualization')
        assert blake_works.visualization is not None
    
    @pytest.mark.asyncio
    async def test_download_all_method_exists(self, blake_works):
        """Test that download_all method exists and is callable."""
        assert hasattr(blake_works, 'download_all')
        assert callable(blake_works.download_all)
    
    @pytest.mark.asyncio
    async def test_get_all_works_returns_list(self, blake_works):
        """Test that get_all_works returns a list."""
        result = await blake_works.get_all_works()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_statistics_returns_dict(self, blake_works):
        """Test that get_statistics returns a dict."""
        result = await blake_works.get_statistics()
        assert isinstance(result, dict)


class TestBlakeWork:
    """Test the BlakeWork model."""
    
    def test_blake_work_creation(self):
        """Test creating a BlakeWork instance."""
        metadata = BlakeMetadata(
            id="test1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
        
        work = BlakeWork(
            id="test1",
            metadata=metadata,
            text_content="Test content",
            fully_processed=True
        )
        
        assert work.id == "test1"
        assert work.metadata.title == "Test Work"
        assert work.text_content == "Test content"
        assert work.fully_processed is True
    
    def test_blake_work_validation(self):
        """Test BlakeWork validation."""
        # Test valid work
        metadata = BlakeMetadata(
            id="test1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
        
        work = BlakeWork(
            id="test1",
            metadata=metadata,
            text_content="Test content"
        )
        
        assert work.id == "test1"
        
        # Test invalid work (missing required fields)
        with pytest.raises(ValueError):
            BlakeWork(id="test1")  # Missing metadata


class TestBlakeMetadata:
    """Test the BlakeMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating BlakeMetadata instance."""
        metadata = BlakeMetadata(
            id="test1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
        
        assert metadata.id == "test1"
        assert metadata.title == "Test Work"
        assert metadata.work_type == WorkType.POEM
        assert metadata.source == SourceType.PROJECT_GUTENBERG
    
    def test_metadata_validation(self):
        """Test metadata validation."""
        # Test valid metadata
        metadata = BlakeMetadata(
            id="test1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
        
        assert metadata.id == "test1"
        
        # Test invalid metadata (missing required fields)
        with pytest.raises(ValueError):
            BlakeMetadata(title="Test Work")  # Missing id


if __name__ == "__main__":
    pytest.main([__file__])
