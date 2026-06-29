"""
Comprehensive Blake downloader for acquiring works from all sources.
Integrates source discovery, incremental updates, and data organization.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .scraper import WebScraper, ImageDownloader
from .sources import BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource
from .source_discovery_engine import SourceDiscoveryEngine, SourceConfig
from .museum_adapters import SourceAdapterFactory
from .update_scheduler import IncrementalUpdater, UpdateFrequency
from .collection_organizer import DataOrganizer, DataStructure, OrganizationLevel
from .manager import DownloadManager
from ..models import BlakeWork, SourceType, WorkType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class UniversalBlakeDownloader:
    """
    Universal downloader for Blake works from all available sources.
    
    This is the main entry point for comprehensive Blake work acquisition,
    providing a unified interface for discovering, downloading, organizing,
    and managing target-ledger Blake corpus candidates from museums, archives,
    and academic sources.
    
    Features:
    - Multi-source discovery and cataloging (15+ sources)
    - Incremental updates with change detection
    - Hybrid data organization (source-specific + unified)
    - Quality assurance and verification
    - Performance optimization (50+ concurrent downloads)
    - Real-time monitoring and alerting
    - Error recovery and retry mechanisms
    """
    
    def __init__(self, data_dir: Path, max_concurrent: int = 50):
        """
        Initialize comprehensive Blake downloader.
        
        Args:
            data_dir: Directory to store downloaded data
            max_concurrent: Maximum concurrent downloads
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        
        # Initialize core components
        self.scraper = WebScraper(data_dir)
        self.image_downloader = ImageDownloader(data_dir)
        
        # Initialize comprehensive systems
        self.discovery_engine = SourceDiscoveryEngine(data_dir)
        self.incremental_updater = IncrementalUpdater(data_dir, self.discovery_engine)
        
        # Initialize data organization
        data_structure = DataStructure(
            level=OrganizationLevel.HYBRID,
            create_thumbnails=True,
            create_indexes=True,
            backup_enabled=True
        )
        self.data_organizer = DataOrganizer(data_dir, data_structure)
        
        # Initialize download manager
        self.download_manager = DownloadManager(data_dir, max_concurrent)
        
        # Legacy sources for backward compatibility
        self.legacy_sources = {
            SourceType.BLAKE_ARCHIVE: BlakeArchiveSource(data_dir),
            SourceType.PROJECT_GUTENBERG: ProjectGutenbergSource(data_dir),
            SourceType.INTERNET_ARCHIVE: InternetArchiveSource(data_dir),
        }
        
        logger.info(f"Initialized UniversalBlakeDownloader with {max_concurrent} concurrent downloads")
    
    async def discover_and_download_all(self, force: bool = False) -> Dict[str, Any]:
        """
        Discover and fetch currently available provider records.
        
        Args:
            force: Force re-download even if works exist
            
        Returns:
            Dictionary with provider-discovery download results
        """
        logger.info("Starting provider-discovery acquisition")
        
        results = {
            'session_id': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'start_time': datetime.now(),
            'sources_discovered': 0,
            'works_discovered': 0,
            'works_downloaded': 0,
            'works_organized': 0,
            'errors': [],
            'source_reports': {}
        }
        
        try:
            # Step 1: Discover all sources
            logger.info("Step 1: Discovering sources")
            valid_sources = await self.discovery_engine.discover_sources()
            results['sources_discovered'] = len(valid_sources)
            
            # Step 2: Catalog works from all sources
            logger.info("Step 2: Cataloging works from configured sources")
            all_works_metadata = await self.discovery_engine.get_comprehensive_work_list()
            results['works_discovered'] = len(all_works_metadata)
            
            # Step 3: Download works from each source
            logger.info("Step 3: Fetching provider-discovered records")
            downloaded_works = []
            
            for source_config in valid_sources:
                try:
                    source_report = await self._download_from_source_comprehensive(
                        source_config, force
                    )
                    results['source_reports'][source_config.source_type.value] = source_report
                    results['works_downloaded'] += source_report.get('works_downloaded', 0)
                    downloaded_works.extend(source_report.get('works', []))
                    
                except Exception as e:
                    error_msg = f"Error downloading from {source_config.name}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Step 4: Organize all downloaded works
            logger.info("Step 4: Organizing downloaded works")
            for work in downloaded_works:
                try:
                    # Find source metadata
                    source_metadata = None
                    for work_meta in all_works_metadata:
                        if work_meta.id == work.id:
                            source_metadata = work_meta
                            break
                    
                    if source_metadata:
                        organization_results = await self.data_organizer.organize_work(
                            work, source_metadata
                        )
                        results['works_organized'] += 1
                        
                except Exception as e:
                    error_msg = f"Error organizing work {work.id}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Step 5: Update indexes and create reports
            logger.info("Step 5: Finalizing organization")
            await self.data_organizer._save_indexes()
            
            results['end_time'] = datetime.now()
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
            
            logger.info(f"Provider-discovery acquisition completed: {results['works_downloaded']} works downloaded, "
                       f"{results['works_organized']} works organized")
            
            return results
            
        except Exception as e:
            error_msg = f"Error in provider-discovery acquisition: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['end_time'] = datetime.now()
            return results
    
    async def _download_from_source_comprehensive(self, source_config: SourceConfig, 
                                                force: bool) -> Dict[str, Any]:
        source_report = {
            'source': source_config.name,
            'source_type': source_config.source_type.value,
            'works_found': 0,
            'works_downloaded': 0,
            'works_skipped': 0,
            'works_failed': 0,
            'works': [],
            'errors': []
        }
        
        try:
            # Create source adapter
            adapter = SourceAdapterFactory.create_adapter(
                source_config.source_type, self.data_dir, source_config
            )
            
            # Discover works
            works_metadata = await adapter.discover_works()
            source_report['works_found'] = len(works_metadata)
            
            # Download works with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def download_single_work(work_metadata):
                async with semaphore:
                    try:
                        # Check if work already exists
                        if not force and await self._work_exists_and_complete(work_metadata.id):
                            source_report['works_skipped'] += 1
                            return None
                        
                        # Download work
                        work = await adapter.download_work(work_metadata)
                        if work:
                            source_report['works_downloaded'] += 1
                            return work
                        else:
                            source_report['works_failed'] += 1
                            return None
                            
                    except Exception as e:
                        error_msg = f"Error downloading work {work_metadata.id}: {e}"
                        logger.warning(error_msg)
                        source_report['errors'].append(error_msg)
                        source_report['works_failed'] += 1
                        return None
            
            tasks = [download_single_work(work_meta) for work_meta in works_metadata]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful downloads
            for result in results:
                if isinstance(result, BlakeWork):
                    source_report['works'].append(result)
            
            logger.info(f"Downloaded {source_report['works_downloaded']} works from {source_config.name}")
            
        except Exception as e:
            error_msg = f"Error downloading from {source_config.name}: {e}"
            logger.error(error_msg)
            source_report['errors'].append(error_msg)
        
        return source_report
    
    async def run_incremental_updates(self) -> Dict[str, Any]:
        """
        Run incremental updates for all sources.
        
        Returns:
            Dictionary with update results
        """
        logger.info("Running incremental updates")
        
        try:
            # Run comprehensive update check
            update_report = await self.incremental_updater.check_all_sources()
            
            # Apply discovered updates
            if update_report.works_discovered > 0:
                # Get updates from discovery engine
                updates = []
                for source_type in SourceType:
                    source_config = self.discovery_engine.sources_config.get(source_type)
                    if source_config:
                        source_updates = await self.discovery_engine.detect_updates(source_config)
                        updates.extend(source_updates)
                
                if updates:
                    apply_results = await self.incremental_updater.apply_updates(updates)
                    update_report.works_updated = apply_results.get('applied', 0)
            
            logger.info(f"Incremental updates completed: {update_report.works_discovered} works discovered, "
                       f"{update_report.works_updated} works updated")
            
            return update_report
            
        except Exception as e:
            logger.error(f"Error running incremental updates: {e}")
            return {
                'session_id': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'sources_checked': 0,
                'sources_successful': 0,
                'works_discovered': 0,
                'works_updated': 0,
                'errors': [str(e)]
            }
    
    async def download_work(self, work_id: str, force: bool = False) -> Optional[BlakeWork]:
        """
        Download a specific work by ID from any source.
        
        Args:
            work_id: Unique identifier for the work
            force: Force re-download even if work exists
            
        Returns:
            BlakeWork object or None if not found
        """
        logger.info(f"Downloading specific work: {work_id}")
        
        # Try to find work in known works
        if work_id in self.discovery_engine.known_works:
            work_metadata = self.discovery_engine.known_works[work_id]
            source_config = self.discovery_engine.sources_config.get(work_metadata.source)
            
            if source_config:
                adapter = SourceAdapterFactory.create_adapter(
                    work_metadata.source, self.data_dir, source_config
                )
                return await adapter.download_work(work_metadata)
        
        # Fallback to legacy sources
        for source_type, source in self.legacy_sources.items():
            try:
                work = await source.download_work({'id': work_id})
                if work:
                    return work
            except Exception as e:
                logger.debug(f"Work {work_id} not found in {source_type}: {e}")
        
        logger.warning(f"Work {work_id} not found in any source")
        return None
    
    async def search_works(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[BlakeWork]:
        """
        Search works using the data organizer's search capabilities.
        
        Args:
            query: Search query
            filters: Additional filters
            
        Returns:
            List of matching BlakeWork objects
        """
        logger.info(f"Searching works with query: {query}")
        
        try:
            # Get matching work IDs
            work_ids = await self.data_organizer.search_works(query, filters)
            
            # Load works
            works = []
            for work_id in work_ids:
                work = await self._load_work_from_organization(work_id)
                if work:
                    works.append(work)
            
            logger.info(f"Found {len(works)} works matching query")
            return works
            
        except Exception as e:
            logger.error(f"Error searching works: {e}")
            return []
    
    async def _load_work_from_organization(self, work_id: str) -> Optional[BlakeWork]:
        """Load work from organized data structure."""
        try:
            work_path = self.data_organizer.work_index.get(work_id)
            if not work_path or not Path(work_path).exists():
                return None
            
            with open(work_path, 'r', encoding='utf-8') as f:
                work_data = json.load(f)
            
            # Convert back to BlakeWork object
            from ..models import BlakeWork, BlakeMetadata, BlakeImage
            import json
            
            # This is a simplified conversion - in practice, you'd need proper deserialization
            return BlakeWork(**work_data)
            
        except Exception as e:
            logger.warning(f"Error loading work {work_id}: {e}")
            return None
    
    async def _work_exists_and_complete(self, work_id: str) -> bool:
        """Check if work exists and is complete in organized structure."""
        work_path = self.data_organizer.work_index.get(work_id)
        if not work_path or not Path(work_path).exists():
            return False
        
        # Check for required files
        work_dir = Path(work_path).parent
        required_files = ["work.json"]
        for file_name in required_files:
            if not (work_dir / file_name).exists():
                return False
        
        return True
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the collection."""
        stats = {
            'discovery': self.discovery_engine.get_source_statistics(),
            'organization': self.data_organizer.get_organization_statistics(),
            'updates': self.incremental_updater.get_update_statistics(),
            'downloads': self.download_manager.get_download_statistics()
        }
        
        return stats
    
    def configure_update_schedule(self, source_type: SourceType, frequency: UpdateFrequency, 
                                enabled: bool = True, max_works: int = 100) -> None:
        """Configure update schedule for a source."""
        self.incremental_updater.configure_schedule(source_type, frequency, enabled, max_works)
    
    async def cleanup_and_optimize(self) -> Dict[str, Any]:
        """Clean up and optimize the data collection."""
        logger.info("Starting cleanup and optimization")
        
        results = {
            'orphaned_files_removed': 0,
            'indexes_rebuilt': 0,
            'errors': []
        }
        
        try:
            # Clean up orphaned files
            orphaned_count = await self.data_organizer.cleanup_orphaned_files()
            results['orphaned_files_removed'] = orphaned_count
            
            # Rebuild indexes
            await self.data_organizer._save_indexes()
            results['indexes_rebuilt'] = 1
            
            # Clean up failed downloads
            failed_count = await self.download_manager.cleanup_failed_downloads()
            results['failed_downloads_cleaned'] = failed_count
            
            logger.info(f"Cleanup completed: {orphaned_count} orphaned files removed")
            
        except Exception as e:
            error_msg = f"Error during cleanup: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results


# Legacy compatibility
class BlakeDownloader(UniversalBlakeDownloader):
    """Legacy BlakeDownloader for backward compatibility."""
    
    def __init__(self, data_dir: Path):
        super().__init__(data_dir, max_concurrent=3)
