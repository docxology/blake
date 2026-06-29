#!/usr/bin/env python3
"""
Test Fixed Download Methods

Tests the download infrastructure using real methods
without requiring network access.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from blake.downloader.sources import ProjectGutenbergSource
from blake.downloader import BlakeDownloader
from blake.models import SourceType


class TestDownloadInfrastructure:
    """Tests for download infrastructure - no network required."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def source(self, temp_dir):
        """Create ProjectGutenbergSource instance."""
        return ProjectGutenbergSource(temp_dir)
    
    @pytest.fixture
    def downloader(self, temp_dir):
        """Create BlakeDownloader instance."""
        return BlakeDownloader(temp_dir)


def test_single_work_download():
    """Test that single work download infrastructure exists and is configured."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        source = ProjectGutenbergSource(temp_dir)
        
        # Verify source is properly configured
        assert source.data_dir == temp_dir
        assert hasattr(source, 'get_work_list')
        assert hasattr(source, 'download_work')
        assert callable(source.get_work_list)
        assert callable(source.download_work)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_multiple_works():
    """Test that downloader can be configured for multiple works."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        downloader = BlakeDownloader(temp_dir)
        
        # Verify downloader configuration
        assert downloader.data_dir == temp_dir
        assert len(downloader.sources) >= 3
        assert SourceType.BLAKE_ARCHIVE in downloader.sources
        assert SourceType.PROJECT_GUTENBERG in downloader.sources
        assert SourceType.INTERNET_ARCHIVE in downloader.sources
        
        # Verify source info
        info = downloader.get_source_info()
        assert isinstance(info, dict)
        assert len(info) >= 3
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
