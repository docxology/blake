"""
Main GUI application for Blake works exploration.
"""

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import sys

# Handle imports for both package and direct script execution
# When run via `streamlit run blake/gui/gui.py`, __package__ is None
if __name__ == "__main__" or __package__ is None or __package__ == "":
    # Direct execution - add parent directories to path
    _gui_dir = Path(__file__).resolve().parent
    _blake_dir = _gui_dir.parent
    _project_dir = _blake_dir.parent
    if str(_project_dir) not in sys.path:
        sys.path.insert(0, str(_project_dir))
    from blake.models import BlakeWork, BlakeImage
    from blake.exceptions import BlakeError
    from blake.provenance import manifest_context_for_work, work_provenance
else:
    # Package execution
    from ..models import BlakeWork, BlakeImage
    from ..exceptions import BlakeError
    from ..provenance import manifest_context_for_work, work_provenance

from blake.version import version_info

logger = logging.getLogger(__name__)


class BlakeGUI:
    """Main GUI application for exploring Blake works."""
    
    def __init__(self, data_dir: Path, output_dir: Optional[Path] = None):
        """
        Initialize Blake GUI.
        
        Args:
            data_dir: Directory containing Blake data
        """
        self.data_dir = Path(data_dir)
        self.output_dir = (
            Path(output_dir) if output_dir is not None
            else self.data_dir.parent / "analysis_output"
        )
        self.analysis_context = None
        self.analysis_error = None
        from blake.corpus.saved_epoch import load_saved_analysis_epoch
        try:
            self.analysis_context = load_saved_analysis_epoch(
                self.data_dir, self.output_dir
            )
        except Exception as exc:
            self.analysis_error = str(exc)
        self.collection_dir = (
            self.analysis_context["store"] if self.analysis_context else self.data_dir
        )
        self.works_cache = {}
    
    def run(self, host: str = "localhost", port: int = 8501) -> None:
        """
        Run the GUI application.
        
        Args:
            host: Host to run on
            port: Port to run on
        """
        if not STREAMLIT_AVAILABLE or st is None:
            logger.error("Streamlit is not installed or failed to import. Cannot run GUI.")
            print("Error: Streamlit is not installed. Please install 'streamlit' to run the GUI.")
            return

        logger.info(f"Starting Blake GUI on {host}:{port}")
        
        # Configure Streamlit
        st.set_page_config(
            page_title="Blake Works Explorer",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Main app
        self._render_app()
    
    def _render_app(self) -> None:
        """Render the main application."""
        st.title("Blake Works Explorer")
        identity = version_info()
        st.caption(f"Blake {identity['package_version']} · Methods {identity['methods_profile']}")
        st.markdown("Explore the current target-aware Blake corpus with interactive analysis and visualization.")
        
        # Sidebar
        with st.sidebar:
            self._render_sidebar()
        
        # Main content
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Browse Works", "Search & Filter", "Analysis", "Export", "Local evidence"])
        
        with tab1:
            self._render_browse_works()
        
        with tab2:
            self._render_search_filter()
        
        with tab3:
            self._render_analysis()
        
        with tab4:
            self._render_export()

        with tab5:
            from blake.gui.evidence_panel import render_evidence_panel
            render_evidence_panel(self.data_dir)
    
    def _render_sidebar(self) -> None:
        """Render the sidebar."""
        st.header("Navigation")
        if self.analysis_error:
            st.warning(
                "Saved analysis unavailable: " + self.analysis_error
                + ". Browsing captured records."
            )
        elif self.analysis_context:
            context = self.analysis_context
            st.info(
                f"Saved analysis {context['run_id']} · "
                f"producer {context['analysis_software_version']}"
            )
            if "nested_error_count" in context:
                st.caption(
                    f"{context['nested_error_count']} unavailable sub-analysis results; "
                    "record completion is separate."
                )
        else:
            st.info("No verified saved analysis epoch. Browsing captured records.")
        st.caption(
            "Counts describe source/copy records and image associations, "
            "not distinct Blake works or unique images."
        )
        
        # Quick stats
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        # Load basic stats
        try:
            stats = self._get_collection_stats()
            st.metric("Local records", stats.get('total_works', 0))
            st.metric("Image associations", stats.get('total_images', 0))
            st.metric("Processed records", stats.get('processed_works', 0))
        except Exception as e:
            st.error(f"Error loading stats: {e}")
    
    def _render_browse_works(self) -> None:
        """Render the browse works tab."""
        st.header("Browse Blake's Works")
        
        # Load works
        works = self._load_works()
        
        if not works:
            st.warning("No works found. Please download some works first.")
            return
        
        # Work type filter
        work_types = list(set(work.metadata.work_type for work in works))
        selected_type = st.selectbox("Filter by Work Type", ["All"] + work_types)
        
        # Filter works
        filtered_works = works
        if selected_type != "All":
            filtered_works = [w for w in works if w.metadata.work_type == selected_type]
        
        # Display works
        for work in self._paged_works(filtered_works, "browse"):
            with st.expander(f"{work.metadata.title} ({work.metadata.work_type})"):
                if st.checkbox("Load details and images", key=f"browse:load:{work.id}"):
                    self._render_work_details(work)
    
    def _paged_works(self, works: List[BlakeWork], scope: str) -> List[BlakeWork]:
        """Bound rendered media while retaining the complete collection and counts."""
        if len(works) <= 25:
            return works
        pages = (len(works) + 24) // 25
        page = st.selectbox("Results page", list(range(1, pages + 1)), key=scope + ":page")
        start = (page - 1) * 25
        st.caption(f"Showing {start + 1}–{min(start + 25, len(works))} of {len(works)} works")
        return works[start:start + 25]

    def _render_work_details(self, work: BlakeWork, key_prefix: str = "browse") -> None:
        """Render details for a specific work."""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic info
            st.subheader(work.metadata.title)
            st.write(f"**Type:** {work.metadata.work_type}")
            st.write(f"**Date:** {work.metadata.creation_date or 'Unknown'}")
            provenance = work_provenance(work)
            manifest_context = manifest_context_for_work(
                work, self._manifest_payload()
            )
            st.write(f"**Source:** {work.metadata.source}")
            if manifest_context.get("coverage_status"):
                st.write(f"**Coverage Status:** {manifest_context['coverage_status']}")
            if manifest_context.get("target_id"):
                st.write(f"**Target ID:** {manifest_context['target_id']}")
            st.write(f"**Authority Tier:** {provenance['source_authority_tier']}")
            st.write(f"**Text Evidence:** {'local' if work.text_content else 'not local'}")
            st.write(f"**Image Evidence:** {len(work.images)} local files")
            st.write(f"**Rights Status:** {provenance['rights_disposition']}")
            if provenance.get("source_url"):
                st.write(f"**Source URL:** {provenance['source_url']}")
            
            if work.metadata.description:
                st.write(f"**Description:** {work.metadata.description}")
            
            # Text content
            if work.text_content:
                st.subheader("Text Content")
                st.text_area(
                    "Text content", work.text_content, height=200, disabled=True,
                    key=f"{key_prefix}:text:{work.id}",
                )
            
            # Tags and themes
            if work.metadata.tags or work.metadata.themes:
                st.subheader("Tags & Themes")
                if work.metadata.tags:
                    st.write("**Tags:**", ", ".join(work.metadata.tags))
                if work.metadata.themes:
                    st.write("**Themes:**", ", ".join(work.metadata.themes))
        
        with col2:
            # Images
            if work.images:
                st.subheader("Images")
                for i, image in enumerate(work.images[:3]):  # Show first 3 images
                    if image.thumbnail_path and image.thumbnail_path.exists():
                        st.image(str(image.thumbnail_path), caption=image.title, use_column_width=True)
                    elif image.file_path and image.file_path.exists():
                        st.image(str(image.file_path), caption=image.title, use_column_width=True)
                
                if len(work.images) > 3:
                    st.write(f"... and {len(work.images) - 3} more images")
            
            # Analysis results
            if work.text_analysis or work.visual_analysis or work.cross_analysis:
                st.subheader("Analysis")
                
                if work.text_analysis:
                    st.write("✅ Text Analysis")
                if work.visual_analysis:
                    st.write("✅ Visual Analysis")
                if work.cross_analysis:
                    st.write("✅ Cross Analysis")
    
    def _render_search_filter(self) -> None:
        """Render the search and filter tab."""
        st.header("Search & Filter Works")
        
        # Search interface
        search_query = st.text_input("Search Query", placeholder="Enter keywords to search...")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            work_types = st.multiselect("Work Types", ["poem", "prose", "letter", "manuscript", "plate", "drawing", "painting", "engraving"])
        
        with col2:
            sources = st.multiselect("Sources", ["blake_archive", "project_gutenberg", "internet_archive", "british_museum", "tate", "wikimedia"])
        
        with col3:
            has_images = st.selectbox("Has Images", ["All", "Yes", "No"])
            has_text = st.selectbox("Has Text", ["All", "Yes", "No"])
        
        # Search button
        if st.button("Search"):
            filters = {}
            if work_types:
                filters['work_type'] = work_types
            if sources:
                filters['source'] = sources
            if has_images != "All":
                filters['has_images'] = has_images == "Yes"
            if has_text != "All":
                filters['has_text'] = has_text == "Yes"
            
            st.session_state["metadata-search-request"] = {"query": search_query, "filters": filters}
            st.session_state.pop("search:page", None)

        request = st.session_state.get("metadata-search-request")
        if request is not None:
            results = self._search_works(request["query"], request["filters"])
            st.subheader(f"Search Results ({len(results)} found)")
            for work in self._paged_works(results, "search"):
                with st.expander(f"{work.metadata.title}"):
                    if st.checkbox("Load details and images", key=f"search:load:{work.id}"):
                        self._render_work_details(work, key_prefix="search")

    def _manifest_payload(self) -> Dict[str, Any]:
        path = Path(self.output_dir) / "corpus_manifest.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    
    def _render_analysis(self) -> None:
        """Render the analysis tab."""
        st.header("Analysis & Visualization")
        
        # Load works
        works = self._load_works()
        
        if not works:
            st.warning("No works found for analysis.")
            return
        
        # Analysis options
        analysis_type = st.selectbox("Analysis Type", [
            "Work Statistics",
            "Theme Analysis", 
            "Chronological Analysis",
            "Text Analysis",
            "Visual Analysis",
            "Cross Analysis"
        ])
        
        if analysis_type == "Work Statistics":
            self._render_work_statistics(works)
        elif analysis_type == "Theme Analysis":
            self._render_theme_analysis(works)
        elif analysis_type == "Chronological Analysis":
            self._render_chronological_analysis(works)
        elif analysis_type == "Text Analysis":
            self._render_text_analysis(works)
        elif analysis_type == "Visual Analysis":
            self._render_visual_analysis(works)
        elif analysis_type == "Cross Analysis":
            self._render_cross_analysis(works)
    
    def _render_work_statistics(self, works: List[BlakeWork]) -> None:
        """Render work statistics."""
        st.subheader("Collection Statistics")
        
        # Basic counts
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Works", len(works))
        
        with col2:
            total_images = sum(len(work.images) for work in works)
            st.metric("Local Image Evidence", total_images)
        
        with col3:
            processed_works = sum(1 for work in works if work.fully_processed)
            st.metric("Processed Locally", processed_works)
        
        with col4:
            works_with_text = sum(1 for work in works if work.text_content)
            st.metric("Local Text Evidence", works_with_text)
        
        # Work types distribution
        st.subheader("Work Types Distribution")
        work_types = [work.metadata.work_type for work in works]
        type_counts = {}
        for work_type in work_types:
            type_counts[work_type] = type_counts.get(work_type, 0) + 1
        
        st.bar_chart(type_counts)
        
        # Sources distribution
        st.subheader("Sources Distribution")
        sources = [work.metadata.source for work in works]
        source_counts = {}
        for source in sources:
            source_counts[source] = source_counts.get(source, 0) + 1
        
        st.bar_chart(source_counts)
    
    def _render_theme_analysis(self, works: List[BlakeWork]) -> None:
        """Render theme analysis."""
        st.subheader("Theme Analysis")
        
        # Collect all themes
        all_themes = []
        for work in works:
            all_themes.extend(work.metadata.themes)
        
        if not all_themes:
            st.warning("No themes found in the works.")
            return
        
        # Theme frequency
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        # Sort by frequency
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Display top themes
        st.write("**Most Common Themes:**")
        for theme, count in sorted_themes[:10]:
            st.write(f"- {theme}: {count} works")
        
        # Theme visualization
        if len(sorted_themes) > 0:
            st.bar_chart(dict(sorted_themes[:10]))
    
    def _render_chronological_analysis(self, works: List[BlakeWork]) -> None:
        """Render chronological analysis."""
        st.subheader("Chronological Analysis")
        
        # Filter works with dates
        dated_works = [work for work in works if work.metadata.creation_date]
        
        if not dated_works:
            st.warning("No works with creation dates found.")
            return
        
        # Sort by date
        dated_works.sort(key=lambda x: x.metadata.creation_date)
        
        # Display timeline
        st.write("**Timeline of Works:**")
        for work in dated_works:
            date_str = work.metadata.creation_date.strftime("%Y-%m-%d")
            st.write(f"- {date_str}: {work.metadata.title}")
        
        # Date range
        earliest = dated_works[0].metadata.creation_date
        latest = dated_works[-1].metadata.creation_date
        st.write(f"**Date Range:** {earliest.strftime('%Y')} - {latest.strftime('%Y')}")
    
    def _render_text_analysis(self, works: List[BlakeWork]) -> None:
        """Render text analysis."""
        st.subheader("Text Analysis")
        
        # Select work for detailed analysis
        works_with_text = [work for work in works if work.text_content]
        
        if not works_with_text:
            st.warning("No works with text content found.")
            return
        
        selected_work = st.selectbox("Select Work for Analysis", 
                                   [work.metadata.title for work in works_with_text])
        
        work = next(work for work in works_with_text if work.metadata.title == selected_work)
        
        # Display text analysis results
        if work.text_analysis:
            st.write("**Text Analysis Results:**")
            
            # Basic stats
            basic_stats = work.text_analysis.get('basic_stats', {})
            if basic_stats:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Word Count", basic_stats.get('word_count', 0))
                with col2:
                    st.metric("Sentence Count", basic_stats.get('sentence_count', 0))
                with col3:
                    st.metric("Vocabulary Richness", f"{basic_stats.get('vocabulary_richness', 0):.2f}")
            
            # Sentiment analysis
            sentiment = work.text_analysis.get('sentiment', {})
            if sentiment and 'sentiment' in sentiment:
                st.write(f"**Sentiment:** {sentiment['sentiment']}")
                if 'compound_score' in sentiment:
                    st.write(f"**Compound Score:** {sentiment['compound_score']:.3f}")
            
            # Topics
            topics = work.text_analysis.get('topics', {})
            if topics and 'topics' in topics:
                st.write("**Topics:**")
                for topic in topics['topics']:
                    st.write(f"- {', '.join(topic['words'][:5])}")
        else:
            st.info("No text analysis available for this work.")
    
    def _render_visual_analysis(self, works: List[BlakeWork]) -> None:
        """Render visual analysis."""
        st.subheader("Visual Analysis")
        
        # Collect all images
        all_images = []
        for work in works:
            all_images.extend(work.images)
        
        if not all_images:
            st.warning("No images found for analysis.")
            return
        
        st.write(f"**Total Images:** {len(all_images)}")
        
        # Display image analysis if available
        analyzed_images = 0
        for work in works:
            if work.visual_analysis:
                analyzed_images += len(work.visual_analysis)
        
        st.write(f"**Analyzed Images:** {analyzed_images}")
    
    def _render_cross_analysis(self, works: List[BlakeWork]) -> None:
        """Render cross analysis."""
        st.subheader("Cross Analysis")
        
        # Find works with both text and images
        cross_works = [work for work in works if work.text_content and work.images]
        
        if not cross_works:
            st.warning("No works with both text and images found for cross analysis.")
            return
        
        st.write(f"**Works with Text and Images:** {len(cross_works)}")
        
        # Display cross analysis results
        for work in cross_works:
            if work.cross_analysis:
                with st.expander(f"Cross Analysis: {work.metadata.title}"):
                    st.json(work.cross_analysis)
    
    def _render_export(self) -> None:
        """Render the export tab."""
        st.header("Export Data")
        
        # Export options
        export_format = st.selectbox("Export Format", ["JSON", "CSV", "PDF"])
        
        # Filter options
        st.subheader("Filter Works to Export")
        works = self._load_works()
        
        if works:
            work_types = list(set(work.metadata.work_type for work in works))
            selected_types = st.multiselect("Work Types", work_types, default=work_types)
            
            # Filter works
            filtered_works = [work for work in works if work.metadata.work_type in selected_types]
            
            st.write(f"**Works to Export:** {len(filtered_works)}")
            
            # Export button
            if st.button("Export Data"):
                try:
                    export_data = self._prepare_export_data(filtered_works, export_format)
                    
                    if export_format == "JSON":
                        st.download_button(
                            "Download JSON",
                            data=json.dumps(export_data, indent=2, default=str),
                            file_name=f"blake_works_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    else:
                        st.info(f"Export format {export_format} not yet implemented.")
                
                except Exception as e:
                    st.error(f"Error exporting data: {e}")
        else:
            st.warning("No works found to export.")
    
    def _load_works(self) -> List[BlakeWork]:
        """Load works from cache or database."""
        if not self.works_cache:
            try:
                from blake.metadata.database import MetadataDatabase

                path = self.collection_dir / "metadata/metadata.db"
                if not path.is_file():
                    return []
                works = MetadataDatabase(path).load_all_works()
                self.works_cache = {work.id: work for work in works}
            except Exception as e:
                st.error(f"Error loading works: {e}")
                return []
        
        return list(self.works_cache.values())
    
    def _get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        works = self._load_works()
        
        return {
            'total_works': len(works),
            'total_images': sum(len(work.images) for work in works),
            'processed_works': sum(1 for work in works if work.fully_processed),
        }
    
    def _search_works(self, query: str, filters: Dict[str, Any]) -> List[BlakeWork]:
        """Search works based on query and filters."""
        works = self._load_works()
        selected_types = filters.get('work_types') or filters.get('work_type')
        selected_sources = filters.get('sources') or filters.get('source')
        
        # Simple search implementation
        results = []
        for work in works:
            # Text search
            if query:
                search_text = f"{work.metadata.title} {work.metadata.description or ''} {work.text_content or ''}"
                if query.lower() not in search_text.lower():
                    continue
            
            # Apply filters
            if selected_types:
                selected = selected_types
                if work.metadata.work_type not in (selected if isinstance(selected, list) else [selected]):
                    continue
            if selected_sources:
                selected = selected_sources
                if work.metadata.source not in (selected if isinstance(selected, list) else [selected]):
                    continue
            if filters.get('has_images') is not None:
                has_images = len(work.images) > 0
                if has_images != filters['has_images']:
                    continue
            if filters.get('has_text') is not None:
                has_text = work.text_content is not None and len(work.text_content.strip()) > 0
                if has_text != filters['has_text']:
                    continue
            
            results.append(work)
        
        return results
    
    def _prepare_export_data(self, works: List[BlakeWork], format: str) -> Any:
        """Prepare data for export."""
        if format == "JSON":
            export_data = []
            for work in works:
                work_data = {
                    'id': work.id,
                    'provenance': work_provenance(work),
                    'metadata': work.metadata.model_dump(mode="json"),
                    'text_content': work.text_content,
                    'images': [img.model_dump(mode="json") for img in work.images],
                    'text_analysis': work.text_analysis,
                    'visual_analysis': work.visual_analysis,
                    'cross_analysis': work.cross_analysis,
                }
                export_data.append(work_data)
            return export_data
        
        return None


# Main execution for Streamlit
# This runs when Streamlit executes the script
if __name__ == "__main__" and STREAMLIT_AVAILABLE and st is not None:
    # Initialize and run the GUI
    data_dir = Path(__file__).resolve().parent.parent.parent / "blake_data"
    gui = BlakeGUI(data_dir)
    gui.run()
