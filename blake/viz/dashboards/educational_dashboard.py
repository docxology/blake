"""
Educational Dashboard

Student-friendly dashboard with guided learning paths and
educational tools for exploring Blake's works.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import DashboardComponent, InteractiveDashboard

logger = logging.getLogger(__name__)


class EducationalDashboard:
    """Education-focused interactive dashboard."""
    
    def __init__(self):
        """Initialize educational dashboard."""
        self.components = self._create_components()
        logger.info("Initialized EducationalDashboard")
    
    def _create_components(self) -> List[DashboardComponent]:
        """Create educational dashboard components."""
        from ..models import VisualizationConfig
        
        return [
            DashboardComponent(
                id="guided_tour",
                component_type="tour",
                title="Guided Tour",
                description="Interactive guided tour of Blake's works",
                config=VisualizationConfig(
                    viz_type="work_timeline",
                    title="Guided Tour",
                    data_source="all_works",
                    levels=["beginner", "intermediate", "advanced"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="learning_paths",
                component_type="learning",
                title="Learning Paths",
                description="Structured learning paths for different topics",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Learning Paths",
                    data_source="all_works",
                    topics=["poetry", "art", "philosophy", "history"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="interactive_lessons",
                component_type="lesson",
                title="Interactive Lessons",
                description="Interactive lessons and activities",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Interactive Lessons",
                    data_source="all_works",
                    types=["quiz", "exploration", "analysis"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="visual_explorer",
                component_type="explorer",
                title="Visual Explorer",
                description="Visual exploration of works and themes",
                config=VisualizationConfig(
                    viz_type="color_palette",
                    title="Visual Explorer",
                    data_source="visual_works",
                    modes=["timeline", "thematic", "comparative"]
                ),
                data_source="visual_works"
            ),
            DashboardComponent(
                id="progress_tracker",
                component_type="progress",
                title="Progress Tracker",
                description="Track learning progress and achievements",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Progress Tracker",
                    data_source="all_works",
                    metrics=["completion", "engagement", "understanding"]
                ),
                data_source="all_works"
            ),
            DashboardComponent(
                id="resource_library",
                component_type="library",
                title="Resource Library",
                description="Educational resources and materials",
                config=VisualizationConfig(
                    viz_type="metadata_analysis",
                    title="Resource Library",
                    data_source="all_works",
                    types=["texts", "images", "videos", "exercises"]
                ),
                data_source="all_works"
            )
        ]
    
    async def create_dashboard(self, config: Optional[Dict[str, Any]] = None) -> InteractiveDashboard:
        """Create educational dashboard."""
        from ..models import DashboardType
        logger.info("Creating educational dashboard")
        
        return InteractiveDashboard(
            id="educational_dashboard",
            title="Educational Dashboard",
            description="Student-friendly dashboard for learning about Blake's works",
            dashboard_type=DashboardType.EDUCATIONAL,
            components=self.components,
            layout_config={
                "type": "grid",
                "columns": 2,
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
    
    def get_available_components(self) -> List[str]:
        """Get list of available component IDs."""
        return [component.id for component in self.components]
