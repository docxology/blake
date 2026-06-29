"""
Dashboard module.
"""

from .dashboard_manager import DashboardManager
from .research_dashboard import ResearchDashboard
from .educational_dashboard import EducationalDashboard
from .public_dashboard import PublicDashboard
from .comparative_dashboard import ComparativeDashboard

__all__ = [
    "DashboardManager",
    "ResearchDashboard",
    "EducationalDashboard",
    "PublicDashboard",
    "ComparativeDashboard",
]
