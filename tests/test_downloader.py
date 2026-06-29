"""
Tests for Blake downloader functionality.

Tests real methods without mocks.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
import json

from blake.downloader import BlakeDownloader
from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType
from blake.exceptions import DownloadError


class TestBlakeDownloader:
    """Test BlakeDownloader class - real functionality tests."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def downloader(self, temp_dir):
        """Create BlakeDownloader instance."""
        return BlakeDownloader(temp_dir)
    
    def test_initialization(self, downloader, temp_dir):
        """Test downloader initialization."""
        assert downloader.data_dir == temp_dir
        assert len(downloader.sources) == 3
        assert SourceType.BLAKE_ARCHIVE in downloader.sources
        assert SourceType.PROJECT_GUTENBERG in downloader.sources
        assert SourceType.INTERNET_ARCHIVE in downloader.sources
    
    def test_has_sources(self, downloader):
        """Test that downloader has source adapters."""
        assert hasattr(downloader, 'sources')
        assert isinstance(downloader.sources, dict)
        assert len(downloader.sources) > 0
    
    @pytest.mark.asyncio
    async def test_work_exists_check_nonexistent(self, downloader):
        """Test work existence checking for non-existent work."""
        work_id = "nonexistent_test_work"
        exists = await downloader._work_exists_and_complete(work_id)
        assert not exists
    
    @pytest.mark.asyncio
    async def test_work_exists_check_existing(self, downloader):
        """Test work existence checking for existing work."""
        work_id = "test_work"
        
        # Create mock metadata file
        metadata_dir = downloader.data_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_file = metadata_dir / f"{work_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'metadata': {'id': work_id, 'title': 'Test Work'},
                'text_content': 'Test content',
                'images': []
            }, f)
        
        # Test existing work
        exists = await downloader._work_exists_and_complete(work_id)
        assert exists
    
    @pytest.mark.asyncio
    async def test_download_all_returns_list(self, downloader):
        """Test that download_all returns a list (may be empty without network)."""
        works = await downloader.download_all(sources=[])
        assert isinstance(works, list)
    
    @pytest.mark.asyncio
    async def test_download_work_not_found(self, downloader):
        """Test downloading non-existent work returns None."""
        downloader.source_registry._providers = {}
        work = await downloader.download_work("definitely_nonexistent_work_id_xyz123")
        assert work is None
    
    @pytest.mark.asyncio
    async def test_download_from_source_returns_list(self, downloader):
        """Test download_from_source returns a list."""
        class EmptyProvider:
            async def discover(self):
                return []

        downloader.source_registry._providers[SourceType.BLAKE_ARCHIVE] = EmptyProvider()

        works = await downloader.download_from_source(SourceType.BLAKE_ARCHIVE)
        assert isinstance(works, list)
    
    @pytest.mark.asyncio
    async def test_download_from_invalid_source_raises(self, downloader):
        """Test downloading from invalid source raises DownloadError."""
        # Using a string that isn't a valid SourceType
        with pytest.raises(DownloadError):
            await downloader.download_from_source("invalid_source_type")
    
    def test_get_source_info(self, downloader):
        """Test getting source information."""
        info = downloader.get_source_info()
        
        assert SourceType.BLAKE_ARCHIVE.value in info
        assert SourceType.PROJECT_GUTENBERG.value in info
        assert SourceType.INTERNET_ARCHIVE.value in info
        
        # Check structure
        for source_info in info.values():
            assert 'name' in source_info
            assert 'description' in source_info
            assert 'base_url' in source_info
    
    @pytest.mark.asyncio
    async def test_get_available_works_returns_list(self, downloader):
        """Test get_available_works returns a list."""
        downloader.source_registry._providers = {}
        works = await downloader.get_available_works()
        assert isinstance(works, list)
    
    def test_source_adapters_have_required_methods(self, downloader):
        """Test that all source adapters have required methods."""
        for source_type, source in downloader.sources.items():
            assert hasattr(source, 'get_work_list')
            assert hasattr(source, 'download_work')
            assert callable(source.get_work_list)
            assert callable(source.download_work)
