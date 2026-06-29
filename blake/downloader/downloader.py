"""
Main downloader class that coordinates all data sources.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .sources import BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource
from ..models import BlakeWork, SourceType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class BlakeDownloader:
    """
    Compatibility downloader facade for configured source providers.

    The target-ledger corpus contract lives in ``BlakeCorpus.run`` and the
    generated manifest/audit artifacts. This facade remains useful for direct
    provider debugging and older callers.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize Blake downloader.
        
        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = data_dir
        
        # Initialize sources
        self.sources = {
            SourceType.BLAKE_ARCHIVE: BlakeArchiveSource(data_dir),
            SourceType.PROJECT_GUTENBERG: ProjectGutenbergSource(data_dir),
            SourceType.INTERNET_ARCHIVE: InternetArchiveSource(data_dir),
        }
        from ..corpus.sources import build_default_source_registry

        self.source_registry = build_default_source_registry(data_dir, sources=self.sources)
        
        logger.info(f"Initialized BlakeDownloader with data directory: {data_dir}")
    
    async def download_all(self, force: bool = False, 
                          sources: Optional[List[SourceType]] = None) -> List[BlakeWork]:
        """
        Fetch currently discoverable records from configured source providers.
        
        Args:
            force: Force re-download even if works exist
            sources: List of sources to use. If None, uses configured sources
            
        Returns:
            List of downloaded BlakeWork objects
        """
        logger.info("Starting provider-record fetch for configured Blake sources")
        
        all_works = []

        source_types = list(self.sources.keys()) if sources is None else sources
        for source_type in source_types:
            provider = self.source_registry.get(source_type)
            if provider is None:
                logger.warning(f"Unknown source type: {source_type}")
                continue
            
            try:
                logger.info(f"Downloading from {source_type}")
                records = await provider.discover()
                logger.info(f"Found {len(records)} works in {source_type}")

                for record in records:
                    try:
                        work_id = record.source_id
                        
                        if not force and await self._work_exists_and_complete(work_id):
                            logger.info(f"Skipping existing work: {record.title}")
                            continue
                        
                        work = await provider.fetch(record, force=force)
                        if work:
                            all_works.append(work)
                            logger.info(f"Downloaded: {work.metadata.title}")
                    except Exception as e:
                        logger.error(f"Error downloading work {record.source_id}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error downloading from {source_type}: {e}")
                continue
        
        logger.info(f"Download completed. Total works: {len(all_works)}")
        return all_works
    
    async def download_work(self, work_id: str, force: bool = False) -> Optional[BlakeWork]:
        """
        Download a specific work by ID.
        
        Args:
            work_id: Unique identifier for the work
            force: Force re-download even if work exists
            
        Returns:
            BlakeWork object or None if not found
        """
        logger.info(f"Downloading work: {work_id}")
        
        for source_type, provider in ((provider.source_type, provider) for provider in self.source_registry.providers()):
            try:
                records = await provider.discover()
                record = next((item for item in records if item.source_id == work_id), None)
                if record:
                    work = await provider.fetch(record, force=force)
                    if work:
                        logger.info(f"Downloaded work {work_id} from {source_type}")
                        return work
                
            except Exception as e:
                logger.error(f"Error searching for work {work_id} in {source_type}: {e}")
                continue
        
        logger.warning(f"Work {work_id} not found in any source")
        return None
    
    async def download_from_source(self, source_type: SourceType, 
                                 force: bool = False) -> List[BlakeWork]:
        """
        Fetch currently discoverable records from a specific source.
        
        Args:
            source_type: Source to download from
            force: Force re-download even if works exist
            
        Returns:
            List of downloaded BlakeWork objects
        """
        provider = self.source_registry.get(source_type)
        if provider is None:
            raise DownloadError(f"Unknown source type: {source_type}")
        
        logger.info(f"Downloading from {source_type}")
        
        try:
            records = await provider.discover()
            logger.info(f"Found {len(records)} works in {source_type}")

            works = []
            for record in records:
                try:
                    if not force and await self._work_exists_and_complete(record.source_id):
                        continue
                    work = await provider.fetch(record, force=force)
                    if work:
                        works.append(work)
                        logger.info(f"Downloaded: {work.metadata.title}")
                except Exception as e:
                    logger.error(f"Error downloading work {record.source_id}: {e}")
                    continue
            
            logger.info(f"Downloaded {len(works)} works from {source_type}")
            return works
            
        except Exception as e:
            logger.error(f"Error downloading from {source_type}: {e}")
            raise DownloadError(f"Failed to download from {source_type}: {e}")
    
    async def get_available_works(self, source_type: Optional[SourceType] = None) -> List[Dict[str, Any]]:
        """
        Get list of available works without downloading.
        
        Args:
            source_type: Specific source to query. If None, queries all sources
            
        Returns:
            List of work information dictionaries
        """
        if source_type:
            sources_to_query = [source_type]
        else:
            sources_to_query = list(self.sources.keys())
        
        all_works = []
        
        for source_type in sources_to_query:
            if source_type not in self.sources:
                continue
            
            provider = self.source_registry.get(source_type)
            if provider is None:
                continue

            try:
                records = await provider.discover()
                all_works.extend(record.metadata for record in records)
            except Exception as e:
                logger.error(f"Error getting work list from {source_type}: {e}")
                continue
        
        return all_works
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Get information about available sources.
        
        Returns:
            Dictionary of source information
        """
        return {
            source_type.value: {
                "name": source_type.value.replace("_", " ").title(),
                "description": self._get_source_description(source_type),
                "base_url": self._get_source_url(source_type),
            }
            for source_type in self.sources.keys()
        }
    
    def _get_source_description(self, source_type: SourceType) -> str:
        """Get description for a source type."""
        descriptions = {
            SourceType.BLAKE_ARCHIVE: "Target-ledger and Archive inventory records with images where permitted",
            SourceType.PROJECT_GUTENBERG: "Plain text versions of Blake's works",
            SourceType.INTERNET_ARCHIVE: "Historical scans and facsimiles",
        }
        return descriptions.get(source_type, "Unknown source")
    
    def _get_source_url(self, source_type: SourceType) -> str:
        """Get base URL for a source type."""
        urls = {
            SourceType.BLAKE_ARCHIVE: "https://blakearchive.org",
            SourceType.PROJECT_GUTENBERG: "https://www.gutenberg.org",
            SourceType.INTERNET_ARCHIVE: "https://archive.org",
        }
        return urls.get(source_type, "")
    
    async def _work_exists_and_complete(self, work_id: str) -> bool:
        """
        Check if a work already exists and is complete.
        
        Args:
            work_id: ID of the work to check
            
        Returns:
            True if work exists and is complete
        """
        try:
            # Check if metadata file exists
            metadata_file = self.data_dir / "metadata" / f"{work_id}.json"
            if not metadata_file.exists():
                return False
            
            # Load and check work completeness
            import json
            with open(metadata_file, 'r', encoding='utf-8') as f:
                work_data = json.load(f)
            
            # Check if work has required components
            has_metadata = 'metadata' in work_data
            has_text = work_data.get('text_content') is not None
            has_images = len(work_data.get('images', [])) > 0
            
            # Work is complete if it has metadata and at least text or images
            return has_metadata and (has_text or has_images)
            
        except Exception as e:
            logger.debug(f"Error checking work existence for {work_id}: {e}")
            return False
    
