"""
Comparative visualization renderer.

Handles all comparative visualizations including side-by-side comparisons,
parallel analysis, and cross-source comparisons.
"""

import logging
from typing import Dict, Any, List, Optional

from ..models import TextData, ImageData, TemporalData, NetworkData, VisualizationConfig

logger = logging.getLogger(__name__)


class ComparativeRenderer:
    """Renders comparative visualizations."""
    
    def __init__(self):
        """Initialize comparative renderer."""
        self.supported_types = [
            'side_by_side_comparison',
            'parallel_analysis',
            'source_comparison',
            'metadata_analysis'
        ]
        logger.info("Initialized ComparativeRenderer")
    
    async def render_side_by_side_comparison(self, data: Dict[str, Any], config: VisualizationConfig) -> Dict[str, Any]:
        """Render side-by-side comparison visualization."""
        logger.info("Rendering side-by-side comparison visualization")
        
        # Create comparison data
        comparison_data = {
            'left': data.get('left', {}),
            'right': data.get('right', {}),
            'differences': data.get('differences', []),
            'similarities': data.get('similarities', []),
            'config': {
                'title': config.get('title', 'Side-by-Side Comparison'),
                'width': config.get('width', 800),
                'height': config.get('height', 600)
            }
        }
        
        return {
            'type': 'side_by_side_comparison',
            'data': comparison_data,
            'metadata': {
                'renderer': 'ComparativeRenderer',
                'comparison_type': 'side_by_side'
            }
        }
    
    async def render_parallel_analysis(self, data: Dict[str, Any], config: VisualizationConfig) -> Dict[str, Any]:
        """Render parallel analysis visualization."""
        logger.info("Rendering parallel analysis visualization")
        
        # Create parallel analysis data
        parallel_data = {
            'dimensions': data.get('dimensions', []),
            'values': data.get('values', []),
            'correlations': data.get('correlations', []),
            'config': {
                'title': config.get('title', 'Parallel Analysis'),
                'width': config.get('width', 800),
                'height': config.get('height', 400)
            }
        }
        
        return {
            'type': 'parallel_analysis',
            'data': parallel_data,
            'metadata': {
                'renderer': 'ComparativeRenderer',
                'dimension_count': len(parallel_data['dimensions'])
            }
        }
    
    async def render_source_comparison(self, data: Dict[str, Any], config: VisualizationConfig) -> Dict[str, Any]:
        """Render source comparison visualization."""
        logger.info("Rendering source comparison visualization")
        
        # Create source comparison data
        source_data = {
            'sources': data.get('sources', []),
            'metrics': data.get('metrics', []),
            'comparisons': data.get('comparisons', []),
            'config': {
                'title': config.get('title', 'Source Comparison'),
                'width': config.get('width', 800),
                'height': config.get('height', 400)
            }
        }
        
        return {
            'type': 'source_comparison',
            'data': source_data,
            'metadata': {
                'renderer': 'ComparativeRenderer',
                'source_count': len(source_data['sources'])
            }
        }
    
    async def render_metadata_analysis(self, data: Dict[str, Any], config: VisualizationConfig) -> Dict[str, Any]:
        """Render metadata analysis visualization."""
        logger.info("Rendering metadata analysis visualization")
        
        # Create metadata analysis data
        metadata_data = {
            'fields': data.get('fields', []),
            'values': data.get('values', []),
            'statistics': data.get('statistics', {}),
            'config': {
                'title': config.get('title', 'Metadata Analysis'),
                'width': config.get('width', 800),
                'height': config.get('height', 400)
            }
        }
        
        return {
            'type': 'metadata_analysis',
            'data': metadata_data,
            'metadata': {
                'renderer': 'ComparativeRenderer',
                'field_count': len(metadata_data['fields'])
            }
        }
    
    async def render(self, viz_type: str, data: Dict[str, Any], config: VisualizationConfig) -> Dict[str, Any]:
        """Render visualization based on type."""
        if viz_type not in self.supported_types:
            raise ValueError(f"Unsupported visualization type: {viz_type}")
        
        render_method = getattr(self, f'render_{viz_type}', None)
        if not render_method:
            raise ValueError(f"Renderer method not found for type: {viz_type}")
        
        return await render_method(data, config)
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported visualization types."""
        return self.supported_types.copy()

