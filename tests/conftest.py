"""
Pytest configuration and fixtures for Blake tests.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from blake.models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_metadata():
    """Create sample BlakeMetadata for testing."""
    return BlakeMetadata(
        id="test_work_1",
        title="Songs of Innocence",
        work_type=WorkType.POEM,
        source=SourceType.BLAKE_ARCHIVE,
        creation_date=None,
        description="A collection of poems about innocence",
        tags=["innocence", "poetry", "romantic"],
        themes=["innocence", "nature", "childhood"],
        subjects=["children", "animals", "nature"]
    )


@pytest.fixture
def sample_image():
    """Create sample BlakeImage for testing."""
    return BlakeImage(
        id="img_1",
        metadata_id="test_work_1",
        title="Title Page",
        file_path=Path("/test/image.jpg"),
        width=800,
        height=600,
        dominant_colors=["#FF0000", "#00FF00", "#0000FF"]
    )


@pytest.fixture
def sample_work(sample_metadata, sample_image):
    """Create sample BlakeWork for testing."""
    return BlakeWork(
        id="test_work_1",
        metadata=sample_metadata,
        text_content="Little lamb, who made thee?\nDost thou know who made thee?",
        images=[sample_image],
        text_analysis={
            'sentiment': {'sentiment': 'positive', 'compound_score': 0.8},
            'basic_stats': {'word_count': 12, 'sentence_count': 2}
        },
        visual_analysis={
            'img_1': {'colors': ['#FF0000', '#00FF00'], 'brightness': 0.7}
        },
        cross_analysis={
            'text_image_correlation': {'jaccard_similarity': 0.6}
        }
    )


@pytest.fixture
def mock_works(sample_work):
    """Create list of mock works for testing."""
    work2 = BlakeWork(
        id="test_work_2",
        metadata=BlakeMetadata(
            id="test_work_2",
            title="Songs of Experience",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            tags=["experience", "poetry", "romantic"],
            themes=["experience", "maturity", "wisdom"],
            subjects=["adults", "society", "corruption"]
        ),
        text_content="Tyger Tyger, burning bright\nIn the forests of the night"
    )
    
    return [sample_work, work2]


@pytest.fixture
def mock_downloader():
    """Create mock downloader for testing."""
    downloader = Mock()
    downloader.download_all = Mock(return_value=[])
    downloader.download_work = Mock(return_value=None)
    downloader.download_from_source = Mock(return_value=[])
    return downloader


@pytest.fixture
def mock_analyzer():
    """Create mock analyzer for testing."""
    analyzer = Mock()
    analyzer.analyze_work = Mock(return_value={})
    analyzer.analyze_multiple_works = Mock(return_value={})
    analyzer.compare_works = Mock(return_value={})
    return analyzer


@pytest.fixture
def mock_metadata_manager():
    """Create mock metadata manager for testing."""
    manager = Mock()
    manager.process_work = Mock(return_value=None)
    manager.save_work = Mock(return_value=None)
    manager.load_work = Mock(return_value=None)
    manager.load_all_works = Mock(return_value=[])
    manager.search_works = Mock(return_value=[])
    return manager


@pytest.fixture
def mock_exporter():
    """Create mock exporter for testing."""
    exporter = Mock()
    exporter.export_works = Mock(return_value=Path("/test/export"))
    exporter.export_work = Mock(return_value=Path("/test/export"))
    return exporter


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "download: marks tests that require downloading"
    )
    config.addinivalue_line(
        "markers", "analysis: marks tests that require analysis"
    )
    config.addinivalue_line(
        "markers", "gui: marks tests that require GUI components"
    )

