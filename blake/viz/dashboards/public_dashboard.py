"""
Public Dashboard

Public corpus dashboard with coverage, rights, and accessibility
entry points for general audiences.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import DashboardComponent, InteractiveDashboard

logger = logging.getLogger(__name__)


class PublicDashboard:
    """Public engagement interactive dashboard."""
    
    def __init__(self):
        """Initialize public dashboard."""
        self.components = self._create_components()
        logger.info("Initialized PublicDashboard")
    
    def _create_components(self) -> List[DashboardComponent]:
        """Create public dashboard components."""
        from ..models import VisualizationConfig

        return [
            DashboardComponent(
                id="featured_works",
                component_type="featured",
                title="Featured Works",
                description="Selected works with the clearest local coverage and analysis.",
                config=VisualizationConfig(
                    viz_type="work_timeline",
                    title="Featured Works",
                    data_source="all_works",
                    curation="coverage-led",
                    update_frequency="on corpus refresh"
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="visual_stories",
                component_type="exploration",
                title="Exploration Paths",
                description="Guided entry points through chronology, themes, and source context.",
                config=VisualizationConfig(
                    viz_type="work_timeline",
                    title="Exploration Paths",
                    data_source="all_works",
                    narrative=True,
                    multimedia=True,
                    levels=["overview", "guided", "deep dive"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="social_sharing",
                component_type="coverage",
                title="Source Coverage",
                description="Current source mix, acquisition status, and remaining gaps.",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Source Coverage",
                    data_source="all_works",
                    platforms=["github", "zenodo"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="mobile_explorer",
                component_type="rights",
                title="Rights and Reuse",
                description="Public redistribution exclusions and source-license notes.",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Rights and Reuse",
                    data_source="all_works",
                    responsive=True,
                    touch_friendly=True
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="accessibility_tools",
                component_type="accessibility",
                title="Accessibility Tools",
                description="High-contrast, text-size, and screen-reader friendly controls.",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Accessibility Tools",
                    data_source="all_works",
                    features=["text_size", "contrast", "screen_reader"]
                ),
                data_source="all_works"
            )
        ]
    
    async def create_dashboard(
        self, config: Optional[Dict[str, Any]] = None
    ) -> InteractiveDashboard:
        """Create public dashboard."""
        from ..models import DashboardType
        logger.info("Creating public dashboard")

        summary = (config or {}).get("summary") or {}
        total_works = int(summary.get("total_works") or 0)
        total_images = int(summary.get("total_images") or 0)
        processed_works = int(summary.get("processed_works") or 0)
        source_count = len(summary.get("sources") or {})
        description = "Public corpus dashboard for general audiences."
        if summary:
            description = (
                "Public corpus dashboard with "
                f"{total_works} works, {total_images} images, "
                f"{processed_works} processed works, and {source_count} source families."
            )

        layout_config: Dict[str, Any] = {
            "type": "grid",
            "columns": 2,
            "rows": 3,
            "responsive": True,
        }
        if summary:
            layout_config["summary"] = {
                "total_works": total_works,
                "total_images": total_images,
                "processed_works": processed_works,
                "source_count": source_count,
                "coverage_status": summary.get("coverage_status"),
            }

        return InteractiveDashboard(
            id="public_dashboard",
            title="Public Corpus Dashboard",
            description=description,
            dashboard_type=DashboardType.PUBLIC,
            components=self.components,
            layout_config=layout_config,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    
    async def get_component(self, component_id: str) -> Optional[DashboardComponent]:
        """Get specific dashboard component."""
        for component in self.components:
            if component.id == component_id:
                return component
        return None
    
    def get_available_components(self) -> List[str]:
        """Get list of available component IDs."""
        return [component.id for component in self.components]
