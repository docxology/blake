"""
Enhanced comprehensive download manager for acquiring hundreds of Blake works.

Uses multiple enhanced APIs and sources with improved error handling,
retry mechanisms, and comprehensive discovery strategies.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
import json

from .enhanced_api_sources import EnhancedGutendexAPISource, DirectProjectGutenbergSource
from .sources import ProjectGutenbergSource, BlakeArchiveSource
from ..models import BlakeWork, SourceType
from ..utils.unified_logger import get_logger
from ..utils.improved_error_handling import retry_on_failure, RetryConfig, ImprovedErrorRecovery, create_retry_configs
from ..utils.performance_tracker import PerformanceTracker, track_performance

logger = get_logger(__name__)


class EnhancedComprehensiveDownloadManager:
    """Enhanced comprehensive download manager using all available sources with improved discovery."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        logger.info("🚀 Initializing enhanced comprehensive download sources")
        
        # Initialize enhanced API sources
        self.enhanced_gutendex = EnhancedGutendexAPISource(self.data_dir)
        self.direct_pg = DirectProjectGutenbergSource(self.data_dir)
        
        # Initialize traditional sources
        self.pg_source = ProjectGutenbergSource(self.data_dir)
        self.blake_archive_source = BlakeArchiveSource(self.data_dir)
        
        # Initialize sessions
        await self.enhanced_gutendex.__aenter__()
        await self.direct_pg.__aenter__()
        
        logger.info("✅ All enhanced sources initialized")
    
    async def discover_all_works(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover works from all sources with enhanced strategies."""
        logger.info("🔍 Enhanced discovery of works from all sources...")
        
        all_works = {}
        
        # Discover from Enhanced Gutendex API
        try:
            logger.info("📚 Checking Enhanced Gutendex API...")
            gutendex_works = await self.enhanced_gutendex.get_work_list()
            all_works['enhanced_gutendex'] = gutendex_works
            logger.info(f"  ✅ Found {len(gutendex_works)} works in Enhanced Gutendex API")
        except Exception as e:
            logger.error(f"  ❌ Error with Enhanced Gutendex API: {e}")
            all_works['enhanced_gutendex'] = []
        
        # Discover from Direct Project Gutenberg
        try:
            logger.info("📚 Checking Direct Project Gutenberg...")
            direct_pg_works = await self.direct_pg.get_work_list()
            all_works['direct_pg'] = direct_pg_works
            logger.info(f"  ✅ Found {len(direct_pg_works)} works in Direct Project Gutenberg")
        except Exception as e:
            logger.error(f"  ❌ Error with Direct Project Gutenberg: {e}")
            all_works['direct_pg'] = []
        
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
        
        logger.info(f"📊 Enhanced discovery complete: {total_works} total works found across all sources")
        
        return all_works
    
    @track_performance("enhanced_comprehensive_download")
    async def download_all_works(self) -> Dict[str, Any]:
        """Download all discovered works with enhanced error handling and progress tracking."""
        operation_id = self.performance_tracker.start_operation(
            "enhanced_comprehensive_download",
            {"session_id": self.session_id, "data_dir": str(self.data_dir)}
        )
        
        try:
            logger.info("📥 Starting enhanced comprehensive download of all Blake works...")
            
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
                        
                        logger.log_download_result(
                            work.id, work.metadata.title, True,
                            {'characters': len(work.text_content)}
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
            
            logger.info("🎉 Enhanced comprehensive download complete!")
            return report
            
        except Exception as e:
            # End performance tracking with error
            self.performance_tracker.end_operation(operation_id, success=False)
            logger.log_error_with_context(e, context={'operation': 'enhanced_comprehensive_download'})
            raise
    
    def _merge_works(self, all_works: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Merge works from all sources, removing duplicates with improved deduplication."""
        merged = []
        seen_ids = set()
        seen_titles = set()
        
        # Priority order for sources (enhanced sources first)
        source_priority = [
            'enhanced_gutendex',
            'direct_pg',
            'project_gutenberg',
            'blake_archive'
        ]
        
        for source in source_priority:
            if source in all_works:
                for work in all_works[source]:
                    work_id = work.get('id')
                    work_title = work.get('title', '').lower().strip()
                    
                    # Check for duplicates by ID and title
                    is_duplicate = False
                    
                    if work_id and work_id in seen_ids:
                        is_duplicate = True
                        logger.debug(f"Skipping duplicate work by ID: {work_id}")
                    
                    if work_title and work_title in seen_titles:
                        is_duplicate = True
                        logger.debug(f"Skipping duplicate work by title: {work_title}")
                    
                    # Also check for similar titles (fuzzy matching)
                    if not is_duplicate and work_title:
                        for seen_title in seen_titles:
                            if self._titles_similar(work_title, seen_title):
                                is_duplicate = True
                                logger.debug(f"Skipping similar work: '{work_title}' vs '{seen_title}'")
                                break
                    
                    if not is_duplicate:
                        work['source_priority'] = source
                        merged.append(work)
                        if work_id:
                            seen_ids.add(work_id)
                        if work_title:
                            seen_titles.add(work_title)
        
        logger.info(f"Merged {len(merged)} unique works from {len(all_works)} sources")
        logger.info(f"Deduplication: {sum(len(works) for works in all_works.values())} total -> {len(merged)} unique")
        return merged
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar enough to be considered duplicates."""
        try:
            # Simple similarity check based on common words
            words1 = set(title1.split())
            words2 = set(title2.split())
            
            if not words1 or not words2:
                return False
            
            # Calculate Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            similarity = intersection / union if union > 0 else 0
            
            return similarity >= threshold
        except Exception:
            return False
    
    def _select_best_source(self, work_info: Dict[str, Any], all_works: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """Select the best source for downloading a work."""
        work_id = work_info.get('id')
        source_priority = work_info.get('source_priority', 'enhanced_gutendex')
        
        # Check if work exists in the selected source
        if source_priority in all_works:
            for work in all_works[source_priority]:
                if work.get('id') == work_id:
                    return source_priority
        
        # Fallback to any available source
        for source in ['enhanced_gutendex', 'direct_pg', 'project_gutenberg', 'blake_archive']:
            if source in all_works:
                for work in all_works[source]:
                    if work.get('id') == work_id:
                        return source
        
        return None
    
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
    
    async def _download_from_source(self, work_info: Dict[str, Any], source_name: str) -> Optional[BlakeWork]:
        """Download work from the specified source."""
        try:
            if source_name == 'enhanced_gutendex':
                return await self.enhanced_gutendex.download_work(work_info)
            elif source_name == 'direct_pg':
                return await self.direct_pg.download_work(work_info)
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
                'images': len(work.images) if hasattr(work, 'images') else 0,
                'subjects': work.metadata.subjects,
                'languages': work.metadata.languages
            }
            report['downloaded_works'].append(work_data)
            
            # Update statistics
            work_type = work_data['work_type']
            report['statistics']['work_types'][work_type] = report['statistics']['work_types'].get(work_type, 0) + 1
            
            report['statistics']['languages'].update(work.metadata.languages)
            report['statistics']['subjects'].update(work.metadata.subjects)
        
        # Convert sets to lists for JSON serialization
        report['statistics']['languages'] = list(report['statistics']['languages'])
        report['statistics']['subjects'] = list(report['statistics']['subjects'])
        
        # Save report
        report_path = self.data_dir / f"enhanced_download_report_{self.session_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Enhanced comprehensive report saved: {report_path}")
        
        return report
    
    async def _cleanup_sources(self):
        """Cleanup all sources."""
        try:
            await self.enhanced_gutendex.__aexit__(None, None, None)
            await self.direct_pg.__aexit__(None, None, None)
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
