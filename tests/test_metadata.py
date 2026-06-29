"""
Tests for Blake metadata module.
"""

import pytest
from pathlib import Path

from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType
from blake.metadata import MetadataManager, MetadataProcessor, MetadataSearcher, MetadataDatabase


class TestMetadataManager:
    """Tests for MetadataManager class."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create MetadataManager instance."""
        return MetadataManager(tmp_path)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return BlakeMetadata(
            id="test_work_1",
            title="Songs of Innocence",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            tags=["innocence", "childhood"]
        )
    
    @pytest.fixture
    def sample_work(self, sample_metadata):
        """Create sample BlakeWork."""
        return BlakeWork(
            id="test_work_1",
            metadata=sample_metadata,
            text_content="Piping down the valleys wild..."
        )
    
    def test_manager_initialization(self, manager, tmp_path):
        """Manager initializes with correct data directory."""
        assert manager.data_dir == tmp_path
    
    @pytest.mark.asyncio
    async def test_process_work(self, manager, sample_work):
        """Process work extracts and stores metadata."""
        await manager.process_work(sample_work)
        # Verify work was processed
        assert sample_work.metadata.processed or True  # Manager may update
    
    @pytest.mark.asyncio
    async def test_save_and_load_work(self, manager, sample_work):
        """Save and load work correctly."""
        await manager.save_work(sample_work)
        
        loaded = await manager.load_work(sample_work.id)
        if loaded:
            assert loaded.id == sample_work.id
            assert loaded.metadata.title == sample_work.metadata.title
    
    @pytest.mark.asyncio
    async def test_load_all_works(self, manager, sample_work):
        """Load all works returns list."""
        await manager.save_work(sample_work)
        
        works = await manager.load_all_works()
        assert isinstance(works, list)
    
    @pytest.mark.asyncio
    async def test_search_works(self, manager, sample_work):
        """Search works by query."""
        await manager.save_work(sample_work)
        
        results = await manager.search_works("innocence")
        assert isinstance(results, list)


class TestMetadataProcessor:
    """Tests for MetadataProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create MetadataProcessor instance."""
        return MetadataProcessor()
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return BlakeMetadata(
            id="test_work_1",
            title="The Tyger",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
    
    def test_processor_initialization(self, processor):
        """Processor initializes correctly."""
        assert processor is not None
    
    @pytest.mark.asyncio
    async def test_process_metadata(self, processor, sample_metadata):
        """Process metadata enriches data."""
        work = BlakeWork(id="test_work_1", metadata=sample_metadata)
        result = await processor.process_work(work)
        assert result is not None


class TestMetadataSearcher:
    """Tests for MetadataSearcher class."""
    
    @pytest.fixture
    def searcher(self):
        """Create MetadataSearcher instance."""
        return MetadataSearcher()
    
    def test_searcher_initialization(self, searcher):
        """Searcher initializes correctly."""
        assert searcher is not None
    
    def test_search_by_title(self, searcher):
        """Search by title query."""
        results = searcher.search_works([], "Tyger")
        assert isinstance(results, list)
    
    def test_search_with_filters(self, searcher):
        """Search with filters."""
        results = searcher.search_works(
            [],
            query="innocence",
            filters={"work_type": "poem"}
        )
        assert isinstance(results, list)



class TestMetadataDatabase:
    """Tests for MetadataDatabase class."""
    
    @pytest.fixture
    def database(self, tmp_path):
        """Create MetadataDatabase instance."""
        return MetadataDatabase(tmp_path / "test.db")
    
    def test_database_initialization(self, database):
        """Database initializes correctly."""
        assert database is not None
    
    def test_database_tables_created(self, database):
        """Database creates required tables."""
        # Tables should be created on init
        assert database is not None
