"""
Data models for visualization and reporting.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Tuple
from pathlib import Path
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class VisualizationType(str, Enum):
    """Types of visualizations."""
    WORD_CLOUD = "word_cloud"
    FREQUENCY_CHART = "frequency_chart"
    SENTIMENT_TIMELINE = "sentiment_timeline"
    SENTIMENT_HEATMAP = "sentiment_heatmap"
    STYLE_EVOLUTION = "style_evolution"
    STYLE_COMPARISON = "style_comparison"
    COLOR_PALETTE = "color_palette"
    COLOR_EVOLUTION = "color_evolution"
    COLOR_HEATMAP = "color_heatmap"
    COMPOSITION_GRID = "composition_grid"
    GOLDEN_RATIO_ANALYSIS = "golden_ratio_analysis"
    SIMILARITY_NETWORK = "similarity_network"
    CLUSTERING_VISUALIZATION = "clustering_visualization"
    WORK_TIMELINE = "work_timeline"
    THEME_EVOLUTION = "theme_evolution"
    CREATIVE_PERIODS = "creative_periods"
    CHRONOLOGICAL_NETWORK = "chronological_network"
    DEVELOPMENT_PHASES = "development_phases"
    THEME_NETWORK = "theme_network"
    CONCEPT_MAP = "concept_map"
    INFLUENCE_NETWORK = "influence_network"
    CITATION_NETWORK = "citation_network"
    SIDE_BY_SIDE_COMPARISON = "side_by_side_comparison"
    PARALLEL_ANALYSIS = "parallel_analysis"
    SOURCE_COMPARISON = "source_comparison"
    METADATA_ANALYSIS = "metadata_analysis"


class RendererType(str, Enum):
    """Types of visualization renderers."""
    TEXT = "text"
    IMAGE = "image"
    TEMPORAL = "temporal"
    NETWORK = "network"
    COMPARATIVE = "comparative"


class DashboardType(str, Enum):
    """Types of dashboards."""
    RESEARCH = "research"
    EDUCATIONAL = "educational"
    PUBLIC = "public"


class ReportType(str, Enum):
    """Types of reports."""
    RESEARCH = "research"
    EDUCATIONAL = "educational"
    PUBLIC = "public"
    CUSTOM = "custom"


class VisualizationConfig(BaseModel):
    """Configuration for visualizations."""
    
    viz_type: VisualizationType = Field(..., description="Type of visualization")
    title: str = Field("", description="Visualization title")
    description: Optional[str] = Field(None, description="Visualization description")
    
    # Data configuration
    data_source: str = Field("all_works", description="Data source identifier")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Data filters")
    
    # Visual configuration
    width: int = Field(800, description="Visualization width")
    height: int = Field(600, description="Visualization height")
    theme: str = Field("default", description="Visual theme")
    color_scheme: Optional[str] = Field(None, description="Color scheme")
    layout: Optional[str] = Field(None, description="Layout type")
    output_path: Optional[Path] = Field(None, description="Output file path")
    metrics: Optional[List[str]] = Field(None, description="Metrics to render")
    views: Optional[List[str]] = Field(None, description="Views to render")
    granularity: Optional[str] = Field(None, description="Temporal granularity")
    formats: Optional[List[str]] = Field(None, description="Output formats")
    features: Optional[List[str]] = Field(None, description="Enabled features")
    levels: Optional[List[str]] = Field(None, description="Supported audience levels")
    topics: Optional[List[str]] = Field(None, description="Supported learning topics")
    types: Optional[List[str]] = Field(None, description="Supported activity types")
    modes: Optional[List[str]] = Field(None, description="Supported exploration modes")
    curation: Optional[str] = Field(None, description="Curation strategy")
    update_frequency: Optional[str] = Field(None, description="Suggested update cadence")
    narrative: bool = Field(False, description="Enable narrative framing")
    multimedia: bool = Field(False, description="Enable multimedia content")
    platforms: Optional[List[str]] = Field(None, description="Target sharing platforms")
    responsive: bool = Field(False, description="Enable responsive layout behavior")
    touch_friendly: bool = Field(False, description="Enable touch-friendly controls")
    max_words: Optional[int] = Field(None, description="Maximum words")
    
    # Interactive features
    interactive: bool = Field(True, description="Enable interactivity")
    zoomable: bool = Field(True, description="Enable zooming")
    pannable: bool = Field(True, description="Enable panning")
    filterable: bool = Field(True, description="Enable filtering")
    
    # Export options
    export_formats: List[str] = Field(default_factory=lambda: ["png", "svg"], description="Export formats")
    
    # Performance settings
    max_data_points: Optional[int] = Field(None, description="Maximum data points")
    cache_enabled: bool = Field(True, description="Enable caching")
    
    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method for compatibility with renderer code."""
        return getattr(self, key, default)


class DataConfig(BaseModel):
    """Configuration for data processing."""
    
    # Text data configuration
    text_preprocessing: Dict[str, Any] = Field(default_factory=dict, description="Text preprocessing options")
    nlp_models: List[str] = Field(default_factory=lambda: ["spacy", "nltk"], description="NLP models to use")
    
    # Image data configuration
    image_processing: Dict[str, Any] = Field(default_factory=dict, description="Image processing options")
    color_analysis: Dict[str, Any] = Field(default_factory=dict, description="Color analysis options")
    
    # Temporal data configuration
    date_format: str = Field("%Y-%m-%d", description="Date format")
    time_granularity: str = Field("year", description="Time granularity")
    
    # Network data configuration
    similarity_threshold: float = Field(0.5, description="Similarity threshold")
    max_connections: int = Field(100, description="Maximum connections per node")
    
    model_config = ConfigDict(use_enum_values=True)


class DashboardComponent(BaseModel):
    """A component in a dashboard."""
    
    id: str = Field(..., description="Component ID")
    component_type: str = Field(..., description="Type of component")
    title: str = Field(..., description="Component title")
    description: Optional[str] = Field(None, description="Component description")
    
    # Position and size
    x: int = Field(0, description="X position")
    y: int = Field(0, description="Y position")
    width: int = Field(400, description="Component width")
    height: int = Field(300, description="Component height")
    
    # Configuration
    config: VisualizationConfig = Field(..., description="Visualization configuration")
    data_source: str = Field(..., description="Data source")
    
    # Relationships
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    triggers: List[str] = Field(default_factory=list, description="Component triggers")
    
    model_config = ConfigDict(use_enum_values=True)


class InteractiveDashboard(BaseModel):
    """An interactive dashboard."""
    
    id: str = Field(..., description="Dashboard ID")
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    dashboard_type: DashboardType = Field(..., description="Type of dashboard")
    
    # Layout
    components: List[DashboardComponent] = Field(..., description="Dashboard components")
    layout_config: Dict[str, Any] = Field(default_factory=dict, description="Layout configuration")
    
    # Settings
    auto_refresh: bool = Field(False, description="Auto-refresh enabled")
    refresh_interval: int = Field(300, description="Refresh interval in seconds")
    theme: str = Field("default", description="Dashboard theme")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    created_by: Optional[str] = Field(None, description="Creator")
    
    model_config = ConfigDict(use_enum_values=True)


class Visualization(BaseModel):
    """A visualization instance."""
    
    id: str = Field(..., description="Visualization ID")
    config: VisualizationConfig = Field(..., description="Visualization configuration")
    
    # Data
    data: Dict[str, Any] = Field(..., description="Visualization data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Visualization metadata")
    
    # Rendering
    renderer_type: RendererType = Field(..., description="Renderer type")
    rendered_data: Optional[Dict[str, Any]] = Field(None, description="Rendered visualization data")
    
    # Performance
    render_time: Optional[float] = Field(None, description="Render time in seconds")
    data_size: Optional[int] = Field(None, description="Data size in bytes")
    
    # Status
    status: str = Field("pending", description="Visualization status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    model_config = ConfigDict(use_enum_values=True)


class ReportSection(BaseModel):
    """A section in a report."""
    
    id: str = Field(..., description="Section ID")
    title: str = Field(..., description="Section title")
    content_type: str = Field(..., description="Type of content")
    content: Dict[str, Any] = Field(..., description="Section content")
    order: int = Field(0, description="Section order")
    
    # Visualizations
    visualizations: List[str] = Field(default_factory=list, description="Visualization IDs")
    
    model_config = ConfigDict(use_enum_values=True)


class ReportTemplate(BaseModel):
    """A report template."""
    
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    report_type: ReportType = Field(..., description="Report type")
    
    # Structure
    sections: List[ReportSection] = Field(..., description="Report sections")
    
    # Styling
    style_config: Dict[str, Any] = Field(default_factory=dict, description="Style configuration")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    created_by: Optional[str] = Field(None, description="Creator")
    
    model_config = ConfigDict(use_enum_values=True)


class Report(BaseModel):
    """A generated report."""
    
    id: str = Field(..., description="Report ID")
    template: ReportTemplate = Field(..., description="Report template")
    title: str = Field(..., description="Report title")
    
    # Content
    content: Dict[str, Any] = Field(..., description="Report content")
    visualizations: List[Visualization] = Field(default_factory=list, description="Report visualizations")
    
    # Export
    export_path: Optional[Path] = Field(None, description="Export path")
    export_formats: List[str] = Field(default_factory=lambda: ["pdf"], description="Export formats")
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation time")
    generated_by: Optional[str] = Field(None, description="Generator")
    
    model_config = ConfigDict(use_enum_values=True)


class TextData(BaseModel):
    """Processed text data for visualization."""
    
    texts: List[str] = Field(..., description="Text content")
    metadata: List[Dict[str, Any]] = Field(..., description="Text metadata")
    
    # Analysis results
    word_frequencies: Dict[str, int] = Field(default_factory=dict, description="Word frequencies")
    sentiment_scores: List[float] = Field(default_factory=list, description="Sentiment scores")
    topics: List[str] = Field(default_factory=list, description="Identified topics")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Named entities")
    
    # Stylistic features
    avg_word_length: float = Field(0.0, description="Average word length")
    avg_sentence_length: float = Field(0.0, description="Average sentence length")
    vocabulary_richness: float = Field(0.0, description="Vocabulary richness")
    
    model_config = ConfigDict(use_enum_values=True)


class ImageData(BaseModel):
    """Processed image data for visualization."""
    
    images: List[Dict[str, Any]] = Field(..., description="Image data")
    metadata: List[Dict[str, Any]] = Field(..., description="Image metadata")
    
    # Color analysis
    dominant_colors: List[List[str]] = Field(default_factory=list, description="Dominant colors per image")
    color_histograms: List[Dict[str, int]] = Field(default_factory=list, description="Color histograms")
    brightness_scores: List[float] = Field(default_factory=list, description="Brightness scores")
    contrast_scores: List[float] = Field(default_factory=list, description="Contrast scores")
    
    # Composition analysis
    composition_scores: List[Dict[str, float]] = Field(default_factory=list, description="Composition scores")
    golden_ratio_scores: List[float] = Field(default_factory=list, description="Golden ratio scores")
    
    # Similarity data
    similarity_matrix: List[List[float]] = Field(default_factory=list, description="Image similarity matrix")
    clusters: List[int] = Field(default_factory=list, description="Image cluster assignments")
    
    model_config = ConfigDict(use_enum_values=True)


class TemporalData(BaseModel):
    """Processed temporal data for visualization."""
    
    works: List[Dict[str, Any]] = Field(..., description="Work data")
    dates: List[datetime] = Field(..., description="Work dates")
    
    # Timeline data
    timeline_points: List[Dict[str, Any]] = Field(default_factory=list, description="Timeline points")
    periods: List[Dict[str, Any]] = Field(default_factory=list, description="Creative periods")
    
    # Evolution data
    theme_evolution: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Theme evolution")
    style_evolution: List[Dict[str, Any]] = Field(default_factory=list, description="Style evolution")
    
    model_config = ConfigDict(use_enum_values=True)


class NetworkData(BaseModel):
    """Processed network data for visualization."""
    
    nodes: List[Dict[str, Any]] = Field(..., description="Network nodes")
    edges: List[Dict[str, Any]] = Field(..., description="Network edges")
    
    # Network properties
    node_degrees: List[int] = Field(default_factory=list, description="Node degrees")
    clustering_coefficients: List[float] = Field(default_factory=list, description="Clustering coefficients")
    centrality_scores: Dict[str, List[float]] = Field(default_factory=dict, description="Centrality scores")
    
    # Layout data
    positions: Dict[str, Tuple[float, float]] = Field(default_factory=dict, description="Node positions")
    communities: List[int] = Field(default_factory=list, description="Community assignments")
    
    model_config = ConfigDict(use_enum_values=True)
