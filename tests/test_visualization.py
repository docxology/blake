"""
Tests for Blake visualization system.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from blake.viz.engines.visualization_engine import VisualizationEngine
from blake.viz.engines.data_processor import DataProcessor
from blake.viz.models import (
    VisualizationConfig, VisualizationType, TextData, ImageData, 
    TemporalData, NetworkData
)
from blake.viz.renderers.text_renderer import TextRenderer
from blake.viz.renderers.image_renderer import ImageRenderer
from blake.viz.renderers.temporal_renderer import TemporalRenderer
from blake.viz.renderers.network_renderer import NetworkRenderer
from blake.viz.renderers.comparative_renderer import ComparativeRenderer
from blake.viz.dashboards import (
    ResearchDashboard, EducationalDashboard, PublicDashboard, DashboardManager
)
from blake.viz.reports import (
    ReportGenerator, CustomReportBuilder
)
from blake.viz.integrations.blake_viz_integration import BlakeVizIntegration


class TestDataProcessor:
    """Test data processor functionality."""
    
    @pytest.fixture
    def data_processor(self):
        """Create data processor instance."""
        data_dir = Path("./test_data")
        return DataProcessor(data_dir)
    
    @pytest.fixture
    def mock_works(self):
        """Create mock BlakeWork objects."""
        from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType
        
        works = []
        for i in range(3):
            metadata = BlakeMetadata(
                id=f"work_{i}",
                title=f"Test Work {i}",
                work_type=WorkType.POEM,
                source=SourceType.PROJECT_GUTENBERG
            )
            
            work = BlakeWork(
                id=f"work_{i}",
                metadata=metadata,
                text_content=f"This is test work {i} with some content for analysis."
            )
            works.append(work)
        
        return works
    
    @pytest.mark.asyncio
    async def test_prepare_text_data(self, data_processor, mock_works):
        """Test text data preparation."""
        text_data = await data_processor.prepare_text_data(mock_works)
        
        assert isinstance(text_data, TextData)
        assert len(text_data.texts) == 3
        assert len(text_data.metadata) == 3
        assert text_data.avg_word_length > 0
        assert text_data.avg_sentence_length > 0
        assert text_data.vocabulary_richness > 0
    
    @pytest.mark.asyncio
    async def test_prepare_image_data(self, data_processor, mock_works):
        """Test image data preparation."""
        image_data = await data_processor.prepare_image_data(mock_works)
        
        assert isinstance(image_data, ImageData)
        assert len(image_data.images) == 0  # No images in mock works
        assert len(image_data.metadata) == 0
    
    @pytest.mark.asyncio
    async def test_prepare_temporal_data(self, data_processor, mock_works):
        """Test temporal data preparation."""
        temporal_data = await data_processor.prepare_temporal_data(mock_works)
        
        assert isinstance(temporal_data, TemporalData)
        assert len(temporal_data.works) == 3
        assert len(temporal_data.dates) == 3  # Default dates assigned
        assert len(temporal_data.timeline_points) == 3  # Timeline points created
    
    @pytest.mark.asyncio
    async def test_prepare_network_data(self, data_processor, mock_works):
        """Test network data preparation."""
        network_data = await data_processor.prepare_network_data(mock_works)
        
        assert isinstance(network_data, NetworkData)
        assert len(network_data.nodes) == 3
        assert len(network_data.edges) == 0  # No theme overlap in mock works


class TestVisualizationEngine:
    """Test visualization engine functionality."""
    
    @pytest.fixture
    def visualization_engine(self):
        """Create visualization engine instance."""
        data_dir = Path("./test_data")
        return VisualizationEngine(data_dir)
    
    @pytest.fixture
    def mock_text_data(self):
        """Create mock text data."""
        return TextData(
            texts=["Test text 1", "Test text 2"],
            metadata=[{"work_id": "1", "title": "Work 1"}, {"work_id": "2", "title": "Work 2"}],
            word_frequencies={"test": 2, "text": 2},
            sentiment_scores=[0.1, -0.1],
            topics=["topic1", "topic2"],
            entities=[{"text": "entity1"}, {"text": "entity2"}],
            avg_word_length=4.5,
            avg_sentence_length=8.0,
            vocabulary_richness=0.8
        )
    
    @pytest.mark.asyncio
    async def test_create_visualization(self, visualization_engine, mock_text_data):
        """Test visualization creation."""
        # Use string viz_type, not enum
        result = await visualization_engine.create_visualization(
            "word_cloud", mock_text_data, None
        )
        
        assert result is not None
        assert result.get('type') == 'word_cloud'
    
    @pytest.mark.asyncio
    async def test_get_available_visualizations(self, visualization_engine):
        """Test getting available visualizations - async method."""
        visualizations = await visualization_engine.get_available_visualizations()
        
        assert isinstance(visualizations, list)
        assert len(visualizations) > 0
        # Check structure
        for viz in visualizations:
            assert 'type' in viz
            assert 'category' in viz


class TestTextVisualizations:
    """Test text visualization components using TextRenderer."""
    
    @pytest.fixture
    def text_renderer(self):
        """Create text renderer instance."""
        return TextRenderer()
    
    @pytest.fixture
    def mock_text_data(self):
        """Create mock text data."""
        return TextData(
            texts=["Test text for analysis", "Another test text"],
            metadata=[{"work_id": "1", "title": "Work 1", "creation_date": "1800-01-01"}],
            word_frequencies={"test": 2, "text": 2, "analysis": 1},
            sentiment_scores=[0.1, -0.1],
            topics=["topic1"],
            entities=[],
            avg_word_length=4.0,
            avg_sentence_length=6.0,
            vocabulary_richness=0.7
        )
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config using the engine's VisualizationConfig."""
        from blake.viz.engines.visualization_engine import VisualizationConfig as EngineConfig
        return EngineConfig(
            viz_type='word_cloud',
            title='Test Word Cloud',
            data_source='test_data'
        )
    
    @pytest.mark.asyncio
    async def test_word_cloud_visualization(self, text_renderer, mock_text_data, mock_config):
        """Test word cloud visualization creation."""
        result = await text_renderer.render_word_cloud(mock_text_data, mock_config)
        assert result is not None
        assert result.get('type') == 'word_cloud'
    
    @pytest.mark.asyncio
    async def test_sentiment_timeline(self, text_renderer, mock_text_data, mock_config):
        """Test sentiment timeline creation."""
        mock_config.viz_type = 'sentiment_timeline'
        result = await text_renderer.render_sentiment_timeline(mock_text_data, mock_config)
        assert result is not None
        assert result.get('type') == 'sentiment_timeline'
    
    @pytest.mark.asyncio
    async def test_style_evolution(self, text_renderer, mock_text_data, mock_config):
        """Test style evolution creation."""
        mock_config.viz_type = 'style_evolution'
        result = await text_renderer.render_style_evolution(mock_text_data, mock_config)
        assert result is not None
        assert result.get('type') == 'style_evolution'


class TestImageVisualizations:
    """Test image visualization components using ImageRenderer."""
    
    @pytest.fixture
    def image_renderer(self):
        """Create image renderer instance."""
        return ImageRenderer()
    
    @pytest.fixture
    def mock_image_data(self):
        """Create mock image data with required width/height fields."""
        return ImageData(
            images=[
                {"image_id": "1", "work_id": "1", "title": "Image 1", "width": 800, "height": 600},
                {"image_id": "2", "work_id": "1", "title": "Image 2", "width": 800, "height": 600}
            ],
            metadata=[{"image_id": "1", "work_id": "1", "title": "Work 1"}],
            dominant_colors=[["#FF0000", "#00FF00"], ["#0000FF", "#FFFF00"]],
            color_histograms=[{"#FF0000": 10, "#00FF00": 5}],
            brightness_scores=[0.5, 0.6],
            contrast_scores=[0.7, 0.8],
            composition_scores=[{"rule_of_thirds": 0.8}, {"rule_of_thirds": 0.7}],
            golden_ratio_scores=[0.6, 0.5],
            similarity_matrix=[[1.0, 0.5], [0.5, 1.0]],
            clusters=[0, 1]
        )
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config using the engine's VisualizationConfig."""
        from blake.viz.engines.visualization_engine import VisualizationConfig as EngineConfig
        return EngineConfig(
            viz_type='color_palette',
            title='Test Color Palette',
            data_source='test_data'
        )
    
    @pytest.mark.asyncio
    async def test_color_palette(self, image_renderer, mock_image_data, mock_config):
        """Test color palette creation."""
        result = await image_renderer.render_color_palette(mock_image_data, mock_config)
        assert result is not None
        assert result.get('type') == 'color_palette'
    
    @pytest.mark.asyncio
    async def test_composition_grid(self, image_renderer, mock_image_data, mock_config):
        """Test composition grid creation - uses render_composition_analysis."""
        mock_config.viz_type = 'composition_analysis'
        result = await image_renderer.render_composition_analysis(mock_image_data, mock_config)
        assert result is not None
        assert result.get('type') == 'composition_analysis'
    
    @pytest.mark.asyncio
    async def test_similarity_network(self, image_renderer, mock_image_data, mock_config):
        """Test similarity network creation - uses render_image_similarity_network."""
        mock_config.viz_type = 'image_similarity_network'
        result = await image_renderer.render_image_similarity_network(mock_image_data, mock_config)
        assert result is not None
        assert result.get('type') == 'image_similarity_network'



class TestDashboardCreation:
    """Test dashboard creation functionality."""
    
    @pytest.fixture
    def research_dashboard(self):
        """Create research dashboard instance."""
        return ResearchDashboard()
    
    @pytest.fixture
    def educational_dashboard(self):
        """Create educational dashboard instance."""
        return EducationalDashboard()
    
    @pytest.fixture
    def public_dashboard(self):
        """Create public dashboard instance."""
        return PublicDashboard()
    
    @pytest.mark.asyncio
    async def test_research_dashboard_creation(self, research_dashboard):
        """Test research dashboard creation."""
        dashboard = await research_dashboard.create_dashboard()
        assert dashboard is not None
        assert len(dashboard.components) > 0
    
    @pytest.mark.asyncio
    async def test_educational_dashboard_creation(self, educational_dashboard):
        """Test educational dashboard creation."""
        dashboard = await educational_dashboard.create_dashboard()
        assert dashboard is not None
        assert len(dashboard.components) > 0
    
    @pytest.mark.asyncio
    async def test_public_dashboard_creation(self, public_dashboard):
        """Test public dashboard creation."""
        dashboard = await public_dashboard.create_dashboard(
            {
                "summary": {
                    "total_works": 12,
                    "total_images": 31,
                    "processed_works": 9,
                    "sources": {
                        "Blake Archive": 7,
                        "Project Gutenberg": 5,
                    },
                    "coverage_status": "partial",
                }
            }
        )
        assert dashboard is not None
        assert len(dashboard.components) > 0
        titles = [component.title for component in dashboard.components]
        assert "Social Sharing" not in titles
        assert "Source Coverage" in titles
        assert "Rights and Reuse" in titles
        assert dashboard.layout_config["summary"]["total_works"] == 12


class TestReportGeneration:
    """Test report generation functionality."""
    
    @pytest.fixture
    def report_generator(self):
        """Create report generator instance."""
        return ReportGenerator()
    
    @pytest.mark.asyncio
    async def test_research_report_generation(self, report_generator):
        """Test research report generation."""
        report = await report_generator.generate_research_report("comprehensive")
        assert report is not None
    
    @pytest.mark.asyncio
    async def test_educational_report_generation(self, report_generator):
        """Test educational report generation."""
        report = await report_generator.generate_educational_report("intermediate")
        assert report is not None
    
    @pytest.mark.asyncio
    async def test_public_report_generation(self, report_generator):
        """Test public report generation."""
        report = await report_generator.generate_public_report(
            summary={
                "total_works": 2,
                "total_images": 5,
                "processed_works": 2,
                "sources": {
                    "Blake Archive": 1,
                    "Project Gutenberg": 1,
                },
                "work_types": {
                    "poem": 2,
                },
                "coverage_status": "partial",
                "date_range": {
                    "earliest": "1789-01-01",
                    "latest": "1794-01-01",
                },
            },
            works=[
                {
                    "id": "songs-of-innocence",
                    "title": "Songs of Innocence",
                    "source": "Project Gutenberg",
                    "images": [{"id": "img-1"}],
                    "text_content": "text",
                },
                {
                    "id": "the-tyger",
                    "title": "The Tyger",
                    "source": "Blake Archive",
                    "images": [{"id": "img-2"}, {"id": "img-3"}],
                    "text_content": "text",
                },
            ],
        )
        assert report is not None
        assert report.title == "Public Corpus Snapshot"
        assert report.content["summary"]["total_works"] == 2
        assert report.content["summary"]["source_count"] == 2
        assert report.content["highlights"][0] == "Local corpus snapshot: 2 works and 5 images."
        assert report.content["visual_gallery"][0]["title"] == "Songs of Innocence"
        assert "rights-gated assets stay excluded" in " ".join(report.content["stories"]).lower()


class TestIntegration:
    """Test integration functionality."""
    
    @pytest.fixture
    def mock_blake_works(self):
        """Create mock BlakeWorks instance."""
        blake_works = Mock()
        blake_works.data_dir = Path("./test_data")
        blake_works.get_all_works = AsyncMock(return_value=[])
        blake_works.get_statistics = AsyncMock(return_value={"total_works": 0})
        return blake_works
    
    @pytest.fixture
    def viz_integration(self, mock_blake_works):
        """Create visualization integration instance."""
        return BlakeVizIntegration(mock_blake_works)
    
    @pytest.mark.asyncio
    async def test_get_available_visualizations(self, viz_integration):
        """Test getting available visualizations - async method."""
        visualizations = await viz_integration.get_available_visualizations()
        assert isinstance(visualizations, list)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, viz_integration):
        """Test getting dashboard summary - async method."""
        summary = await viz_integration.get_dashboard_summary()
        assert summary is not None
    
    def test_viz_integration_initialization(self, viz_integration):
        """Test visualization integration initialization."""
        assert viz_integration is not None
        assert viz_integration.visualization_engine is not None
        assert viz_integration.data_processor is not None


if __name__ == "__main__":
    pytest.main([__file__])
