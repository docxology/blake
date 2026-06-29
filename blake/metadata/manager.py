"""
Metadata manager that coordinates all metadata operations.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .database import MetadataDatabase
from .processor import MetadataProcessor
from .search import MetadataSearcher
from ..models import BlakeWork, BlakeMetadata, BlakeImage
from ..exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages all metadata operations for Blake works."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize metadata manager.
        
        Args:
            data_dir: Directory to store metadata
        """
        self.data_dir = data_dir
        self.metadata_dir = data_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.database = MetadataDatabase(self.metadata_dir / "metadata.db")
        self.processor = MetadataProcessor()
        self.searcher = MetadataSearcher()
        
        logger.info(f"Initialized MetadataManager with data directory: {data_dir}")
    
    async def process_work(self, work: BlakeWork) -> BlakeWork:
        """
        Process and save a work's metadata.
        
        Args:
            work: BlakeWork to process
            
        Returns:
            Processed BlakeWork
        """
        logger.info(f"Processing metadata for work: {work.id}")
        
        try:
            # Process metadata
            processed_work = await self.processor.process_work(work)
            
            # Save to database
            self.database.save_work(processed_work)
            
            logger.info(f"Successfully processed and saved work: {work.id}")
            return processed_work
            
        except Exception as e:
            logger.error(f"Error processing work {work.id}: {e}")
            raise MetadataError(f"Failed to process work {work.id}: {e}")
    
    async def save_work(self, work: BlakeWork) -> None:
        """
        Save a work to the database.
        
        Args:
            work: BlakeWork to save
        """
        try:
            self.database.save_work(work)
            logger.info(f"Saved work: {work.id}")
        except Exception as e:
            logger.error(f"Error saving work {work.id}: {e}")
            raise MetadataError(f"Failed to save work {work.id}: {e}")

    async def delete_work(self, work_id: str) -> bool:
        try:
            deleted = self.database.delete_work(work_id)
            if deleted:
                logger.info(f"Deleted work: {work_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting work {work_id}: {e}")
            raise MetadataError(f"Failed to delete work {work_id}: {e}")
    
    async def load_work(self, work_id: str) -> Optional[BlakeWork]:
        """
        Load a work from the database.
        
        Args:
            work_id: ID of work to load
            
        Returns:
            BlakeWork or None if not found
        """
        try:
            work = self.database.load_work(work_id)
            if work:
                logger.info(f"Loaded work: {work_id}")
            return work
        except Exception as e:
            logger.error(f"Error loading work {work_id}: {e}")
            return None
    
    async def load_all_works(self) -> List[BlakeWork]:
        """
        Load all works from the database.
        
        Returns:
            List of all BlakeWork objects
        """
        try:
            works = self.database.load_all_works()
            logger.info(f"Loaded {len(works)} works from database")
            return works
        except Exception as e:
            logger.error(f"Error loading all works: {e}")
            raise MetadataError(f"Failed to load all works: {e}")
    
    async def search_works(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[BlakeWork]:
        """
        Search works by query and filters.
        
        Args:
            query: Search query
            filters: Additional filters
            
        Returns:
            List of matching BlakeWork objects
        """
        try:
            # Load all works first
            all_works = await self.load_all_works()
            
            # Perform search
            results = self.searcher.search_works(all_works, query, filters)
            
            logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching works: {e}")
            raise MetadataError(f"Failed to search works: {e}")
    
    async def get_work_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the works collection.
        
        Returns:
            Dictionary of statistics
        """
        try:
            stats = self.database.get_statistics()
            logger.info("Retrieved work statistics")
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise MetadataError(f"Failed to get statistics: {e}")
    
    async def get_search_suggestions(self, partial_query: str) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            
        Returns:
            List of suggestions
        """
        try:
            all_works = await self.load_all_works()
            suggestions = self.searcher.get_search_suggestions(all_works, partial_query)
            return suggestions
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    async def get_facet_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Get facet counts for filtering.
        
        Returns:
            Dictionary of facet counts
        """
        try:
            all_works = await self.load_all_works()
            facets = self.searcher.get_facet_counts(all_works)
            return facets
        except Exception as e:
            logger.error(f"Error getting facet counts: {e}")
            return {}
    
    async def get_related_works(self, work_id: str, max_results: int = 5) -> List[BlakeWork]:
        """
        Get works related to a specific work.
        
        Args:
            work_id: ID of work to find related works for
            max_results: Maximum number of related works to return
            
        Returns:
            List of related BlakeWork objects
        """
        try:
            work = await self.load_work(work_id)
            if not work:
                return []
            
            all_works = await self.load_all_works()
            related = self.searcher.get_related_works(work, all_works, max_results)
            
            logger.info(f"Found {len(related)} related works for {work_id}")
            return related
            
        except Exception as e:
            logger.error(f"Error getting related works for {work_id}: {e}")
            return []
    
    async def update_work_metadata(self, work_id: str, 
                                 metadata_updates: Dict[str, Any]) -> Optional[BlakeWork]:
        """
        Update metadata for a specific work.
        
        Args:
            work_id: ID of work to update
            metadata_updates: Dictionary of metadata updates
            
        Returns:
            Updated BlakeWork or None if not found
        """
        try:
            work = await self.load_work(work_id)
            if not work:
                return None
            
            # Update metadata fields
            for key, value in metadata_updates.items():
                if hasattr(work.metadata, key):
                    setattr(work.metadata, key, value)
            
            # Mark as updated
            work.metadata.updated_at = datetime.now()
            
            # Save updated work
            await self.save_work(work)
            
            logger.info(f"Updated metadata for work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error updating work {work_id}: {e}")
            raise MetadataError(f"Failed to update work {work_id}: {e}")
    
    async def add_work_tag(self, work_id: str, tag: str) -> bool:
        """
        Add a tag to a work.
        
        Args:
            work_id: ID of work to tag
            tag: Tag to add
            
        Returns:
            True if successful
        """
        try:
            work = await self.load_work(work_id)
            if not work:
                return False
            
            if tag not in work.metadata.tags:
                work.metadata.tags.append(tag)
                work.metadata.updated_at = datetime.now()
                await self.save_work(work)
            
            logger.info(f"Added tag '{tag}' to work: {work_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding tag to work {work_id}: {e}")
            return False
    
    async def remove_work_tag(self, work_id: str, tag: str) -> bool:
        """
        Remove a tag from a work.
        
        Args:
            work_id: ID of work to untag
            tag: Tag to remove
            
        Returns:
            True if successful
        """
        try:
            work = await self.load_work(work_id)
            if not work:
                return False
            
            if tag in work.metadata.tags:
                work.metadata.tags.remove(tag)
                work.metadata.updated_at = datetime.now()
                await self.save_work(work)
            
            logger.info(f"Removed tag '{tag}' from work: {work_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing tag from work {work_id}: {e}")
            return False
    
    async def save_analysis_result(self, work_id: str, analysis_type: str,
                                 results: Dict[str, Any], confidence: Optional[float] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save analysis results for a work.
        
        Args:
            work_id: ID of work
            analysis_type: Type of analysis
            results: Analysis results
            confidence: Confidence score
            metadata: Additional metadata
        """
        try:
            self.database.save_analysis_result(work_id, analysis_type, results, confidence, metadata)
            logger.info(f"Saved analysis result for work {work_id}: {analysis_type}")
        except Exception as e:
            logger.error(f"Error saving analysis result for work {work_id}: {e}")
            raise MetadataError(f"Failed to save analysis result: {e}")
    
    async def load_analysis_results(self, work_id: str, 
                                  analysis_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load analysis results for a work.
        
        Args:
            work_id: ID of work
            analysis_type: Type of analysis (optional)
            
        Returns:
            List of analysis results
        """
        try:
            results = self.database.load_analysis_results(work_id, analysis_type)
            return results
        except Exception as e:
            logger.error(f"Error loading analysis results for work {work_id}: {e}")
            return []
    
    async def export_metadata(self, output_path: Path, 
                            works: Optional[List[BlakeWork]] = None) -> None:
        """
        Export metadata to a file.
        
        Args:
            output_path: Path to export file
            works: Works to export (if None, exports all)
        """
        try:
            if works is None:
                works = await self.load_all_works()
            
            # Convert works to dictionaries
            export_data = []
            for work in works:
                work_dict = {
                    'id': work.id,
                    'metadata': work.metadata.model_dump(mode="json"),
                    'text_content': work.text_content,
                    'images': [img.model_dump(mode="json") for img in work.images],
                    'text_analysis': work.text_analysis,
                    'visual_analysis': work.visual_analysis,
                    'cross_analysis': work.cross_analysis,
                }
                export_data.append(work_dict)
            
            # Save to file
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported metadata to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting metadata: {e}")
            raise MetadataError(f"Failed to export metadata: {e}")
    
    async def import_metadata(self, input_path: Path) -> List[BlakeWork]:
        """
        Import metadata from a file.
        
        Args:
            input_path: Path to import file
            
        Returns:
            List of imported BlakeWork objects
        """
        try:
            import json
            
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            works = []
            for work_data in data:
                # Reconstruct BlakeWork from dictionary
                work = BlakeWork(**work_data)
                works.append(work)
                
                # Save to database
                await self.save_work(work)
            
            logger.info(f"Imported {len(works)} works from: {input_path}")
            return works
            
        except Exception as e:
            logger.error(f"Error importing metadata: {e}")
            raise MetadataError(f"Failed to import metadata: {e}")
