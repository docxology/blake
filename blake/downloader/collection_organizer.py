"""
Comprehensive Data Organization System for Blake works.
Implements unified collection structure with source-specific organization.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import json
import shutil
from dataclasses import dataclass, asdict
from enum import Enum

from .source_discovery_engine import WorkMetadata
from ..models import BlakeWork, BlakeMetadata, BlakeImage, SourceType, WorkType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class OrganizationLevel(str, Enum):
    """Organization levels for data structure."""
    SOURCE_SPECIFIC = "source_specific"
    UNIFIED = "unified"
    HYBRID = "hybrid"


@dataclass
class DataStructure:
    """Configuration for data organization structure."""
    level: OrganizationLevel
    create_thumbnails: bool = True
    create_indexes: bool = True
    compress_archives: bool = False
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataOrganizer:
    """
    Comprehensive data organization system for Blake works.
    
    Features:
    - Source-specific and unified organization
    - Automatic file organization and indexing
    - Thumbnail generation and optimization
    - Data integrity verification
    - Backup and archival management
    - Search index creation
    """
    
    def __init__(self, data_dir: Path, structure_config: DataStructure = None):
        """
        Initialize data organizer.
        
        Args:
            data_dir: Base directory for data storage
            structure_config: Data organization configuration
        """
        self.data_dir = data_dir
        self.config = structure_config or DataStructure(level=OrganizationLevel.HYBRID)
        
        # Create directory structure
        self._create_directory_structure()
        
        # Indexes and metadata
        self.work_index: Dict[str, str] = {}  # work_id -> file_path
        self.source_index: Dict[SourceType, Set[str]] = {}  # source -> work_ids
        self.type_index: Dict[WorkType, Set[str]] = {}  # work_type -> work_ids
        self.date_index: Dict[str, Set[str]] = {}  # year -> work_ids
        
        # Load existing indexes
        self._load_indexes()
        
        logger.info(f"Initialized DataOrganizer with {self.config.level.value} structure")
    
    def _create_directory_structure(self) -> None:
        """Create comprehensive directory structure."""
        directories = [
            # Source-specific data
            "sources",
            "sources/blake_archive",
            "sources/blake_archive/works",
            "sources/blake_archive/images",
            "sources/blake_archive/metadata",
            "sources/blake_archive/updates",
            
            "sources/project_gutenberg",
            "sources/project_gutenberg/works",
            "sources/project_gutenberg/metadata",
            
            "sources/internet_archive",
            "sources/internet_archive/works",
            "sources/internet_archive/images",
            "sources/internet_archive/metadata",
            
            "sources/british_museum",
            "sources/british_museum/works",
            "sources/british_museum/images",
            "sources/british_museum/metadata",
            
            "sources/tate",
            "sources/tate/works",
            "sources/tate/images",
            "sources/tate/metadata",
            
            "sources/hathitrust",
            "sources/hathitrust/works",
            "sources/hathitrust/metadata",
            
            "sources/wikimedia",
            "sources/wikimedia/works",
            "sources/wikimedia/images",
            "sources/wikimedia/metadata",
            
            "sources/google_arts",
            "sources/google_arts/works",
            "sources/google_arts/images",
            "sources/google_arts/metadata",
            
            # Unified collection
            "unified",
            "unified/works",
            "unified/works/by_id",
            "unified/works/by_type",
            "unified/works/by_date",
            "unified/works/by_theme",
            
            "unified/images",
            "unified/images/originals",
            "unified/images/thumbnails",
            "unified/images/processed",
            
            "unified/metadata",
            "unified/metadata/database",
            "unified/metadata/indexes",
            "unified/metadata/exports",
            
            # Processing pipeline
            "processing",
            "processing/downloads",
            "processing/analysis",
            "processing/verification",
            "processing/temp",
            
            # Monitoring and logs
            "monitoring",
            "monitoring/logs",
            "monitoring/metrics",
            "monitoring/reports",
            
            # Exports
            "exports",
            "exports/research",
            "exports/public",
            "exports/api",
            "exports/archives",
            
            # Backups
            "backups",
            "backups/daily",
            "backups/weekly",
            "backups/monthly"
        ]
        
        for directory in directories:
            dir_path = self.data_dir / directory
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created directory structure with {len(directories)} directories")
    
    async def organize_work(self, work: BlakeWork, source_metadata: WorkMetadata) -> Dict[str, Any]:
        """
        Organize a Blake work according to the configured structure.
        
        Args:
            work: BlakeWork object to organize
            source_metadata: Source metadata for the work
            
        Returns:
            Dictionary with organization results
        """
        logger.info(f"Organizing work: {work.id}")
        
        try:
            results = {
                'work_id': work.id,
                'source_paths': {},
                'unified_paths': {},
                'thumbnails_created': 0,
                'indexes_updated': 0,
                'errors': []
            }
            
            # Organize by source
            source_results = await self._organize_by_source(work, source_metadata)
            results['source_paths'] = source_results
            
            # Organize in unified collection
            if self.config.level in [OrganizationLevel.UNIFIED, OrganizationLevel.HYBRID]:
                unified_results = await self._organize_unified(work)
                results['unified_paths'] = unified_results
            
            # Create thumbnails
            if self.config.create_thumbnails:
                thumbnails_created = await self._create_thumbnails(work)
                results['thumbnails_created'] = thumbnails_created
            
            # Update indexes
            if self.config.create_indexes:
                await self._update_indexes(work)
                results['indexes_updated'] = 1
            
            # Verify organization
            verification_results = await self._verify_work_organization(work)
            results.update(verification_results)
            
            logger.info(f"Successfully organized work: {work.id}")
            return results
            
        except Exception as e:
            error_msg = f"Error organizing work {work.id}: {e}"
            logger.error(error_msg)
            return {
                'work_id': work.id,
                'errors': [error_msg]
            }
    
    async def _organize_by_source(self, work: BlakeWork, source_metadata: WorkMetadata) -> Dict[str, str]:
        """Organize work in source-specific structure."""
        source_paths = {}
        source_type = work.metadata.source
        
        # Create source directory path
        source_dir = self.data_dir / "sources" / source_type.value
        
        # Organize work files
        work_dir = source_dir / "works" / work.id
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # Save work metadata
        metadata_file = work_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(work.metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
        
        source_paths['metadata'] = str(metadata_file)
        
        # Save text content
        if work.text_content:
            text_file = work_dir / "text.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(work.text_content)
            source_paths['text'] = str(text_file)
        
        # Organize images
        if work.images:
            images_dir = source_dir / "images" / work.id
            images_dir.mkdir(parents=True, exist_ok=True)
            
            for i, image in enumerate(work.images):
                if image.file_path and image.file_path.exists():
                    # Copy image to organized location
                    dest_path = images_dir / f"image_{i+1:03d}{image.file_path.suffix}"
                    shutil.copy2(image.file_path, dest_path)
                    
                    # Update image path
                    image.file_path = dest_path
                    source_paths[f'image_{i+1}'] = str(dest_path)
                    
                    # Copy thumbnail if exists
                    if image.thumbnail_path and image.thumbnail_path.exists():
                        thumb_dest = images_dir / f"thumb_{i+1:03d}{image.thumbnail_path.suffix}"
                        shutil.copy2(image.thumbnail_path, thumb_dest)
                        image.thumbnail_path = thumb_dest
                        source_paths[f'thumb_{i+1}'] = str(thumb_dest)
        
        # Save work data
        work_file = work_dir / "work.json"
        with open(work_file, 'w', encoding='utf-8') as f:
            json.dump(work.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
        
        source_paths['work'] = str(work_file)
        
        return source_paths
    
    async def _organize_unified(self, work: BlakeWork) -> Dict[str, str]:
        """Organize work in unified collection structure."""
        unified_paths = {}
        unified_dir = self.data_dir / "unified"
        
        # Organize by ID
        by_id_dir = unified_dir / "works" / "by_id" / work.id
        by_id_dir.mkdir(parents=True, exist_ok=True)
        
        # Save work data
        work_file = by_id_dir / "work.json"
        with open(work_file, 'w', encoding='utf-8') as f:
            json.dump(work.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
        
        unified_paths['work'] = str(work_file)
        
        # Organize by type
        work_type_dir = unified_dir / "works" / "by_type" / work.metadata.work_type.value
        work_type_dir.mkdir(parents=True, exist_ok=True)
        
        type_link = work_type_dir / f"{work.id}.json"
        if not type_link.exists():
            type_link.symlink_to(work_file.relative_to(work_type_dir))
        
        unified_paths['by_type'] = str(type_link)
        
        # Organize by date
        if work.metadata.creation_date:
            year = work.metadata.creation_date.year
            date_dir = unified_dir / "works" / "by_date" / str(year)
            date_dir.mkdir(parents=True, exist_ok=True)
            
            date_link = date_dir / f"{work.id}.json"
            if not date_link.exists():
                date_link.symlink_to(work_file.relative_to(date_dir))
            
            unified_paths['by_date'] = str(date_link)
        
        # Organize images
        if work.images:
            images_dir = unified_dir / "images" / "originals" / work.id
            images_dir.mkdir(parents=True, exist_ok=True)
            
            for i, image in enumerate(work.images):
                if image.file_path and image.file_path.exists():
                    dest_path = images_dir / f"image_{i+1:03d}{image.file_path.suffix}"
                    shutil.copy2(image.file_path, dest_path)
                    unified_paths[f'unified_image_{i+1}'] = str(dest_path)
        
        return unified_paths
    
    async def _create_thumbnails(self, work: BlakeWork) -> int:
        """Create thumbnails for work images."""
        thumbnails_created = 0
        
        if not work.images:
            return thumbnails_created
        
        for image in work.images:
            if image.file_path and image.file_path.exists():
                try:
                    # Create thumbnail if not exists
                    if not image.thumbnail_path or not image.thumbnail_path.exists():
                        thumbnail_path = await self._generate_thumbnail(image.file_path, work.id)
                        if thumbnail_path:
                            image.thumbnail_path = thumbnail_path
                            thumbnails_created += 1
                except Exception as e:
                    logger.warning(f"Error creating thumbnail for {image.file_path}: {e}")
        
        return thumbnails_created
    
    async def _generate_thumbnail(self, image_path: Path, work_id: str) -> Optional[Path]:
        """Generate thumbnail for an image."""
        try:
            from PIL import Image
            
            # Create thumbnail directory
            thumb_dir = self.data_dir / "unified" / "images" / "thumbnails" / work_id
            thumb_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate thumbnail
            with Image.open(image_path) as img:
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_path = thumb_dir / f"thumb_{image_path.stem}.jpg"
                img.convert('RGB').save(thumb_path, 'JPEG', quality=85)
                
                return thumb_path
                
        except Exception as e:
            logger.warning(f"Error generating thumbnail: {e}")
            return None
    
    async def _update_indexes(self, work: BlakeWork) -> None:
        """Update search indexes for the work."""
        work_id = work.id
        
        # Update work index
        self.work_index[work_id] = str(self.data_dir / "unified" / "works" / "by_id" / work_id / "work.json")
        
        # Update source index
        source = work.metadata.source
        if source not in self.source_index:
            self.source_index[source] = set()
        self.source_index[source].add(work_id)
        
        # Update type index
        work_type = work.metadata.work_type
        if work_type not in self.type_index:
            self.type_index[work_type] = set()
        self.type_index[work_type].add(work_id)
        
        # Update date index
        if work.metadata.creation_date:
            year = str(work.metadata.creation_date.year)
            if year not in self.date_index:
                self.date_index[year] = set()
            self.date_index[year].add(work_id)
        
        # Save indexes
        await self._save_indexes()
    
    async def _verify_work_organization(self, work: BlakeWork) -> Dict[str, Any]:
        """Verify that work is properly organized."""
        verification = {
            'files_exist': 0,
            'files_missing': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            # Check work file
            work_file = self.data_dir / "unified" / "works" / "by_id" / work.id / "work.json"
            if work_file.exists():
                verification['files_exist'] += 1
                verification['total_size'] += work_file.stat().st_size
            else:
                verification['files_missing'] += 1
                verification['errors'].append(f"Work file missing: {work_file}")
            
            # Check images
            if work.images:
                for i, image in enumerate(work.images):
                    if image.file_path and image.file_path.exists():
                        verification['files_exist'] += 1
                        verification['total_size'] += image.file_path.stat().st_size
                    else:
                        verification['files_missing'] += 1
                        verification['errors'].append(f"Image {i+1} missing: {image.file_path}")
            
            # Check thumbnails
            if work.images:
                for i, image in enumerate(work.images):
                    if image.thumbnail_path and image.thumbnail_path.exists():
                        verification['files_exist'] += 1
                        verification['total_size'] += image.thumbnail_path.stat().st_size
                    else:
                        verification['files_missing'] += 1
                        verification['errors'].append(f"Thumbnail {i+1} missing: {image.thumbnail_path}")
            
        except Exception as e:
            verification['errors'].append(f"Verification error: {e}")
        
        return verification
    
    async def search_works(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Search works using indexes.
        
        Args:
            query: Search query
            filters: Additional filters
            
        Returns:
            List of matching work IDs
        """
        results = set()
        
        # Search by title in work index
        query_lower = query.lower()
        for work_id, work_path in self.work_index.items():
            try:
                with open(work_path, 'r', encoding='utf-8') as f:
                    work_data = json.load(f)
                
                title = work_data.get('metadata', {}).get('title', '').lower()
                if query_lower in title:
                    results.add(work_id)
                    
            except Exception as e:
                logger.warning(f"Error searching work {work_id}: {e}")
        
        # Apply filters
        if filters:
            filtered_results = set()
            
            for work_id in results:
                try:
                    work_path = self.work_index[work_id]
                    with open(work_path, 'r', encoding='utf-8') as f:
                        work_data = json.load(f)
                    
                    metadata = work_data.get('metadata', {})
                    
                    # Apply source filter
                    if 'source' in filters:
                        if metadata.get('source') != filters['source']:
                            continue
                    
                    # Apply type filter
                    if 'work_type' in filters:
                        if metadata.get('work_type') != filters['work_type']:
                            continue
                    
                    # Apply date filter
                    if 'date_range' in filters:
                        creation_date = metadata.get('creation_date')
                        if creation_date:
                            work_year = int(creation_date.split('-')[0])
                            date_range = filters['date_range']
                            if work_year < date_range[0] or work_year > date_range[1]:
                                continue
                    
                    filtered_results.add(work_id)
                    
                except Exception as e:
                    logger.warning(f"Error filtering work {work_id}: {e}")
            
            results = filtered_results
        
        return list(results)
    
    def get_organization_statistics(self) -> Dict[str, Any]:
        """Get comprehensive organization statistics."""
        stats = {
            'total_works': len(self.work_index),
            'sources': {},
            'work_types': {},
            'date_range': {},
            'total_size': 0,
            'structure_level': self.config.level.value
        }
        
        # Count by source
        for source, work_ids in self.source_index.items():
            stats['sources'][source.value] = len(work_ids)
        
        # Count by work type
        for work_type, work_ids in self.type_index.items():
            stats['work_types'][work_type.value] = len(work_ids)
        
        # Date range
        if self.date_index:
            years = [int(year) for year in self.date_index.keys()]
            stats['date_range'] = {
                'earliest': min(years),
                'latest': max(years)
            }
        
        # Calculate total size
        for work_path in self.work_index.values():
            try:
                if Path(work_path).exists():
                    stats['total_size'] += Path(work_path).stat().st_size
            except Exception:
                pass
        
        return stats
    
    def _load_indexes(self) -> None:
        """Load existing indexes from disk."""
        index_file = self.data_dir / "unified" / "metadata" / "indexes" / "search_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.work_index = data.get('work_index', {})
                
                # Convert sets back from lists
                self.source_index = {
                    SourceType(k): set(v) for k, v in data.get('source_index', {}).items()
                }
                self.type_index = {
                    WorkType(k): set(v) for k, v in data.get('type_index', {}).items()
                }
                self.date_index = {
                    k: set(v) for k, v in data.get('date_index', {}).items()
                }
                
                logger.info(f"Loaded indexes: {len(self.work_index)} works")
                
            except Exception as e:
                logger.warning(f"Error loading indexes: {e}")
    
    async def _save_indexes(self) -> None:
        """Save indexes to disk."""
        index_file = self.data_dir / "unified" / "metadata" / "indexes" / "search_index.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                'work_index': self.work_index,
                'source_index': {
                    k.value: list(v) for k, v in self.source_index.items()
                },
                'type_index': {
                    k.value: list(v) for k, v in self.type_index.items()
                },
                'date_index': {
                    k: list(v) for k, v in self.date_index.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving indexes: {e}")
    
    async def cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files and directories."""
        logger.info("Cleaning up orphaned files")
        
        cleaned_count = 0
        
        try:
            # Check for orphaned work directories
            works_dir = self.data_dir / "unified" / "works" / "by_id"
            if works_dir.exists():
                for work_dir in works_dir.iterdir():
                    if work_dir.is_dir():
                        work_id = work_dir.name
                        if work_id not in self.work_index:
                            logger.info(f"Removing orphaned work directory: {work_dir}")
                            shutil.rmtree(work_dir)
                            cleaned_count += 1
            
            # Check for orphaned image directories
            images_dir = self.data_dir / "unified" / "images" / "originals"
            if images_dir.exists():
                for image_dir in images_dir.iterdir():
                    if image_dir.is_dir():
                        work_id = image_dir.name
                        if work_id not in self.work_index:
                            logger.info(f"Removing orphaned image directory: {image_dir}")
                            shutil.rmtree(image_dir)
                            cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} orphaned directories")
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {e}")
        
        return cleaned_count
