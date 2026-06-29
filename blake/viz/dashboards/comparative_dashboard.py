"""
Comparative Dashboard for Blake Analytics.

This module provides the comparative dashboard for visualization.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import DashboardComponent, InteractiveDashboard, VisualizationConfig

logger = logging.getLogger(__name__)


class ComparativeDashboard:
    """Dashboard for comparing multiple Blake works."""
    
    def __init__(self):
        """Initialize comparative dashboard."""
        self.components = self._create_components()
        logger.info("Initialized ComparativeDashboard")
    
    def _create_components(self) -> List[DashboardComponent]:
        """Create comparative dashboard components."""
        return [
            DashboardComponent(
                id="readability_comparison",
                component_type="comparison",
                title="Readability Comparison",
                description="Compare readability scores across works",
                config=VisualizationConfig(
                    viz_type="side_by_side_comparison",
                    title="Readability Comparison",
                    data_source="selected_works",
                    metrics=["flesch_reading_ease", "automated_readability_index"]
                ),
                data_source="selected_works"
            ),
            DashboardComponent(
                id="lexical_diversity",
                component_type="comparison",
                title="Lexical Diversity",
                description="Compare vocabulary richness",
                config=VisualizationConfig(
                    viz_type="side_by_side_comparison",
                    title="Lexical Diversity",
                    data_source="selected_works",
                    metrics=["ttr"]
                ),
                data_source="selected_works"
            ),
            DashboardComponent(
                id="sentiment_comparison",
                component_type="comparison",
                title="Sentiment Comparison",
                description="Compare sentiment polarity and subjectivity",
                config=VisualizationConfig(
                    viz_type="sentiment_timeline",
                    title="Sentiment Landscape",
                    data_source="selected_works",
                    metrics=["polarity", "subjectivity"]
                ),
                data_source="selected_works"
            ),
            DashboardComponent(
                id="text_length",
                component_type="comparison",
                title="Text Length",
                description="Compare document lengths",
                config=VisualizationConfig(
                    viz_type="frequency_chart",
                    title="Text Length",
                    data_source="selected_works",
                    metrics=["word_count"]
                ),
                data_source="selected_works"
            )
        ]
    
    async def create_dashboard(self, config: Optional[Dict[str, Any]] = None) -> InteractiveDashboard:
        """Create comparative dashboard."""
        logger.info("Creating comparative dashboard")
        
        dashboard_config = config or {}
        
        return InteractiveDashboard(
            id="comparative_dashboard",
            title="Comparative Analysis Dashboard",
            name="Comparative Analysis Dashboard",
            description="Dashboard for comparing multiple works",
            dashboard_type="research",
            components=self.components,
            layout={
                "type": "grid",
                "columns": 2,
                "rows": 2,
                "responsive": True
            },
            features=[
                "readability_comparison",
                "lexical_diversity",
                "sentiment_comparison",
                "text_length"
            ],
            config=dashboard_config,
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
