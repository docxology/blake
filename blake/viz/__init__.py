"""
Blake Visualization System

A comprehensive visualization and reporting system for William Blake's works.
Provides interactive dashboards, advanced visualizations, and automated reporting.
"""

from .engines.visualization_engine import VisualizationEngine
from .engines.data_processor import DataProcessor
from .integrations.blake_viz_integration import BlakeVizIntegration

# Renderers
from .renderers.text_renderer import TextRenderer
from .renderers.image_renderer import ImageRenderer
from .renderers.temporal_renderer import TemporalRenderer
from .renderers.network_renderer import NetworkRenderer
from .renderers.comparative_renderer import ComparativeRenderer

# Dashboards
from .dashboards.research_dashboard import ResearchDashboard
from .dashboards.educational_dashboard import EducationalDashboard
from .dashboards.public_dashboard import PublicDashboard
from .dashboards.dashboard_manager import DashboardManager

# Reports
from .reports.report_generator import ReportGenerator
from .reports.custom_report_builder import CustomReportBuilder

# Models
from .models import (
    VisualizationConfig, DashboardComponent, InteractiveDashboard,
    Visualization, Report, ReportTemplate, ReportSection
)

__version__ = "1.0.0"
__all__ = [
    # Core engines
    'VisualizationEngine',
    'DataProcessor',
    'BlakeVizIntegration',
    
    # Renderers
    'TextRenderer',
    'ImageRenderer', 
    'TemporalRenderer',
    'NetworkRenderer',
    'ComparativeRenderer',
    
    # Dashboards
    'ResearchDashboard',
    'EducationalDashboard',
    'PublicDashboard',
    'DashboardManager',
    
    # Reports
    'ReportGenerator',
    'CustomReportBuilder',
    
    # Models
    'VisualizationConfig',
    'DashboardComponent',
    'InteractiveDashboard',
    'Visualization',
    'Report',
    'ReportTemplate',
    'ReportSection'
]

