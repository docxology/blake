"""
Blake Visualization Integration

Integrates the visualization system with the main BlakeCorpus class.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..engines.visualization_engine import VisualizationEngine
from ..engines.data_processor import DataProcessor
from ..dashboards.dashboard_manager import DashboardManager
from ..reports.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class BlakeVizIntegration:
    """Integrates visualization system with BlakeCorpus."""
    
    def __init__(self, blake_works):
        """
        Initialize visualization integration.
        
        Args:
            blake_works: BlakeCorpus instance to integrate with
        """
        self.blake_works = blake_works
        self.data_dir = blake_works.data_dir
        
        # Initialize components
        self.data_processor = DataProcessor(self.data_dir)
        self.visualization_engine = VisualizationEngine(self.data_dir)
        self.dashboard_manager = DashboardManager()
        self.report_generator = ReportGenerator()
        
        logger.info("Initialized BlakeVizIntegration")
    
    async def create_visualization(
        self,
        viz_type: str,
        data_type: str = "all",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization.
        
        Args:
            viz_type: Type of visualization to create
            data_type: Type of data to visualize (text, image, temporal, network, comparative)
            config: Visualization configuration
            
        Returns:
            Visualization result
        """
        logger.info(f"Creating visualization: {viz_type} for {data_type} data")
        
        # Get works data
        works = await self.blake_works.get_all_works()
        if not works:
            return {"error": "No works available for visualization"}
        
        # Deduce data type if 'all'
        if data_type == "all":
            available_viz = await self.visualization_engine.get_available_visualizations()
            for viz in available_viz:
                if viz['type'] == viz_type:
                    data_type = viz['category']
                    break
        
        # Process data based on type
        if data_type == "text":
            data = await self.data_processor.prepare_text_data(works)
        elif data_type == "image":
            data = await self.data_processor.prepare_image_data(works)
        elif data_type == "temporal":
            data = await self.data_processor.prepare_temporal_data(works)
        elif data_type == "network":
            data = await self.data_processor.prepare_network_data(works)
        elif data_type == "comparative":
            # Comparative visualizations use dict data structure
            data = {
                "works": [{"work_id": w.id, "title": w.metadata.title} for w in works],
                "sources": list(set(w.metadata.source for w in works if w.metadata.source)),
                "metrics": [],
                "statistics": {"total_works": len(works)}
            }
        else:
            # Default to text data
            data = await self.data_processor.prepare_text_data(works)
        
        # Create visualization
        result = await self.visualization_engine.create_visualization(
            viz_type, data, config or {}
        )
        
        return result
    
    async def create_research_dashboard(self) -> Dict[str, Any]:
        """Create research dashboard."""
        logger.info("Creating research dashboard")
        
        dashboard = await self.dashboard_manager.create_dashboard("research")
        
        return {
            "dashboard": dashboard,
            "type": "research",
            "component_count": len(dashboard.components)
        }
    
    async def create_educational_dashboard(self) -> Dict[str, Any]:
        """Create educational dashboard."""
        logger.info("Creating educational dashboard")
        
        dashboard = await self.dashboard_manager.create_dashboard("educational")
        
        return {
            "dashboard": dashboard,
            "type": "educational",
            "component_count": len(dashboard.components)
        }
    
    async def create_public_dashboard(self) -> Dict[str, Any]:
        """Create public dashboard."""
        logger.info("Creating public dashboard")
        
        summary = await self.blake_works.get_statistics()
        dashboard = await self.dashboard_manager.create_dashboard(
            "public", {"summary": summary}
        )
        
        return {
            "dashboard": dashboard,
            "type": "public",
            "component_count": len(dashboard.components)
        }
    
    async def generate_research_report(self, focus: str = "comprehensive") -> Dict[str, Any]:
        """Generate research report."""
        logger.info(f"Generating research report with focus: {focus}")
        
        report = await self.report_generator.generate_research_report(focus)
        
        return {
            "report": report,
            "type": "research",
            "focus": focus
        }
    
    async def generate_educational_report(self, level: str = "intermediate") -> Dict[str, Any]:
        """Generate educational report."""
        logger.info(f"Generating educational report for level: {level}")
        
        report = await self.report_generator.generate_educational_report(level)
        
        return {
            "report": report,
            "type": "educational",
            "level": level
        }
    
    async def generate_public_report(self) -> Dict[str, Any]:
        """Generate public report."""
        logger.info("Generating public report")
        
        summary = await self.blake_works.get_statistics()
        works = await self.blake_works.get_all_works()
        report = await self.report_generator.generate_public_report(
            summary=summary, works=works
        )
        
        return {
            "report": report,
            "type": "public"
        }
    
    async def get_available_visualizations(self) -> List[Dict[str, Any]]:
        """Get list of available visualizations."""
        return await self.visualization_engine.get_available_visualizations()
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary of available dashboards."""
        return await self.dashboard_manager.get_dashboard_summary()
    
    async def get_visualization_statistics(self) -> Dict[str, Any]:
        """Get visualization statistics."""
        works = await self.blake_works.get_all_works()
        
        return {
            "total_works": len(works),
            "text_works": len([w for w in works if w.text_content]),
            "image_works": len([w for w in works if w.images]),
            "analyzed_works": len([w for w in works if w.text_analysis or w.visual_analysis]),
            "available_visualizations": len(await self.get_available_visualizations()),
            "available_dashboards": 3
        }
