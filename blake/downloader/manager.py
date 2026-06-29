"""
Comprehensive download manager for Blake works.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from .downloader import BlakeDownloader
from .sources import BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource
from ..models import BlakeWork, SourceType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class DownloadManager:
    """
    Comprehensive download manager with progress tracking and error recovery.
    """
    
    def __init__(self, data_dir: Path, max_concurrent: int = 3):
        """
        Initialize download manager.
        
        Args:
            data_dir: Directory to store downloaded data
            max_concurrent: Maximum concurrent downloads
        """
        self.data_dir = data_dir
        self.max_concurrent = max_concurrent
        self.downloader = BlakeDownloader(data_dir)
        
        # Progress tracking
        self.progress_file = data_dir / "download_progress.json"
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load existing progress
        self.progress = self._load_progress()
        
        logger.info(f"Initialized DownloadManager with session ID: {self.session_id}")
    
    def _load_progress(self) -> Dict[str, Any]:
        """Load download progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading progress file: {e}")
        
        return {
            'sessions': {},
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'last_updated': None
        }
    
    def _save_progress(self) -> None:
        """Save download progress to file."""
        try:
            self.progress['last_updated'] = datetime.now().isoformat()
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    async def download_all_sources(self, force: bool = False, 
                                 sources: Optional[List[SourceType]] = None) -> Dict[str, Any]:
        """
        Download from all sources with comprehensive tracking.
        
        Args:
            force: Force re-download even if works exist
            sources: List of sources to download from
            
        Returns:
            Dictionary with download results
        """
        if sources is None:
            sources = list(SourceType)
        
        logger.info(f"Starting comprehensive download from {len(sources)} sources")
        
        # Initialize session progress
        session_progress = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'sources': {},
            'total_works': 0,
            'successful_works': 0,
            'failed_works': 0,
            'errors': []
        }
        
        self.progress['sessions'][self.session_id] = session_progress
        
        try:
            # Download from each source
            for source_type in sources:
                logger.info(f"Downloading from {source_type}")
                
                source_progress = {
                    'source': source_type.value,
                    'start_time': datetime.now().isoformat(),
                    'works_found': 0,
                    'works_downloaded': 0,
                    'works_skipped': 0,
                    'works_failed': 0,
                    'errors': []
                }
                
                try:
                    # Get work list
                    work_list = await self.downloader.sources[source_type].get_work_list()
                    source_progress['works_found'] = len(work_list)
                    
                    logger.info(f"Found {len(work_list)} works in {source_type}")
                    
                    # Download works with progress tracking
                    downloaded_works = await self._download_works_with_progress(
                        work_list, source_type, force, source_progress
                    )
                    
                    source_progress['works_downloaded'] = len(downloaded_works)
                    session_progress['total_works'] += len(work_list)
                    session_progress['successful_works'] += len(downloaded_works)
                    
                    logger.info(f"Downloaded {len(downloaded_works)} works from {source_type}")
                    
                except Exception as e:
                    error_msg = f"Error downloading from {source_type}: {e}"
                    logger.error(error_msg)
                    source_progress['errors'].append(error_msg)
                    session_progress['errors'].append(error_msg)
                
                source_progress['end_time'] = datetime.now().isoformat()
                session_progress['sources'][source_type.value] = source_progress
            
            # Finalize session
            session_progress['end_time'] = datetime.now().isoformat()
            session_progress['status'] = 'completed'
            
            # Update global progress
            self.progress['total_downloads'] += session_progress['total_works']
            self.progress['successful_downloads'] += session_progress['successful_works']
            self.progress['failed_downloads'] += (session_progress['total_works'] - 
                                                session_progress['successful_works'])
            
            self._save_progress()
            
            logger.info(f"Download session completed: {session_progress['successful_works']}/{session_progress['total_works']} works")
            
            return session_progress
            
        except Exception as e:
            logger.error(f"Download session failed: {e}")
            session_progress['status'] = 'failed'
            session_progress['end_time'] = datetime.now().isoformat()
            session_progress['errors'].append(str(e))
            self._save_progress()
            return session_progress
    
    async def _download_works_with_progress(self, work_list: List[Dict[str, Any]], 
                                          source_type: SourceType, force: bool,
                                          source_progress: Dict[str, Any]) -> List[BlakeWork]:
        """Download works with detailed progress tracking."""
        downloaded_works = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_single_work(work_info: Dict[str, Any]) -> Optional[BlakeWork]:
            async with semaphore:
                work_id = work_info.get('id', 'unknown')
                
                try:
                    # Check if work already exists
                    if not force and await self.downloader._work_exists_and_complete(work_id):
                        source_progress['works_skipped'] += 1
                        logger.debug(f"Skipping existing work: {work_id}")
                        return None
                    
                    # Download work
                    work = await self.downloader.sources[source_type].download_work(work_info)
                    
                    if work:
                        source_progress['works_downloaded'] += 1
                        logger.debug(f"Downloaded work: {work_id}")
                        return work
                    else:
                        source_progress['works_failed'] += 1
                        logger.warning(f"Failed to download work: {work_id}")
                        return None
                        
                except Exception as e:
                    error_msg = f"Error downloading work {work_id}: {e}"
                    logger.error(error_msg)
                    source_progress['errors'].append(error_msg)
                    source_progress['works_failed'] += 1
                    return None
        
        tasks = [download_single_work(work_info) for work_info in work_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful downloads
        for result in results:
            if isinstance(result, BlakeWork):
                downloaded_works.append(result)
        
        return downloaded_works
    
    async def resume_download(self, session_id: str) -> Dict[str, Any]:
        """
        Resume a previous download session.
        
        Args:
            session_id: ID of session to resume
            
        Returns:
            Dictionary with resume results
        """
        if session_id not in self.progress['sessions']:
            raise DownloadError(f"Session {session_id} not found")
        
        session = self.progress['sessions'][session_id]
        logger.info(f"Resuming download session: {session_id}")
        
        # Resume from where we left off
        # This is a simplified implementation - in practice, you'd track individual work status
        return await self.download_all_sources(force=False)
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download statistics."""
        stats = {
            'total_downloads': self.progress['total_downloads'],
            'successful_downloads': self.progress['successful_downloads'],
            'failed_downloads': self.progress['failed_downloads'],
            'success_rate': 0,
            'sessions': len(self.progress['sessions']),
            'last_updated': self.progress['last_updated']
        }
        
        if stats['total_downloads'] > 0:
            stats['success_rate'] = stats['successful_downloads'] / stats['total_downloads']
        
        return stats
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific download session."""
        return self.progress['sessions'].get(session_id)
    
    def list_sessions(self) -> List[Dict[str, str]]:
        """List all download sessions."""
        sessions = []
        for session_id, session in self.progress['sessions'].items():
            sessions.append({
                'session_id': session_id,
                'start_time': session.get('start_time'),
                'end_time': session.get('end_time'),
                'status': session.get('status', 'unknown'),
                'total_works': session.get('total_works', 0),
                'successful_works': session.get('successful_works', 0)
            })
        
        return sorted(sessions, key=lambda x: x['start_time'], reverse=True)
    
    async def cleanup_failed_downloads(self) -> int:
        """
        Clean up files from failed downloads.
        
        Returns:
            Number of files cleaned up
        """
        logger.info("Cleaning up failed downloads")
        
        cleaned_count = 0
        
        # Check for incomplete files (0 bytes or very small)
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    if file_size == 0 or file_size < 100:  # Less than 100 bytes
                        logger.debug(f"Removing incomplete file: {file_path}")
                        file_path.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Error checking file {file_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} incomplete files")
        return cleaned_count
    
    async def verify_downloads(self) -> Dict[str, Any]:
        """
        Verify integrity of downloaded files.
        
        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying downloaded files")
        
        verification_results = {
            'total_files': 0,
            'valid_files': 0,
            'corrupted_files': 0,
            'missing_files': 0,
            'errors': []
        }
        
        # Check all downloaded files
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.endswith('.json'):
                verification_results['total_files'] += 1
                
                try:
                    # Basic file integrity check
                    file_size = file_path.stat().st_size
                    if file_size > 0:
                        verification_results['valid_files'] += 1
                    else:
                        verification_results['corrupted_files'] += 1
                        logger.warning(f"Empty file found: {file_path}")
                        
                except Exception as e:
                    verification_results['corrupted_files'] += 1
                    verification_results['errors'].append(f"Error checking {file_path}: {e}")
        
        logger.info(f"Verification completed: {verification_results['valid_files']}/{verification_results['total_files']} files valid")
        return verification_results
