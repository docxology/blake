"""
Core visualization engine for creating and managing visualizations.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import hashlib

from ...models import BlakeWork, BlakeImage
from ..models import (
    VisualizationConfig, TextData, ImageData, TemporalData, NetworkData
)
# Import renderers
from ..renderers.text_renderer import TextRenderer
from ..renderers.image_renderer import ImageRenderer
from ..renderers.temporal_renderer import TemporalRenderer
from ..renderers.network_renderer import NetworkRenderer
from ..renderers.comparative_renderer import ComparativeRenderer

logger = logging.getLogger(__name__)

class VisualizationEngine:
    """Core visualization engine for creating and managing visualizations."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize visualization engine.
        
        Args:
            data_dir: Directory containing Blake data
        """
        self.data_dir = data_dir
        self.cache_dir = data_dir / "visualization_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize renderers
        self.text_renderer = TextRenderer()
        self.image_renderer = ImageRenderer()
        self.temporal_renderer = TemporalRenderer()
        self.network_renderer = NetworkRenderer()
        self.comparative_renderer = ComparativeRenderer()
        
        logger.info(f"Initialized VisualizationEngine with data directory: {data_dir}")
    
    async def create_visualization(
        self,
        viz_type: str,
        data: Union[TextData, ImageData, TemporalData, NetworkData, Dict[str, Any]],
        config: Optional[VisualizationConfig] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization.
        
        Args:
            viz_type: Type of visualization to create
            data: Data to visualize
            config: Visualization configuration
            
        Returns:
            Created visualization result
        """
        logger.info(f"Creating visualization: {viz_type}")
        
        # Check for comparative visualization types first (by viz_type)
        comparative_types = self.comparative_renderer.get_supported_types()
        if viz_type in comparative_types:
            renderer = self.comparative_renderer
        # Determine renderer based on data type
        elif isinstance(data, TextData):
            renderer = self.text_renderer
        elif isinstance(data, ImageData):
            renderer = self.image_renderer
        elif isinstance(data, TemporalData):
            renderer = self.temporal_renderer
        elif isinstance(data, NetworkData):
            renderer = self.network_renderer
        elif isinstance(data, dict):
            # Fallback to comparative renderer for raw dict data
            renderer = self.comparative_renderer
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Helper to ensure config is model
        if config is None:
            config = VisualizationConfig(viz_type=viz_type)
        elif isinstance(config, dict):
            # Ensure viz_type is set
            if 'viz_type' not in config:
                config['viz_type'] = viz_type
            config = VisualizationConfig(**config)
            
        # Create visualization
        result = await renderer.render(viz_type, data, config)
        
        return result
    
    async def get_available_visualizations(self) -> List[Dict[str, Any]]:
        """Get list of available visualizations."""
        visualizations = []
        
        # Text visualizations
        for viz_type in self.text_renderer.get_supported_types():
            visualizations.append({
                "type": viz_type,
                "category": "text",
                "description": f"Text-based {viz_type.replace('_', ' ')} visualization"
            })
        
        # Image visualizations
        for viz_type in self.image_renderer.get_supported_types():
            visualizations.append({
                "type": viz_type,
                "category": "image",
                "description": f"Image-based {viz_type.replace('_', ' ')} visualization"
            })
        
        # Temporal visualizations
        for viz_type in self.temporal_renderer.get_supported_types():
            visualizations.append({
                "type": viz_type,
                "category": "temporal",
                "description": f"Temporal {viz_type.replace('_', ' ')} visualization"
            })
        
        # Network visualizations
        for viz_type in self.network_renderer.get_supported_types():
            visualizations.append({
                "type": viz_type,
                "category": "network",
                "description": f"Network {viz_type.replace('_', ' ')} visualization"
            })
        
        # Comparative visualizations
        for viz_type in self.comparative_renderer.get_supported_types():
            visualizations.append({
                "type": viz_type,
                "category": "comparative",
                "description": f"Comparative {viz_type.replace('_', ' ')} visualization"
            })
        
        return visualizations
