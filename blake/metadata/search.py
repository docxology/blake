"""
Search functionality for Blake metadata.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from ..models import BlakeWork, BlakeMetadata, WorkType, SourceType
from ..exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataSearcher:
    """Advanced search functionality for Blake works."""
    
    def __init__(self):
        """Initialize metadata searcher."""
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'would', 'you', 'your'
        }
    
    def search_works(self, works: List[BlakeWork], query: str, 
                    filters: Optional[Dict[str, Any]] = None) -> List[BlakeWork]:
        """
        Search works by query and filters.
        
        Args:
            works: List of works to search
            query: Search query
            filters: Additional filters
            
        Returns:
            List of matching works
        """
        if not query and not filters:
            return works
        
        # Apply text search
        if query:
            works = self._text_search(works, query)
        
        # Apply filters
        if filters:
            works = self._apply_filters(works, filters)
        
        return works
    
    def _text_search(self, works: List[BlakeWork], query: str) -> List[BlakeWork]:
        """Perform text search on works."""
        query_terms = self._tokenize_query(query)
        
        scored_works = []
        for work in works:
            score = self._calculate_relevance_score(work, query_terms)
            if score > 0:
                scored_works.append((work, score))
        
        # Sort by relevance score
        scored_works.sort(key=lambda x: x[1], reverse=True)
        
        return [work for work, score in scored_works]
    
    def _apply_filters(self, works: List[BlakeWork], filters: Dict[str, Any]) -> List[BlakeWork]:
        """Apply filters to works."""
        filtered_works = works
        
        # Work type filter
        if 'work_type' in filters and filters['work_type']:
            filtered_works = [
                w for w in filtered_works 
                if w.metadata.work_type == filters['work_type']
            ]
        
        # Source filter
        if 'source' in filters and filters['source']:
            filtered_works = [
                w for w in filtered_works 
                if w.metadata.source == filters['source']
            ]
        
        # Date range filter
        if 'date_range' in filters and filters['date_range']:
            start_date, end_date = filters['date_range']
            filtered_works = [
                w for w in filtered_works
                if w.metadata.creation_date and 
                start_date <= w.metadata.creation_date <= end_date
            ]
        
        # Tags filter
        if 'tags' in filters and filters['tags']:
            tag_list = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            filtered_works = [
                w for w in filtered_works
                if any(tag.lower() in [t.lower() for t in w.metadata.tags] for tag in tag_list)
            ]
        
        # Themes filter
        if 'themes' in filters and filters['themes']:
            theme_list = filters['themes'] if isinstance(filters['themes'], list) else [filters['themes']]
            filtered_works = [
                w for w in filtered_works
                if any(theme.lower() in [t.lower() for t in w.metadata.themes] for theme in theme_list)
            ]
        
        # Subjects filter
        if 'subjects' in filters and filters['subjects']:
            subject_list = filters['subjects'] if isinstance(filters['subjects'], list) else [filters['subjects']]
            filtered_works = [
                w for w in filtered_works
                if any(subject.lower() in [s.lower() for s in w.metadata.subjects] for subject in subject_list)
            ]
        
        # Has images filter
        if 'has_images' in filters and filters['has_images'] is not None:
            filtered_works = [
                w for w in filtered_works
                if (len(w.images) > 0) == filters['has_images']
            ]
        
        # Has text filter
        if 'has_text' in filters and filters['has_text'] is not None:
            filtered_works = [
                w for w in filtered_works
                if (w.text_content is not None and len(w.text_content.strip()) > 0) == filters['has_text']
            ]
        
        # Processed filter
        if 'processed' in filters and filters['processed'] is not None:
            filtered_works = [
                w for w in filtered_works
                if w.metadata.processed == filters['processed']
            ]
        
        return filtered_works
    
    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize search query."""
        # Remove special characters and split
        tokens = re.findall(r'\b\w+\b', query.lower())
        
        # Remove stop words
        tokens = [token for token in tokens if token not in self.stop_words]
        
        return tokens
    
    def _calculate_relevance_score(self, work: BlakeWork, query_terms: List[str]) -> float:
        """Calculate relevance score for a work."""
        score = 0.0
        
        # Search in title (highest weight)
        title_text = work.metadata.title.lower()
        for term in query_terms:
            if term in title_text:
                score += 3.0
        
        # Search in description
        if work.metadata.description:
            desc_text = work.metadata.description.lower()
            for term in query_terms:
                if term in desc_text:
                    score += 2.0
        
        # Search in text content
        if work.text_content:
            content_text = work.text_content.lower()
            for term in query_terms:
                if term in content_text:
                    score += 1.0
        
        # Search in tags
        for tag in work.metadata.tags:
            tag_lower = tag.lower()
            for term in query_terms:
                if term in tag_lower:
                    score += 1.5
        
        # Search in themes
        for theme in work.metadata.themes:
            theme_lower = theme.lower()
            for term in query_terms:
                if term in theme_lower:
                    score += 1.5
        
        # Search in subjects
        for subject in work.metadata.subjects:
            subject_lower = subject.lower()
            for term in query_terms:
                if term in subject_lower:
                    score += 1.5
        
        # Search in image descriptions
        for image in work.images:
            if image.description:
                img_desc = image.description.lower()
                for term in query_terms:
                    if term in img_desc:
                        score += 0.5
        
        return score
    
    def get_search_suggestions(self, works: List[BlakeWork], partial_query: str) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = set()
        partial_lower = partial_query.lower()
        
        for work in works:
            # Title suggestions
            if partial_lower in work.metadata.title.lower():
                suggestions.add(work.metadata.title)
            
            # Tag suggestions
            for tag in work.metadata.tags:
                if partial_lower in tag.lower():
                    suggestions.add(tag)
            
            # Theme suggestions
            for theme in work.metadata.themes:
                if partial_lower in theme.lower():
                    suggestions.add(theme)
            
            # Subject suggestions
            for subject in work.metadata.subjects:
                if partial_lower in subject.lower():
                    suggestions.add(subject)
        
        return sorted(list(suggestions))[:10]  # Return top 10 suggestions
    
    def get_facet_counts(self, works: List[BlakeWork]) -> Dict[str, Dict[str, int]]:
        """Get facet counts for filtering."""
        facets = {
            'work_types': {},
            'sources': {},
            'tags': {},
            'themes': {},
            'subjects': {},
            'series': {},
        }
        
        for work in works:
            # Work types
            work_type = work.metadata.work_type
            facets['work_types'][work_type] = facets['work_types'].get(work_type, 0) + 1
            
            # Sources
            source = work.metadata.source
            facets['sources'][source] = facets['sources'].get(source, 0) + 1
            
            # Tags
            for tag in work.metadata.tags:
                facets['tags'][tag] = facets['tags'].get(tag, 0) + 1
            
            # Themes
            for theme in work.metadata.themes:
                facets['themes'][theme] = facets['themes'].get(theme, 0) + 1
            
            # Subjects
            for subject in work.metadata.subjects:
                facets['subjects'][subject] = facets['subjects'].get(subject, 0) + 1
            
            # Series
            if work.metadata.series:
                series = work.metadata.series
                facets['series'][series] = facets['series'].get(series, 0) + 1
        
        return facets
    
    def get_date_range(self, works: List[BlakeWork]) -> Optional[Tuple[datetime, datetime]]:
        """Get date range for works."""
        dates = [w.metadata.creation_date for w in works if w.metadata.creation_date]
        
        if not dates:
            return None
        
        return (min(dates), max(dates))
    
    def get_related_works(self, work: BlakeWork, all_works: List[BlakeWork], 
                         max_results: int = 5) -> List[BlakeWork]:
        """Find works related to the given work."""
        # Get common themes and subjects
        work_themes = set(work.metadata.themes)
        work_subjects = set(work.metadata.subjects)
        work_tags = set(work.metadata.tags)
        
        scored_works = []
        
        for other_work in all_works:
            if other_work.id == work.id:
                continue
            
            score = 0.0
            
            # Theme similarity
            other_themes = set(other_work.metadata.themes)
            theme_intersection = work_themes.intersection(other_themes)
            if theme_intersection:
                score += len(theme_intersection) * 2.0
            
            # Subject similarity
            other_subjects = set(other_work.metadata.subjects)
            subject_intersection = work_subjects.intersection(other_subjects)
            if subject_intersection:
                score += len(subject_intersection) * 1.5
            
            # Tag similarity
            other_tags = set(other_work.metadata.tags)
            tag_intersection = work_tags.intersection(other_tags)
            if tag_intersection:
                score += len(tag_intersection) * 1.0
            
            # Series similarity
            if work.metadata.series and other_work.metadata.series:
                if work.metadata.series == other_work.metadata.series:
                    score += 3.0
            
            # Date proximity (works from similar time periods)
            if work.metadata.creation_date and other_work.metadata.creation_date:
                date_diff = abs((work.metadata.creation_date - other_work.metadata.creation_date).days)
                if date_diff < 365:  # Within a year
                    score += 1.0
            
            if score > 0:
                scored_works.append((other_work, score))
        
        # Sort by score and return top results
        scored_works.sort(key=lambda x: x[1], reverse=True)
        return [w for w, score in scored_works[:max_results]]

