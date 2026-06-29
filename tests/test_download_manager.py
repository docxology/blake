"""
Tests for download manager functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil
import json

from blake.downloader.manager import DownloadManager
from blake.models import SourceType, BlakeWork, BlakeMetadata, WorkType
from blake.exceptions import DownloadError


class TestDownloadManager:
    """Test DownloadManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def download_manager(self, temp_dir):
        """Create DownloadManager instance."""
        return DownloadManager(temp_dir, max_concurrent=2)
    
    def test_initialization(self, download_manager, temp_dir):
        """Test download manager initialization."""
        assert download_manager.data_dir == temp_dir
        assert download_manager.max_concurrent == 2
        assert download_manager.session_id is not None
        assert 'sessions' in download_manager.progress
    
    def test_load_progress(self, download_manager):
        """Test loading progress from file."""
        # Test with non-existent file
        progress = download_manager._load_progress()
        assert 'sessions' in progress
        assert 'total_downloads' in progress
    
    def test_save_progress(self, download_manager):
        """Test saving progress to file."""
        # Modify progress
        download_manager.progress['test_key'] = 'test_value'
        
        # Save and reload
        download_manager._save_progress()
        
        # Check file exists
        assert download_manager.progress_file.exists()
        
        # Load and verify
        with open(download_manager.progress_file, 'r') as f:
            saved_progress = json.load(f)
        assert saved_progress['test_key'] == 'test_value'
    
    @pytest.mark.asyncio
    async def test_download_all_sources(self, download_manager):
        """Test downloading from all sources."""
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
        
        with patch.object(download_manager.downloader, 'sources') as mock_sources:
            # Mock source
            mock_source = Mock()
            mock_source.get_work_list = AsyncMock(return_value=[
                {'id': 'work1', 'title': 'Work 1', 'url': 'http://example.com/1'}
            ])
            mock_source.download_work = AsyncMock(return_value=mock_work)
            
            # Set up sources
            mock_sources.__getitem__.return_value = mock_source
            
            # Run download
            results = await download_manager.download_all_sources(
                sources=[SourceType.BLAKE_ARCHIVE]
            )
            
            # Verify results
            assert results['status'] == 'completed'
            assert results['total_works'] == 1
            assert results['successful_works'] == 1
            assert SourceType.BLAKE_ARCHIVE.value in results['sources']
    
    @pytest.mark.asyncio
    async def test_download_with_errors(self, download_manager):
        """Test download handling with errors."""
        with patch.object(download_manager.downloader, 'sources') as mock_sources:
            # Mock source that raises error
            mock_source = Mock()
            mock_source.get_work_list = AsyncMock(side_effect=Exception("Network error"))
            
            mock_sources.__getitem__.return_value = mock_source
            
            # Run download
            results = await download_manager.download_all_sources(
                sources=[SourceType.BLAKE_ARCHIVE]
            )
            
            # Verify error handling
            assert results['status'] == 'completed'  # Session completed despite errors
            assert len(results['errors']) > 0
            assert SourceType.BLAKE_ARCHIVE.value in results['sources']
            assert len(results['sources'][SourceType.BLAKE_ARCHIVE.value]['errors']) > 0
    
    def test_get_download_statistics(self, download_manager):
        """Test getting download statistics."""
        # Set up some test data
        download_manager.progress['total_downloads'] = 100
        download_manager.progress['successful_downloads'] = 80
        download_manager.progress['failed_downloads'] = 20
        
        stats = download_manager.get_download_statistics()
        
        assert stats['total_downloads'] == 100
        assert stats['successful_downloads'] == 80
        assert stats['failed_downloads'] == 20
        assert stats['success_rate'] == 0.8
        assert stats['sessions'] == 0  # No sessions yet
    
    def test_list_sessions(self, download_manager):
        """Test listing download sessions."""
        # Add a test session
        download_manager.progress['sessions']['test_session'] = {
            'session_id': 'test_session',
            'start_time': '2023-01-01T00:00:00',
            'end_time': '2023-01-01T01:00:00',
            'status': 'completed',
            'total_works': 10,
            'successful_works': 8
        }
        
        sessions = download_manager.list_sessions()
        
        assert len(sessions) == 1
        assert sessions[0]['session_id'] == 'test_session'
        assert sessions[0]['status'] == 'completed'
        assert sessions[0]['total_works'] == 10
    
    def test_get_session_details(self, download_manager):
        """Test getting session details."""
        # Add a test session
        test_session = {
            'session_id': 'test_session',
            'start_time': '2023-01-01T00:00:00',
            'status': 'completed'
        }
        download_manager.progress['sessions']['test_session'] = test_session
        
        # Get details
        details = download_manager.get_session_details('test_session')
        assert details == test_session
        
        # Test non-existent session
        details = download_manager.get_session_details('nonexistent')
        assert details is None
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_downloads(self, download_manager):
        """Test cleaning up failed downloads."""
        # Create some test files
        test_dir = download_manager.data_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create empty file (should be cleaned up)
        empty_file = test_dir / "empty.txt"
        empty_file.touch()
        
        # Create small file (should be cleaned up)
        small_file = test_dir / "small.txt"
        small_file.write_text("x")  # 1 byte
        
        # Create normal file (should not be cleaned up - must be >= 100 bytes)
        normal_file = test_dir / "normal.txt"
        normal_file.write_text("This is a normal file with sufficient content that exceeds the 100 byte threshold for cleanup operations. Adding more text to ensure we pass the threshold safely.")
        
        # Run cleanup
        cleaned_count = await download_manager.cleanup_failed_downloads()
        
        # Verify results - at least 2 files should be cleaned (empty and small)
        assert cleaned_count >= 2
        assert not empty_file.exists()
        assert not small_file.exists()
        assert normal_file.exists()
    
    @pytest.mark.asyncio
    async def test_verify_downloads(self, download_manager):
        """Test verifying downloads."""
        # Create some test files
        test_dir = download_manager.data_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create valid file
        valid_file = test_dir / "valid.txt"
        valid_file.write_text("Valid content")
        
        # Create empty file (corrupted)
        empty_file = test_dir / "empty.txt"
        empty_file.touch()
        
        # Run verification
        results = await download_manager.verify_downloads()
        
        # Verify results
        assert results['total_files'] == 2
        assert results['valid_files'] == 1
        assert results['corrupted_files'] == 1
        assert results['missing_files'] == 0
    
    @pytest.mark.asyncio
    async def test_resume_download(self, download_manager):
        """Test resuming a download session."""
        # Add a test session
        test_session = {
            'session_id': 'test_session',
            'start_time': '2023-01-01T00:00:00',
            'status': 'in_progress'
        }
        download_manager.progress['sessions']['test_session'] = test_session
        
        # Mock the download process
        with patch.object(download_manager, 'download_all_sources', return_value={'status': 'completed'}) as mock_download:
            results = await download_manager.resume_download('test_session')
            
            assert results['status'] == 'completed'
            mock_download.assert_called_once_with(force=False)
    
    @pytest.mark.asyncio
    async def test_resume_nonexistent_session(self, download_manager):
        """Test resuming a non-existent session."""
        with pytest.raises(DownloadError):
            await download_manager.resume_download('nonexistent_session')

