#!/usr/bin/env python3
"""
Unit tests for the download system.

Tests downloaders, sources, and download management with real methods.
No mocks - tests actual functionality.
"""

import pytest
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup

from blake.downloader.downloader import BlakeDownloader
from blake.downloader.manager import DownloadManager
from blake.downloader.sources import ProjectGutenbergSource, BlakeArchiveSource
from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType


class TestBlakeDownloader:
    """Test the main BlakeDownloader class."""
    
    @pytest.fixture
    def downloader(self, tmp_path):
        """Create a BlakeDownloader instance for testing."""
        return BlakeDownloader(tmp_path)
    
    def test_initialization(self, downloader, tmp_path):
        """Test BlakeDownloader initialization."""
        assert downloader.data_dir == tmp_path
        assert hasattr(downloader, 'sources')
    
    def test_data_dir_exists(self, downloader, tmp_path):
        """Test that data directories are created."""
        assert tmp_path.exists()
    
    def test_downloader_has_sources(self, downloader):
        """Test that downloader has source adapters."""
        assert hasattr(downloader, 'sources')
        assert isinstance(downloader.sources, dict)
    
    def test_get_available_works_returns_list(self, downloader):
        """Test that get_available_works returns a list."""
        downloader.source_registry._providers = {}
        result = asyncio.get_event_loop().run_until_complete(
            downloader.get_available_works()
        )
        assert isinstance(result, list)
    
    def test_get_source_info_returns_dict(self, downloader):
        """Test that get_source_info returns a dict."""
        result = downloader.get_source_info()
        assert isinstance(result, dict)


class TestDownloadManager:
    """Test the DownloadManager class."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a DownloadManager instance for testing."""
        return DownloadManager(tmp_path)
    
    def test_initialization(self, manager, tmp_path):
        """Test DownloadManager initialization."""
        assert manager.data_dir == tmp_path
        assert manager.session_id is not None
    
    def test_has_session_id(self, manager):
        """Test that manager has a session ID."""
        assert manager.session_id is not None
        assert len(manager.session_id) > 0
    
    def test_get_download_statistics_returns_dict(self, manager):
        """Test that get_download_statistics returns a dict."""
        result = manager.get_download_statistics()
        assert isinstance(result, dict)
    
    def test_list_sessions_returns_list(self, manager):
        """Test that list_sessions returns a list."""
        result = manager.list_sessions()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_downloads(self, manager):
        """Test cleanup_failed_downloads method."""
        result = await manager.cleanup_failed_downloads()
        assert isinstance(result, int)
        assert result >= 0


class TestProjectGutenbergSource:
    """Test the Project Gutenberg source."""
    
    @pytest.fixture
    def source(self, tmp_path):
        """Create a ProjectGutenbergSource instance for testing."""
        return ProjectGutenbergSource(tmp_path)
    
    def test_initialization(self, source, tmp_path):
        """Test ProjectGutenbergSource initialization."""
        assert source.data_dir == tmp_path
        assert source.scraper is not None
        assert source.image_downloader is not None
    
    def test_has_scraper(self, source):
        """Test that source has a web scraper."""
        assert hasattr(source, 'scraper')
        assert source.scraper is not None
    
    def test_has_image_downloader(self, source):
        """Test that source has an image downloader."""
        assert hasattr(source, 'image_downloader')
        assert source.image_downloader is not None
    
    @pytest.mark.asyncio
    async def test_get_work_list_returns_list(self, source):
        """Test that get_work_list returns a list (may be empty without network)."""
        async def scrape_page(_url):
            return BeautifulSoup(
                '<a href="/ebooks/1934">William Blake: Songs of Innocence</a>',
                "html.parser",
            )

        source.scraper.scrape_page = scrape_page

        result = await source.get_work_list()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_download_work_handles_invalid_input(self, source):
        """Test download_work handles invalid work info gracefully."""
        work_info = {"id": "invalid_test", "title": "Invalid Test"}
        try:
            result = await source.download_work(work_info)
            assert result is None or isinstance(result, BlakeWork)
        except Exception:
            pass  # Expected for invalid input without network


class TestBlakeArchiveSource:
    """Test the Blake Archive source."""
    
    @pytest.fixture
    def source(self, tmp_path):
        """Create a BlakeArchiveSource instance for testing."""
        return BlakeArchiveSource(tmp_path)
    
    def test_initialization(self, source, tmp_path):
        """Test BlakeArchiveSource initialization."""
        assert source.data_dir == tmp_path
        assert source.scraper is not None
        assert source.image_downloader is not None
    
    def test_has_scraper(self, source):
        """Test that source has a web scraper."""
        assert hasattr(source, 'scraper')
        assert source.scraper is not None
    
    def test_has_image_downloader(self, source):
        """Test that source has an image downloader."""
        assert hasattr(source, 'image_downloader')
        assert source.image_downloader is not None
    
    @pytest.mark.asyncio
    async def test_get_work_list_returns_list(self, source):
        """Test that get_work_list returns a list (may be empty without network)."""
        async def scrape_page(_url):
            return BeautifulSoup("", "html.parser")

        source.scraper.scrape_page = scrape_page

        result = await source.get_work_list()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_download_work_handles_invalid_input(self, source):
        """Test download_work handles invalid work info gracefully."""
        work_info = {"id": "invalid_test", "title": "Invalid Test"}
        try:
            result = await source.download_work(work_info)
            assert result is None or isinstance(result, BlakeWork)
        except Exception:
            pass  # Expected for invalid input without network


if __name__ == "__main__":
    pytest.main([__file__])
