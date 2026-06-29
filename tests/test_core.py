"""
Tests for Blake core functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from blake import BlakeCorpus
from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType


class TestBlakeCorpus:
    """Test BlakeCorpus core class."""
    
    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create temporary data directory."""
        return tmp_path / "blake_data"
    
    @pytest.fixture
    def blake_works(self, data_dir):
        """Create BlakeCorpus instance."""
        return BlakeCorpus(data_dir)
    
    def test_initialization(self, blake_works, data_dir):
        """Test BlakeCorpus initialization."""
        assert blake_works.data_dir == data_dir
        assert data_dir.exists()
        assert blake_works.downloader is not None
        assert blake_works.metadata_manager is not None
        assert blake_works.analyzer is not None
        assert blake_works.gui is not None
        assert blake_works.exporter is not None
    
    @pytest.mark.asyncio
    async def test_download_work(self, blake_works):
        """Test downloading a single work."""
        # Mock the downloader
        mock_work = BlakeWork(
            id="test_work",
            metadata=BlakeMetadata(
                id="test_work",
                title="Test Work",
                work_type=WorkType.POEM,
                source=SourceType.BLAKE_ARCHIVE
            )
        )
        
        with patch.object(blake_works.downloader, 'download_work', return_value=mock_work):
            with patch.object(blake_works.metadata_manager, 'process_work', return_value=mock_work):
                result = await blake_works.download_work("test_work")
                
                assert result is not None
                assert result.id == "test_work"
                assert result.metadata.title == "Test Work"
    
    @pytest.mark.asyncio
    async def test_analyze_work(self, blake_works):
        """Test analyzing a work."""
        # Create mock work
        work = BlakeWork(
            id="test_work",
            metadata=BlakeMetadata(
                id="test_work",
                title="Test Work",
                work_type=WorkType.POEM,
                source=SourceType.BLAKE_ARCHIVE
            ),
            text_content="This is a test poem."
        )
        
        # Mock the analyzer
        mock_results = {
            'text_analysis': {'sentiment': 'positive'},
            'visual_analysis': {},
            'cross_analysis': {}
        }
        
        with patch.object(blake_works, 'get_work', return_value=work):
            with patch.object(blake_works.analyzer, 'analyze_work', return_value=mock_results):
                with patch.object(blake_works.metadata_manager, 'save_work'):
                    result = await blake_works.analyze_work("test_work")
                    
                    assert result == mock_results
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, blake_works):
        """Test getting collection statistics."""
        # Mock works
        works = [
            BlakeWork(
                id="work1",
                metadata=BlakeMetadata(
                    id="work1",
                    title="Work 1",
                    work_type=WorkType.POEM,
                    source=SourceType.BLAKE_ARCHIVE
                )
            ),
            BlakeWork(
                id="work2",
                metadata=BlakeMetadata(
                    id="work2",
                    title="Work 2",
                    work_type=WorkType.PAINTING,
                    source=SourceType.BLAKE_ARCHIVE
                )
            )
        ]
        
        with patch.object(blake_works, 'get_all_works', return_value=works):
            stats = await blake_works.get_statistics()
            
            assert stats['total_works'] == 2
            assert stats['work_types']['poem'] == 1
            assert stats['work_types']['painting'] == 1
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, blake_works):
        """Test clearing the works cache."""
        # Add something to cache
        blake_works._works_cache['test'] = Mock()
        assert 'test' in blake_works._works_cache
        
        # Clear cache
        await blake_works.clear_cache()
        assert len(blake_works._works_cache) == 0

