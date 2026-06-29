"""
Research Dashboard

Advanced dashboard for researchers and academics with comprehensive
analysis tools and professional features.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import DashboardComponent, InteractiveDashboard

logger = logging.getLogger(__name__)


class ResearchDashboard:
    """Research-focused interactive dashboard."""
    
    def __init__(self):
        """Initialize research dashboard."""
        self.components = self._create_components()
        logger.info("Initialized ResearchDashboard")
    
    def _create_components(self) -> List[DashboardComponent]:
        """Create research dashboard components."""
        from ..models import VisualizationConfig
        
        return [
            DashboardComponent(
                id="advanced_search",
                component_type="search",
                title="Advanced Search",
                description="Comprehensive search across all works and metadata",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Advanced Search",
                    data_source="all_works",
                    filters={"date": True, "type": True, "theme": True, "source": True}
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="network_analysis",
                component_type="network",
                title="Network Analysis",
                description="Thematic and influence network analysis",
                config=VisualizationConfig(
                    viz_type="theme_network",
                    title="Network Analysis",
                    data_source="all_works",
                    layout="force",
                    interactive=True
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="comparative_analysis",
                component_type="comparison",
                title="Comparative Analysis",
                description="Side-by-side comparison of works and themes",
                config=VisualizationConfig(
                    viz_type="side_by_side_comparison",
                    title="Comparative Analysis",
                    data_source="selected_works",
                    views=["text", "image", "metadata"]
                ),
                data_source="selected_works"
            ),
            DashboardComponent(
                id="statistical_analysis",
                component_type="statistics",
                title="Statistical Analysis",
                description="Advanced statistical analysis and metrics",
                config=VisualizationConfig(
                    viz_type="frequency_chart",
                    title="Statistical Analysis",
                    data_source="all_works",
                    metrics=["frequency", "sentiment", "style"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="timeline_analysis",
                component_type="timeline",
                title="Timeline Analysis",
                description="Chronological analysis of works and themes",
                config=VisualizationConfig(
                    viz_type="work_timeline",
                    title="Timeline Analysis",
                    data_source="all_works",
                    granularity="year",
                    interactive=True
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="export_tools",
                component_type="export",
                title="Export Tools",
                description="Export data and visualizations in multiple formats",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Export Tools",
                    data_source="all_works",
                    formats=["json", "csv", "pdf", "html"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="collaboration_tools",
                component_type="collaboration",
                title="Collaboration Tools",
                description="Shared workspaces and collaborative features",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Collaboration Tools",
                    data_source="all_works",
                    features=["annotations", "comments", "sharing"]
                ),
                data_source="all_works"
            )
        ]
    
    async def create_dashboard(self, config: Optional[Dict[str, Any]] = None) -> InteractiveDashboard:
        """Create research dashboard."""
        from ..models import DashboardType
        logger.info("Creating research dashboard")
        
        return InteractiveDashboard(
            id="research_dashboard",
            title="Research Dashboard",
            description="Advanced dashboard for researchers and academics",
            dashboard_type=DashboardType.RESEARCH,
            components=self.components,
            layout_config={
                "type": "grid",
                "columns": 3,
                "rows": 3,
                "responsive": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    
    async def get_component(self, component_id: str) -> Optional[DashboardComponent]:
        """Get specific dashboard component."""
        for component in self.components:
            if component.id == component_id:
                return component
        return None
    
    async def update_component(self, component_id: str, updates: Dict[str, Any]) -> bool:
        """Update dashboard component."""
        for component in self.components:
            if component.id == component_id:
                for key, value in updates.items():
                    setattr(component, key, value)
                return True
        return False
    
    def get_available_components(self) -> List[str]:
        """Get list of available component IDs."""
        return [component.id for component in self.components]
