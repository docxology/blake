"""
Dashboard Manager

Manages all dashboard types and provides unified interface
for dashboard creation and management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .research_dashboard import ResearchDashboard
from .educational_dashboard import EducationalDashboard
from .public_dashboard import PublicDashboard
from ..models import InteractiveDashboard

logger = logging.getLogger(__name__)


class DashboardManager:
    """Manages all dashboard types."""
    
    def __init__(self):
        """Initialize dashboard manager."""
        self.research_dashboard = ResearchDashboard()
        self.educational_dashboard = EducationalDashboard()
        self.public_dashboard = PublicDashboard()
        logger.info("Initialized DashboardManager")
    
    async def create_dashboard(self, dashboard_type: str, config: Optional[Dict[str, Any]] = None) -> InteractiveDashboard:
        """Create dashboard of specified type."""
        logger.info(f"Creating {dashboard_type} dashboard")
        
        if dashboard_type == "research":
            return await self.research_dashboard.create_dashboard(config)
        elif dashboard_type == "educational":
            return await self.educational_dashboard.create_dashboard(config)
        elif dashboard_type == "public":
            return await self.public_dashboard.create_dashboard(config)
        else:
            raise ValueError(f"Unknown dashboard type: {dashboard_type}")
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary of all available dashboards."""
        return {
            "available_dashboards": [
                {
                    "type": "research",
                    "name": "Research Dashboard",
                    "description": "Advanced dashboard for researchers and academics",
                    "component_count": len(self.research_dashboard.components)
                },
                {
                    "type": "educational", 
                    "name": "Educational Dashboard",
                    "description": "Student-friendly dashboard for learning",
                    "component_count": len(self.educational_dashboard.components)
                },
                {
                    "type": "public",
                    "name": "Public Corpus Dashboard",
                    "description": "Public corpus dashboard with coverage and rights context",
                    "component_count": len(self.public_dashboard.components)
                }
            ],
            "total_dashboards": 3,
            "total_components": (
                len(self.research_dashboard.components) +
                len(self.educational_dashboard.components) +
                len(self.public_dashboard.components)
            )
        }
    
    async def get_dashboard_types(self) -> List[str]:
        """Get list of available dashboard types."""
        return ["research", "educational", "public"]
    
    async def get_dashboard_components(self, dashboard_type: str) -> List[str]:
        """Get components for specific dashboard type."""
        if dashboard_type == "research":
            return self.research_dashboard.get_available_components()
        elif dashboard_type == "educational":
            return self.educational_dashboard.get_available_components()
        elif dashboard_type == "public":
            return self.public_dashboard.get_available_components()
        else:
            raise ValueError(f"Unknown dashboard type: {dashboard_type}")
