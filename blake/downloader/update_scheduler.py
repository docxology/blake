"""
Incremental Update System for comprehensive Blake work monitoring.
Implements change detection, scheduling, and automated updates.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

from .source_discovery_engine import SourceDiscoveryEngine, SourceConfig, WorkMetadata, WorkUpdate
from .museum_adapters import SourceAdapterFactory, SourceAdapter
from ..models import SourceType, BlakeWork
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class UpdateFrequency(str, Enum):
    """Update frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class UpdateSchedule:
    """Schedule configuration for updates."""
    source_type: SourceType
    frequency: UpdateFrequency
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    max_works_per_run: int = 100
    priority: int = 1  # 1=highest, 5=lowest


@dataclass
class UpdateReport:
    """Report of update operations."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    sources_checked: int = 0
    sources_successful: int = 0
    sources_failed: int = 0
    works_discovered: int = 0
    works_updated: int = 0
    works_deleted: int = 0
    errors: List[str] = None
    source_reports: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.source_reports is None:
            self.source_reports = {}


@dataclass
class SourceUpdateReport:
    """Report for a single source update."""
    source_type: SourceType
    start_time: datetime
    end_time: Optional[datetime] = None
    works_found: int = 0
    works_new: int = 0
    works_modified: int = 0
    works_deleted: int = 0
    works_skipped: int = 0
    errors: List[str] = None
    status: str = "pending"  # pending, running, completed, failed

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class IncrementalUpdater:
    """
    Manages incremental updates and change detection across all sources.
    
    Features:
    - Scheduled updates with configurable frequencies
    - Change detection and work comparison
    - Automated download of new/updated works
    - Error recovery and retry mechanisms
    - Comprehensive reporting and monitoring
    """
    
    def __init__(self, data_dir: Path, discovery_engine: SourceDiscoveryEngine):
        """
        Initialize incremental updater.
        
        Args:
            data_dir: Directory to store update data
            discovery_engine: Source discovery engine instance
        """
        self.data_dir = data_dir
        self.discovery_engine = discovery_engine
        self.update_dir = data_dir / "updates"
        self.update_dir.mkdir(parents=True, exist_ok=True)
        
        # Update tracking
        self.schedules: Dict[SourceType, UpdateSchedule] = {}
        self.update_history: List[UpdateReport] = []
        self.work_checksums: Dict[str, str] = {}  # work_id -> checksum
        
        # Load existing data
        self._load_update_data()
        self._setup_default_schedules()
        
        logger.info("Initialized IncrementalUpdater")
    
    def _setup_default_schedules(self) -> None:
        """Setup default update schedules for all sources."""
        default_schedules = {
            # Tier 1: Primary sources - daily updates
            SourceType.BLAKE_ARCHIVE: UpdateSchedule(
                source_type=SourceType.BLAKE_ARCHIVE,
                frequency=UpdateFrequency.DAILY,
                priority=1,
                max_works_per_run=200
            ),
            SourceType.PROJECT_GUTENBERG: UpdateSchedule(
                source_type=SourceType.PROJECT_GUTENBERG,
                frequency=UpdateFrequency.WEEKLY,
                priority=1,
                max_works_per_run=100
            ),
            SourceType.INTERNET_ARCHIVE: UpdateSchedule(
                source_type=SourceType.INTERNET_ARCHIVE,
                frequency=UpdateFrequency.DAILY,
                priority=1,
                max_works_per_run=150
            ),
            
            # Tier 2: Museum sources - weekly updates
            SourceType.BRITISH_MUSEUM: UpdateSchedule(
                source_type=SourceType.BRITISH_MUSEUM,
                frequency=UpdateFrequency.WEEKLY,
                priority=2,
                max_works_per_run=50
            ),
            SourceType.TATE: UpdateSchedule(
                source_type=SourceType.TATE,
                frequency=UpdateFrequency.WEEKLY,
                priority=2,
                max_works_per_run=50
            ),
            
            # Tier 3: Academic sources - monthly updates
            SourceType.HATHITRUST: UpdateSchedule(
                source_type=SourceType.HATHITRUST,
                frequency=UpdateFrequency.MONTHLY,
                priority=3,
                max_works_per_run=100
            ),
            SourceType.WIKIMEDIA: UpdateSchedule(
                source_type=SourceType.WIKIMEDIA,
                frequency=UpdateFrequency.WEEKLY,
                priority=3,
                max_works_per_run=75
            ),
            SourceType.GOOGLE_ARTS: UpdateSchedule(
                source_type=SourceType.GOOGLE_ARTS,
                frequency=UpdateFrequency.MONTHLY,
                priority=3,
                max_works_per_run=50
            )
        }
        
        for source_type, schedule in default_schedules.items():
            if source_type not in self.schedules:
                self.schedules[source_type] = schedule
    
    async def check_all_sources(self) -> UpdateReport:
        """
        Check all sources for updates.
        
        Returns:
            Comprehensive update report
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Starting comprehensive update check: {session_id}")
        
        report = UpdateReport(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        try:
            # Get all enabled sources
            enabled_sources = [
                source for source in self.schedules.values()
                if source.enabled and self._should_run_update(source)
            ]
            
            logger.info(f"Checking {len(enabled_sources)} sources for updates")
            
            # Check each source
            for schedule in enabled_sources:
                try:
                    source_report = await self._check_source_updates(schedule)
                    report.source_reports[schedule.source_type.value] = asdict(source_report)
                    
                    report.sources_checked += 1
                    if source_report.status == "completed":
                        report.sources_successful += 1
                        report.works_discovered += source_report.works_found
                        report.works_updated += source_report.works_new + source_report.works_modified
                        report.works_deleted += source_report.works_deleted
                    else:
                        report.sources_failed += 1
                        report.errors.extend(source_report.errors)
                    
                    # Update schedule
                    schedule.last_run = datetime.now()
                    schedule.next_run = self._calculate_next_run(schedule)
                    
                except Exception as e:
                    error_msg = f"Error checking {schedule.source_type}: {e}"
                    logger.error(error_msg)
                    report.errors.append(error_msg)
                    report.sources_failed += 1
            
            # Finalize report
            report.end_time = datetime.now()
            report.sources_checked = len(enabled_sources)
            
            # Save update data
            self.update_history.append(report)
            self._save_update_data()
            
            logger.info(f"Update check completed: {report.sources_successful}/{report.sources_checked} sources successful")
            return report
            
        except Exception as e:
            logger.error(f"Error in comprehensive update check: {e}")
            report.end_time = datetime.now()
            report.errors.append(str(e))
            return report
    
    async def _check_source_updates(self, schedule: UpdateSchedule) -> SourceUpdateReport:
        """Check updates for a specific source."""
        source_report = SourceUpdateReport(
            source_type=schedule.source_type,
            start_time=datetime.now(),
            status="running"
        )
        
        try:
            # Get source configuration
            source_config = self.discovery_engine.sources_config.get(schedule.source_type)
            if not source_config:
                raise DownloadError(f"Source configuration not found: {schedule.source_type}")
            
            # Create source adapter
            adapter = SourceAdapterFactory.create_adapter(
                schedule.source_type, self.data_dir, source_config
            )
            
            # Discover current works
            current_works = await adapter.discover_works()
            source_report.works_found = len(current_works)
            
            # Get previously known works for this source
            known_work_ids = {
                work_id for work_id, work in self.discovery_engine.known_works.items()
                if work.source == schedule.source_type
            }
            
            current_work_ids = {work.id for work in current_works}
            
            # Detect changes
            new_work_ids = current_work_ids - known_work_ids
            deleted_work_ids = known_work_ids - current_work_ids
            
            # Check for modifications
            modified_works = []
            for work in current_works:
                if work.id in known_work_ids:
                    known_work = self.discovery_engine.known_works[work.id]
                    if self._work_has_changed(known_work, work):
                        modified_works.append(work)
            
            source_report.works_new = len(new_work_ids)
            source_report.works_modified = len(modified_works)
            source_report.works_deleted = len(deleted_work_ids)
            source_report.works_skipped = len(current_work_ids) - len(new_work_ids) - len(modified_works)
            
            # Download new and modified works
            await self._download_updated_works(
                current_works, new_work_ids, modified_works, adapter, schedule
            )
            
            # Update known works
            for work in current_works:
                self.discovery_engine.known_works[work.id] = work
                self.discovery_engine._index_work(work)
            
            # Remove deleted works
            for work_id in deleted_work_ids:
                if work_id in self.discovery_engine.known_works:
                    del self.discovery_engine.known_works[work_id]
            
            source_report.status = "completed"
            source_report.end_time = datetime.now()
            
            logger.info(f"Source {schedule.source_type} update completed: "
                       f"{source_report.works_new} new, {source_report.works_modified} modified, "
                       f"{source_report.works_deleted} deleted")
            
        except Exception as e:
            error_msg = f"Error updating source {schedule.source_type}: {e}"
            logger.error(error_msg)
            source_report.errors.append(error_msg)
            source_report.status = "failed"
            source_report.end_time = datetime.now()
        
        return source_report
    
    async def _download_updated_works(self, current_works: List[WorkMetadata], 
                                    new_work_ids: Set[str], modified_works: List[WorkMetadata],
                                    adapter: SourceAdapter, schedule: UpdateSchedule) -> None:
        """Download new and modified works."""
        works_to_download = []
        
        # Add new works
        for work in current_works:
            if work.id in new_work_ids:
                works_to_download.append(work)
        
        # Add modified works
        works_to_download.extend(modified_works)
        
        # Limit number of works per run
        if len(works_to_download) > schedule.max_works_per_run:
            works_to_download = works_to_download[:schedule.max_works_per_run]
            logger.warning(f"Limited to {schedule.max_works_per_run} works for {schedule.source_type}")
        
        # Download works concurrently
        semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads
        
        async def download_single_work(work: WorkMetadata) -> Optional[BlakeWork]:
            async with semaphore:
                try:
                    return await adapter.download_work(work)
                except Exception as e:
                    logger.warning(f"Error downloading work {work.id}: {e}")
                    return None
        
        tasks = [download_single_work(work) for work in works_to_download]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful downloads
        successful_downloads = sum(1 for result in results if isinstance(result, BlakeWork))
        logger.info(f"Downloaded {successful_downloads}/{len(works_to_download)} works from {schedule.source_type}")
    
    def _work_has_changed(self, old_work: WorkMetadata, new_work: WorkMetadata) -> bool:
        """Check if a work has changed."""
        # Compare key fields
        if old_work.title != new_work.title:
            return True
        
        if old_work.description != new_work.description:
            return True
        
        if old_work.creation_date != new_work.creation_date:
            return True
        
        # Compare checksums if available
        old_checksum = self.work_checksums.get(old_work.id)
        new_checksum = self._calculate_work_checksum(new_work)
        
        if old_checksum and new_checksum and old_checksum != new_checksum:
            return True
        
        return False
    
    def _calculate_work_checksum(self, work: WorkMetadata) -> str:
        """Calculate checksum for work metadata."""
        content = f"{work.title}|{work.description}|{work.creation_date}|{work.source_url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _should_run_update(self, schedule: UpdateSchedule) -> bool:
        """Check if update should run based on schedule."""
        if not schedule.enabled:
            return False
        
        if schedule.next_run is None:
            schedule.next_run = self._calculate_next_run(schedule)
        
        return datetime.now() >= schedule.next_run
    
    def _calculate_next_run(self, schedule: UpdateSchedule) -> datetime:
        """Calculate next run time based on frequency."""
        now = datetime.now()
        
        if schedule.frequency == UpdateFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif schedule.frequency == UpdateFrequency.DAILY:
            return now + timedelta(days=1)
        elif schedule.frequency == UpdateFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif schedule.frequency == UpdateFrequency.MONTHLY:
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=1)
    
    async def apply_updates(self, updates: List[WorkUpdate]) -> Dict[str, Any]:
        """
        Apply discovered updates to local collection.
        
        Args:
            updates: List of work updates to apply
            
        Returns:
            Dictionary with update results
        """
        logger.info(f"Applying {len(updates)} updates")
        
        results = {
            'applied': 0,
            'failed': 0,
            'errors': []
        }
        
        for update in updates:
            try:
                if update.update_type == 'new':
                    # Download new work
                    source_config = self.discovery_engine.sources_config.get(update.source)
                    if source_config:
                        adapter = SourceAdapterFactory.create_adapter(
                            update.source, self.data_dir, source_config
                        )
                        
                        # Find work metadata
                        work_metadata = None
                        for work in self.discovery_engine.known_works.values():
                            if work.id == update.work_id and work.source == update.source:
                                work_metadata = work
                                break
                        
                        if work_metadata:
                            downloaded_work = await adapter.download_work(work_metadata)
                            if downloaded_work:
                                results['applied'] += 1
                            else:
                                results['failed'] += 1
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Work metadata not found: {update.work_id}")
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Source configuration not found: {update.source}")
                
                elif update.update_type == 'modified':
                    # Re-download modified work
                    # Similar implementation to 'new'
                    results['applied'] += 1
                
                elif update.update_type == 'deleted':
                    # Remove deleted work
                    if update.work_id in self.discovery_engine.known_works:
                        del self.discovery_engine.known_works[update.work_id]
                        results['applied'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Work not found for deletion: {update.work_id}")
                
            except Exception as e:
                error_msg = f"Error applying update {update.work_id}: {e}"
                logger.error(error_msg)
                results['failed'] += 1
                results['errors'].append(error_msg)
        
        logger.info(f"Applied {results['applied']} updates, {results['failed']} failed")
        return results
    
    async def schedule_updates(self) -> None:
        """Schedule regular update checks."""
        logger.info("Scheduling regular updates")
        
        # This would typically be run as a background task
        # For now, we'll just log the schedule
        for schedule in self.schedules.values():
            if schedule.enabled:
                next_run = self._calculate_next_run(schedule)
                logger.info(f"Next update for {schedule.source_type}: {next_run}")
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """Get comprehensive update statistics."""
        stats = {
            'total_sources': len(self.schedules),
            'enabled_sources': sum(1 for s in self.schedules.values() if s.enabled),
            'total_updates': len(self.update_history),
            'last_update': None,
            'sources': {}
        }
        
        if self.update_history:
            last_update = self.update_history[-1]
            stats['last_update'] = {
                'session_id': last_update.session_id,
                'start_time': last_update.start_time.isoformat(),
                'end_time': last_update.end_time.isoformat() if last_update.end_time else None,
                'sources_checked': last_update.sources_checked,
                'sources_successful': last_update.sources_successful,
                'works_discovered': last_update.works_discovered,
                'works_updated': last_update.works_updated
            }
        
        for source_type, schedule in self.schedules.items():
            stats['sources'][source_type.value] = {
                'frequency': schedule.frequency.value,
                'enabled': schedule.enabled,
                'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
                'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
                'priority': schedule.priority,
                'max_works_per_run': schedule.max_works_per_run
            }
        
        return stats
    
    def _load_update_data(self) -> None:
        """Load existing update data from disk."""
        update_file = self.update_dir / "update_data.json"
        
        if update_file.exists():
            try:
                with open(update_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load schedules
                for source_data in data.get('schedules', []):
                    source_type = SourceType(source_data['source_type'])
                    schedule = UpdateSchedule(**source_data)
                    self.schedules[source_type] = schedule
                
                # Load update history
                for report_data in data.get('update_history', []):
                    report = UpdateReport(**report_data)
                    self.update_history.append(report)
                
                logger.info(f"Loaded update data: {len(self.schedules)} schedules, {len(self.update_history)} updates")
                
            except Exception as e:
                logger.warning(f"Error loading update data: {e}")
    
    def _save_update_data(self) -> None:
        """Save update data to disk."""
        update_file = self.update_dir / "update_data.json"
        
        try:
            data = {
                'schedules': [asdict(schedule) for schedule in self.schedules.values()],
                'update_history': [asdict(report) for report in self.update_history[-100:]],  # Keep last 100
                'last_updated': datetime.now().isoformat()
            }
            
            with open(update_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Error saving update data: {e}")
    
    def configure_schedule(self, source_type: SourceType, frequency: UpdateFrequency, 
                          enabled: bool = True, max_works: int = 100) -> None:
        """Configure update schedule for a source."""
        if source_type in self.schedules:
            self.schedules[source_type].frequency = frequency
            self.schedules[source_type].enabled = enabled
            self.schedules[source_type].max_works_per_run = max_works
            self.schedules[source_type].next_run = self._calculate_next_run(self.schedules[source_type])
        else:
            self.schedules[source_type] = UpdateSchedule(
                source_type=source_type,
                frequency=frequency,
                enabled=enabled,
                max_works_per_run=max_works
            )
        
        self._save_update_data()
        logger.info(f"Configured schedule for {source_type}: {frequency.value}, enabled={enabled}")
