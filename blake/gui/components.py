"""
GUI components for Blake interface.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import logging

from ..models import BlakeWork, BlakeImage

logger = logging.getLogger(__name__)


class WorkBrowser:
    """Component for browsing Blake works."""
    
    def __init__(self):
        """Initialize work browser."""
        pass
    
    def render(self, works: List[BlakeWork]) -> None:
        """Render work browser interface."""
        st.subheader("Browse Works")
        
        if not works:
            st.warning("No works found.")
            return
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            work_types = list(set(work.metadata.work_type for work in works))
            selected_type = st.selectbox("Work Type", ["All"] + work_types)
        
        with col2:
            sources = list(set(work.metadata.source for work in works))
            selected_source = st.selectbox("Source", ["All"] + sources)
        
        # Filter works
        filtered_works = works
        if selected_type != "All":
            filtered_works = [w for w in filtered_works if w.metadata.work_type == selected_type]
        if selected_source != "All":
            filtered_works = [w for w in filtered_works if w.metadata.source == selected_source]
        
        # Display works
        for work in filtered_works:
            self._render_work_card(work)
    
    def _render_work_card(self, work: BlakeWork) -> None:
        """Render a work card."""
        with st.expander(f"{work.metadata.title} ({work.metadata.work_type})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Date:** {work.metadata.creation_date or 'Unknown'}")
                st.write(f"**Source:** {work.metadata.source}")
                if work.metadata.description:
                    st.write(f"**Description:** {work.metadata.description}")
            
            with col2:
                if work.images:
                    st.write(f"**Images:** {len(work.images)}")
                if work.text_content:
                    st.write("**Text:** Available")
                if work.fully_processed:
                    st.write("**Status:** Processed")


class AnalysisViewer:
    """Component for viewing analysis results."""
    
    def __init__(self):
        """Initialize analysis viewer."""
        pass
    
    def render(self, work: BlakeWork) -> None:
        """Render analysis results for a work."""
        st.subheader(f"Analysis: {work.metadata.title}")
        
        # Text analysis
        if work.text_analysis:
            self._render_text_analysis(work.text_analysis)
        
        # Visual analysis
        if work.visual_analysis:
            self._render_visual_analysis(work.visual_analysis)
        
        # Cross analysis
        if work.cross_analysis:
            self._render_cross_analysis(work.cross_analysis)
    
    def _render_text_analysis(self, analysis: Dict[str, Any]) -> None:
        """Render text analysis results."""
        st.subheader("Text Analysis")
        
        # Basic statistics
        if 'basic_stats' in analysis:
            stats = analysis['basic_stats']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Word Count", stats.get('word_count', 0))
            with col2:
                st.metric("Sentences", stats.get('sentence_count', 0))
            with col3:
                st.metric("Vocabulary Richness", f"{stats.get('vocabulary_richness', 0):.2f}")
        
        # Sentiment
        if 'sentiment' in analysis:
            sentiment = analysis['sentiment']
            st.write(f"**Sentiment:** {sentiment.get('sentiment', 'Unknown')}")
            if 'compound_score' in sentiment:
                st.write(f"**Score:** {sentiment['compound_score']:.3f}")
    
    def _render_visual_analysis(self, analysis: Dict[str, Any]) -> None:
        """Render visual analysis results."""
        st.subheader("Visual Analysis")
        
        for image_id, image_analysis in analysis.items():
            if isinstance(image_analysis, dict):
                st.write(f"**Image {image_id}:**")
                
                if 'basic_properties' in image_analysis:
                    props = image_analysis['basic_properties']
                    st.write(f"Dimensions: {props.get('width', 0)}x{props.get('height', 0)}")
                    st.write(f"Aspect Ratio: {props.get('aspect_ratio', 0):.2f}")
    
    def _render_cross_analysis(self, analysis: Dict[str, Any]) -> None:
        """Render cross analysis results."""
        st.subheader("Cross Analysis")
        
        if 'text_image_correlation' in analysis:
            correlation = analysis['text_image_correlation']
            if 'jaccard_similarity' in correlation:
                st.write(f"**Text-Image Similarity:** {correlation['jaccard_similarity']:.3f}")


class SearchInterface:
    """Component for searching works."""
    
    def __init__(self):
        """Initialize search interface."""
        pass
    
    def render(self, on_search) -> None:
        """Render search interface."""
        st.subheader("Search Works")
        
        # Search query
        query = st.text_input("Search Query", placeholder="Enter keywords...")
        
        # Filters
        with st.expander("Filters"):
            col1, col2 = st.columns(2)
            
            with col1:
                work_types = st.multiselect("Work Types", [
                    "poem", "prose", "letter", "manuscript", 
                    "plate", "drawing", "painting", "engraving"
                ])
                
                has_images = st.selectbox("Has Images", ["All", "Yes", "No"])
            
            with col2:
                sources = st.multiselect("Sources", [
                    "blake_archive", "project_gutenberg", "internet_archive",
                    "british_museum", "tate", "wikimedia"
                ])
                
                has_text = st.selectbox("Has Text", ["All", "Yes", "No"])
        
        # Search button
        if st.button("Search"):
            filters = {}
            if work_types:
                filters['work_types'] = work_types
            if sources:
                filters['sources'] = sources
            if has_images != "All":
                filters['has_images'] = has_images == "Yes"
            if has_text != "All":
                filters['has_text'] = has_text == "Yes"
            
            on_search(query, filters)

