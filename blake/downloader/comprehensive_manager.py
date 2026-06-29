"""
Comprehensive download manager for acquiring hundreds of Blake works.

Uses multiple APIs and sources to download all available Blake documents,
texts, and images from web resources.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
import json

from .api_sources import GutendexAPISource, ProjectGutenbergAPISource, ImageDownloader
from .sources import ProjectGutenbergSource, BlakeArchiveSource
# from .manager import DownloadManager  # Avoid circular import
from ..models import BlakeWork, SourceType
from ..utils.unified_logger import get_logger
from ..utils.improved_error_handling import retry_on_failure, RetryConfig, ImprovedErrorRecovery, create_retry_configs
from ..utils.performance_tracker import PerformanceTracker, track_performance

logger = get_logger(__name__)


class ComprehensiveDownloadManager:
    """Comprehensive download manager using all available sources."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.api_sources = []
        self.image_downloader = None
        self.downloaded_works = set()
        self.failed_works = set()
        self.stats = {
            'total_found': 0,
            'total_downloaded': 0,
            'total_failed': 0,
            'total_images': 0,
            'sources': {}
        }
        
        # Initialize performance tracking and error recovery
        self.performance_tracker = PerformanceTracker(self.data_dir / "logs")
        self.error_recovery = ImprovedErrorRecovery(self.data_dir / "logs")
        
        # Retry configuration for different operations
        self.retry_configs = create_retry_configs()
    
    async def initialize_sources(self):
        """Initialize all available sources."""
        logger.info("Initializing comprehensive download sources")
        
        # Initialize API sources
        self.gutendex_source = GutendexAPISource(self.data_dir)
        self.pg_api_source = ProjectGutenbergAPISource(self.data_dir)
        
        # Initialize traditional sources
        self.pg_source = ProjectGutenbergSource(self.data_dir)
        self.blake_archive_source = BlakeArchiveSource(self.data_dir)
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(self.data_dir)
        
        # Initialize sessions
        await self.gutendex_source.__aenter__()
        await self.pg_api_source.__aenter__()
        await self.image_downloader.__aenter__()
        
        logger.info("All sources initialized")
    
    async def discover_all_works(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover works from all sources."""
        logger.info("🔍 Discovering works from all sources...")
        
        all_works = {}
        
        # Discover from Gutendex API
        try:
            logger.info("📚 Checking Gutendex API...")
            gutendex_works = await self.gutendex_source.get_work_list()
            all_works['gutendex'] = gutendex_works
            logger.info(f"  ✅ Found {len(gutendex_works)} works in Gutendex API")
        except Exception as e:
            logger.error(f"  ❌ Error with Gutendex API: {e}")
            all_works['gutendex'] = []
        
        # Discover from Project Gutenberg API
        try:
            logger.info("📚 Checking Project Gutenberg API...")
            pg_api_works = await self.pg_api_source.get_work_list()
            all_works['project_gutenberg_api'] = pg_api_works
            logger.info(f"  ✅ Found {len(pg_api_works)} works in Project Gutenberg API")
        except Exception as e:
            logger.error(f"  ❌ Error with Project Gutenberg API: {e}")
            all_works['project_gutenberg_api'] = []
        
        # Discover from traditional Project Gutenberg
        try:
            logger.info("📚 Checking traditional Project Gutenberg...")
            pg_works = await self.pg_source.get_work_list()
            all_works['project_gutenberg'] = pg_works
            logger.info(f"  ✅ Found {len(pg_works)} works in traditional Project Gutenberg")
        except Exception as e:
            logger.error(f"  ❌ Error with traditional Project Gutenberg: {e}")
            all_works['project_gutenberg'] = []
        
        # Discover from Blake Archive
        try:
            logger.info("🏛️ Checking Blake Archive...")
            ba_works = await self.blake_archive_source.get_work_list()
            all_works['blake_archive'] = ba_works
            logger.info(f"  ✅ Found {len(ba_works)} works in Blake Archive")
        except Exception as e:
            logger.error(f"  ❌ Error with Blake Archive: {e}")
            all_works['blake_archive'] = []
        
        # Calculate totals
        total_works = sum(len(works) for works in all_works.values())
        self.stats['total_found'] = total_works
        
        logger.info(f"📊 Discovery complete: {total_works} total works found across all sources")
        
        return all_works
    
    @track_performance("comprehensive_download")
    async def download_all_works(self) -> Dict[str, Any]:
        """Download all discovered works with enhanced error handling and progress tracking."""
        operation_id = self.performance_tracker.start_operation(
            "comprehensive_download",
            {"session_id": self.session_id, "data_dir": str(self.data_dir)}
        )
        
        try:
            logger.info("📥 Starting comprehensive download of all Blake works...")
            
            # Initialize sources
            await self.initialize_sources()
            
            # Discover works
            all_works = await self.discover_all_works()
            
            # Merge and deduplicate works
            merged_works = self._merge_works(all_works)
            
            # Download works with progress tracking
            downloaded_works = []
            failed_works = []
            
            for i, work_info in enumerate(merged_works, 1):
                try:
                    # Track progress
                    self.performance_tracker.track_progress(
                        operation_id, i, len(merged_works), 
                        work_info.get('title', 'Unknown')[:50]
                    )
                    
                    # Download work with retry
                    work = await self._download_work_with_retry(work_info, all_works)
                    
                    if work:
                        downloaded_works.append(work)
                        self.downloaded_works.add(work.id)
                        
                        # Download associated images with retry
                        try:
                            images = await self._download_images_with_retry(work)
                            work.images = images
                            self.stats['total_images'] += len(images)
                            
                            if images:
                                logger.log_download_result(
                                    work.id, work.metadata.title, True,
                                    {'characters': len(work.text_content), 'images': len(images)}
                                )
                            else:
                                logger.log_download_result(
                                    work.id, work.metadata.title, True,
                                    {'characters': len(work.text_content)}
                                )
                        
                        except Exception as e:
                            logger.log_error_with_context(
                                e, 
                                context={'work_id': work.id, 'operation': 'image_download'}
                            )
                            logger.log_download_result(
                                work.id, work.metadata.title, True,
                                {'characters': len(work.text_content), 'images': 0}
                            )
                    else:
                        failed_works.append(work_info)
                        self.failed_works.add(work_info.get('id', 'unknown'))
                        logger.log_download_result(
                            work_info.get('id', 'unknown'),
                            work_info.get('title', 'Unknown'),
                            False,
                            {'error': 'Download failed'}
                        )
                
                except Exception as e:
                    logger.log_error_with_context(
                        e, 
                        context={'work_info': work_info, 'operation': 'work_download'}
                    )
                    failed_works.append(work_info)
                    self.failed_works.add(work_info.get('id', 'unknown'))
                    logger.log_download_result(
                        work_info.get('id', 'unknown'),
                        work_info.get('title', 'Unknown'),
                        False,
                        {'error': str(e)}
                    )
            
            # Update statistics
            self.stats['total_downloaded'] = len(downloaded_works)
            self.stats['total_failed'] = len(failed_works)
            
            # Generate comprehensive report
            report = await self._generate_comprehensive_report(all_works, downloaded_works, failed_works)
            
            # Cleanup
            await self._cleanup_sources()
            
            # End performance tracking
            self.performance_tracker.end_operation(
                operation_id, 
                success=True, 
                items_processed=len(downloaded_works),
                metadata={
                    'total_found': self.stats['total_found'],
                    'total_downloaded': self.stats['total_downloaded'],
                    'total_failed': self.stats['total_failed'],
                    'total_images': self.stats['total_images']
                }
            )
            
            logger.info("🎉 Comprehensive download complete!")
            return report
            
        except Exception as e:
            # End performance tracking with error
            self.performance_tracker.end_operation(operation_id, success=False)
            logger.log_error_with_context(e, context={'operation': 'comprehensive_download'})
            raise
    
    def _merge_works(self, all_works: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Merge works from all sources, removing duplicates."""
        merged = []
        seen_ids = set()
        
        # Priority order for sources
        source_priority = [
            'gutendex',
            'project_gutenberg_api', 
            'project_gutenberg',
            'blake_archive'
        ]
        
        for source in source_priority:
            if source in all_works:
                for work in all_works[source]:
                    work_id = work.get('id')
                    if work_id and work_id not in seen_ids:
                        work['source_priority'] = source
                        merged.append(work)
                        seen_ids.add(work_id)
        
        logger.info(f"Merged {len(merged)} unique works from {len(all_works)} sources")
        return merged
    
    def _select_best_source(self, work_info: Dict[str, Any], all_works: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """Select the best source for downloading a work."""
        work_id = work_info.get('id')
        source_priority = work_info.get('source_priority', 'gutendex')
        
        # Check if work exists in the selected source
        if source_priority in all_works:
            for work in all_works[source_priority]:
                if work.get('id') == work_id:
                    return source_priority
        
        # Fallback to any available source
        for source in ['gutendex', 'project_gutenberg_api', 'project_gutenberg', 'blake_archive']:
            if source in all_works:
                for work in all_works[source]:
                    if work.get('id') == work_id:
                        return source
        
        return None
    
    async def _download_from_source(self, work_info: Dict[str, Any], source_name: str) -> Optional[BlakeWork]:
        """Download work from the specified source."""
        try:
            if source_name == 'gutendex':
                return await self.gutendex_source.download_work(work_info)
            elif source_name == 'project_gutenberg_api':
                return await self.pg_api_source.download_work(work_info)
            elif source_name == 'project_gutenberg':
                return await self.pg_source.download_work(work_info)
            elif source_name == 'blake_archive':
                return await self.blake_archive_source.download_work(work_info)
            else:
                logger.warning(f"Unknown source: {source_name}")
                return None
        except Exception as e:
            logger.error(f"Error downloading from {source_name}: {e}")
            return None
    
    async def _generate_comprehensive_report(self, all_works: Dict[str, List[Dict[str, Any]]], 
                                           downloaded_works: List[BlakeWork], 
                                           failed_works: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive download report."""
        report = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'total_works_found': self.stats['total_found'],
            'total_works_downloaded': self.stats['total_downloaded'],
            'total_works_failed': self.stats['total_failed'],
            'total_images_downloaded': self.stats['total_images'],
            'success_rate': (self.stats['total_downloaded'] / max(self.stats['total_found'], 1)) * 100,
            'sources': {},
            'downloaded_works': [],
            'failed_works': failed_works,
            'statistics': {
                'total_characters': sum(len(work.text_content) for work in downloaded_works),
                'average_work_size': sum(len(work.text_content) for work in downloaded_works) / max(len(downloaded_works), 1),
                'work_types': {},
                'languages': set(),
                'subjects': set()
            }
        }
        
        # Source breakdown
        for source_name, works in all_works.items():
            report['sources'][source_name] = {
                'works_found': len(works),
                'works_downloaded': len([w for w in downloaded_works if w.metadata.api_source == source_name]),
                'success_rate': 0
            }
        
        # Downloaded works details
        for work in downloaded_works:
            work_data = {
                'id': work.id,
                'title': work.metadata.title,
                'author': work.metadata.author,
                'work_type': work.metadata.work_type.value if hasattr(work.metadata.work_type, 'value') else str(work.metadata.work_type),
                'source': work.metadata.source.value if hasattr(work.metadata.source, 'value') else str(work.metadata.source),
                'characters': len(work.text_content),
                'images': len(work.images),
                'subjects': work.metadata.subjects,
                'languages': work.metadata.languages
            }
            report['downloaded_works'].append(work_data)
            
            # Update statistics
            work_type = work_data['work_type']
            report['statistics']['work_types'][work_type] = report['statistics']['work_types'].get(work_type, 0) + 1
            
            languages = getattr(work.metadata, 'languages', [])
            if languages:
                report['statistics']['languages'].update(languages)
                
            subjects = getattr(work.metadata, 'subjects', [])
            if subjects:
                report['statistics']['subjects'].update(subjects)
        
        # Convert sets to lists for JSON serialization
        report['statistics']['languages'] = list(report['statistics']['languages'])
        report['statistics']['subjects'] = list(report['statistics']['subjects'])
        
        # Save report
        report_path = self.data_dir / f"comprehensive_download_report_{self.session_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Comprehensive report saved: {report_path}")
        
        return report
    
    async def _cleanup_sources(self):
        """Cleanup all sources."""
        try:
            await self.gutendex_source.__aexit__(None, None, None)
            await self.pg_api_source.__aexit__(None, None, None)
            await self.image_downloader.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive download statistics."""
        return {
            'total_found': self.stats['total_found'],
            'total_downloaded': self.stats['total_downloaded'],
            'total_failed': self.stats['total_failed'],
            'total_images': self.stats['total_images'],
            'success_rate': (self.stats['total_downloaded'] / max(self.stats['total_found'], 1)) * 100,
            'downloaded_works': list(self.downloaded_works),
            'failed_works': list(self.failed_works)
        }
    
    async def _download_work_with_retry(self, work_info: Dict[str, Any], 
                                      all_works: Dict[str, List[Dict[str, Any]]]) -> Optional[BlakeWork]:
        """Download work with retry mechanism."""
        source = self._select_best_source(work_info, all_works)
        
        if not source:
            return None
        
        try:
            return await self.error_recovery.retry_async(
                self._download_from_source,
                work_info, source,
                retry_config=self.retry_configs['download']
            )
        except Exception as e:
            logger.log_error_with_context(
                e, 
                context={'work_id': work_info.get('id'), 'source': source}
            )
            return None
    
    async def _download_images_with_retry(self, work: BlakeWork) -> List[Any]:
        """Download images with retry mechanism."""
        try:
            return await self.error_recovery.retry_async(
                self.image_downloader.download_images_for_work,
                work.id, work.metadata.title,
                retry_config=self.retry_configs['image_download']
            )
        except Exception as e:
            logger.log_error_with_context(
                e, 
                context={'work_id': work.id, 'operation': 'image_download'}
            )
            return []
