"""
Custom Report Builder

Allows users to create custom reports with flexible configurations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import Report, ReportTemplate, ReportSection

logger = logging.getLogger(__name__)


class CustomReportBuilder:
    """Builds custom reports with user-defined configurations."""
    
    def __init__(self):
        """Initialize custom report builder."""
        logger.info("Initialized CustomReportBuilder")
    
    async def create_custom_template(
        self,
        template_id: str,
        name: str,
        description: str,
        sections: List[Dict[str, Any]]
    ) -> ReportTemplate:
        """Create custom report template."""
        logger.info(f"Creating custom template: {template_id}")
        
        # Convert section dictionaries to ReportSection objects
        report_sections = []
        for section_data in sections:
            section = ReportSection(
                id=section_data["id"],
                title=section_data["title"],
                type=section_data["type"],
                required=section_data.get("required", False),
                config=section_data.get("config", {})
            )
            report_sections.append(section)
        
        return ReportTemplate(
            id=template_id,
            name=name,
            description=description,
            sections=report_sections
        )
    
    async def build_custom_report(
        self,
        template: ReportTemplate,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Report:
        """Build custom report from template and content."""
        logger.info(f"Building custom report from template: {template.id}")
        
        # Validate content against template sections
        self._validate_content(template, content)
        
        return Report(
            id=f"custom_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=template.name,
            template_id=template.id,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _validate_content(self, template: ReportTemplate, content: Dict[str, Any]) -> None:
        """Validate content against template requirements."""
        for section in template.sections:
            if section.required and section.id not in content:
                raise ValueError(f"Required section '{section.id}' missing from content")
    
    async def get_section_types(self) -> List[str]:
        """Get available section types."""
        return [
            "text",
            "analysis", 
            "visualization",
            "works",
            "themes",
            "highlights",
            "gallery",
            "stories",
            "activities"
        ]
    
    async def create_section_config(
        self,
        section_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create configuration for specific section type."""
        base_configs = {
            "text": {
                "format": "markdown",
                "max_length": 10000
            },
            "analysis": {
                "metrics": ["sentiment", "frequency", "similarity"],
                "visualization": True
            },
            "visualization": {
                "types": ["chart", "graph", "timeline"],
                "interactive": True
            },
            "works": {
                "max_works": 50,
                "include_metadata": True
            },
            "themes": {
                "max_themes": 20,
                "include_examples": True
            },
            "highlights": {
                "max_highlights": 10,
                "include_images": True
            },
            "gallery": {
                "max_images": 25,
                "include_captions": True
            },
            "stories": {
                "max_stories": 5,
                "include_multimedia": True
            },
            "activities": {
                "max_activities": 10,
                "include_instructions": True
            }
        }
        
        base_config = base_configs.get(section_type, {})
        if config:
            base_config.update(config)
        
        return base_config

