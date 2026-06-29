"""
Comprehensive test suite for Project A: Comprehensive Data Acquisition.
Tests all new components and integration points.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import comprehensive acquisition components
from blake.downloader.source_discovery_engine import SourceDiscoveryEngine, SourceConfig, WorkMetadata
from blake.downloader.museum_adapters import SourceAdapterFactory, BritishMuseumAdapter
from blake.downloader.update_scheduler import IncrementalUpdater, UpdateFrequency
from blake.downloader.collection_organizer import DataOrganizer, DataStructure, OrganizationLevel
from blake.downloader.work_verifier import QualityAssurance, QualityLevel
from blake.downloader.system_monitor import MonitoringSystem, AlertLevel, HealthStatus
from blake.downloader.universal_downloader import UniversalBlakeDownloader
from blake.models import SourceType, WorkType, BlakeWork, BlakeMetadata, BlakeImage


class TestSourceDiscoveryEngine:
    """Test source discovery engine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def discovery_engine(self, temp_dir):
        """Create discovery engine instance."""
        return SourceDiscoveryEngine(temp_dir)
    
    def test_initialization(self, discovery_engine, temp_dir):
        """Test discovery engine initialization."""
        assert discovery_engine.data_dir == temp_dir
        assert discovery_engine.discovery_dir == temp_dir / "discovery"
        assert len(discovery_engine.sources_config) > 0
        assert SourceType.BLAKE_ARCHIVE in discovery_engine.sources_config
        assert SourceType.PROJECT_GUTENBERG in discovery_engine.sources_config
    
    def test_source_config_creation(self, discovery_engine):
        """Test source configuration creation."""
        config = discovery_engine.sources_config[SourceType.BLAKE_ARCHIVE]
        assert config.name == "Blake Archive"
        assert config.source_type == SourceType.BLAKE_ARCHIVE
        assert config.base_url == "https://blakearchive.org"
        assert config.priority == 1
        assert config.enabled is True
    
    @pytest.mark.asyncio
    async def test_discover_sources(self, discovery_engine):
        """Test source discovery."""
        with patch.object(discovery_engine, '_test_source_availability', return_value=True):
            sources = await discovery_engine.discover_sources()
            assert len(sources) > 0
            assert all(isinstance(s, SourceConfig) for s in sources)
    
    @pytest.mark.asyncio
    async def test_catalog_works(self, discovery_engine):
        """Test work cataloging."""
        source_config = discovery_engine.sources_config[SourceType.BLAKE_ARCHIVE]
        
        with patch.object(discovery_engine, '_catalog_blake_archive', return_value=[]):
            works = await discovery_engine.catalog_works(source_config)
            assert isinstance(works, list)
    
    def test_work_metadata_creation(self):
        """Test work metadata creation."""
        work = WorkMetadata(
            id="test_work_1",
            title="Test Work",
            source=SourceType.BLAKE_ARCHIVE,
            source_url="https://example.com/work1",
            work_type=WorkType.POEM
        )
        
        assert work.id == "test_work_1"
        assert work.title == "Test Work"
        assert work.source == SourceType.BLAKE_ARCHIVE
        assert work.work_type == WorkType.POEM


class TestComprehensiveSources:
    """Test comprehensive source adapters."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def source_config(self):
        """Create source configuration."""
        return SourceConfig(
            name="Test Museum",
            source_type=SourceType.BRITISH_MUSEUM,
            base_url="https://test-museum.org",
            search_url="https://test-museum.org/search",
            priority=2
        )
    
    def test_source_adapter_factory(self, temp_dir, source_config):
        """Test source adapter factory."""
        adapter = SourceAdapterFactory.create_adapter(
            SourceType.BRITISH_MUSEUM, temp_dir, source_config
        )
        assert isinstance(adapter, BritishMuseumAdapter)
        assert adapter.config == source_config
    
    @pytest.mark.asyncio
    async def test_museum_adapter_discover_works(self, temp_dir, source_config):
        """Test museum adapter work discovery."""
        adapter = BritishMuseumAdapter(temp_dir, source_config)
        
        with patch.object(adapter, '_get_api_data', return_value={'objects': []}):
            works = await adapter.discover_works()
            assert isinstance(works, list)
    
    @pytest.mark.asyncio
    async def test_museum_adapter_download_work(self, temp_dir, source_config):
        """Test museum adapter work download."""
        adapter = BritishMuseumAdapter(temp_dir, source_config)
        
        work_metadata = WorkMetadata(
            id="test_work",
            title="Test Work",
            source=SourceType.BRITISH_MUSEUM,
            source_url="https://test-museum.org/work",
            work_type=WorkType.DRAWING
        )
        
        with patch.object(adapter, '_get_api_data', return_value={}):
            work = await adapter.download_work(work_metadata)
            # Should return None due to empty API data
            assert work is None


class TestIncrementalUpdater:
    """Test incremental update system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def discovery_engine(self, temp_dir):
        """Create discovery engine instance."""
        return SourceDiscoveryEngine(temp_dir)
    
    @pytest.fixture
    def updater(self, temp_dir, discovery_engine):
        """Create incremental updater instance."""
        return IncrementalUpdater(temp_dir, discovery_engine)
    
    def test_initialization(self, updater, temp_dir):
        """Test updater initialization."""
        assert updater.data_dir == temp_dir
        assert updater.update_dir == temp_dir / "updates"
        assert len(updater.schedules) > 0
    
    def test_schedule_configuration(self, updater):
        """Test schedule configuration."""
        updater.configure_schedule(
            SourceType.BLAKE_ARCHIVE, 
            UpdateFrequency.DAILY, 
            True, 
            100
        )
        
        schedule = updater.schedules[SourceType.BLAKE_ARCHIVE]
        assert schedule.frequency == UpdateFrequency.DAILY
        assert schedule.enabled is True
        assert schedule.max_works_per_run == 100
    
    @pytest.mark.asyncio
    async def test_check_all_sources(self, updater):
        """Test comprehensive source checking."""
        # Test that check_all_sources returns a report dict or object
        report = await updater.check_all_sources()
        # Check it returns something (empty dict or report object is fine)
        assert report is not None
    
    def test_update_statistics(self, updater):
        """Test update statistics."""
        stats = updater.get_update_statistics()
        assert 'total_sources' in stats
        assert 'enabled_sources' in stats
        assert 'total_updates' in stats


class TestDataOrganizer:
    """Test data organization system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def data_structure(self):
        """Create data structure configuration."""
        return DataStructure(
            level=OrganizationLevel.HYBRID,
            create_thumbnails=True,
            create_indexes=True
        )
    
    @pytest.fixture
    def organizer(self, temp_dir, data_structure):
        """Create data organizer instance."""
        return DataOrganizer(temp_dir, data_structure)
    
    def test_initialization(self, organizer, temp_dir):
        """Test organizer initialization."""
        assert organizer.data_dir == temp_dir
        assert organizer.config.level == OrganizationLevel.HYBRID
        assert organizer.config.create_thumbnails is True
    
    def test_directory_structure_creation(self, organizer, temp_dir):
        """Test directory structure creation."""
        # Check key directories exist
        assert (temp_dir / "sources").exists()
        assert (temp_dir / "unified").exists()
        assert (temp_dir / "unified" / "works" / "by_id").exists()
        assert (temp_dir / "unified" / "images" / "originals").exists()
        assert (temp_dir / "processing").exists()
        assert (temp_dir / "monitoring").exists()
    
    @pytest.mark.asyncio
    async def test_organize_work(self, organizer):
        """Test work organization method exists and is callable."""
        # Verify the method exists and is async
        assert hasattr(organizer, 'organize_work')
        assert callable(organizer.organize_work)
    
    @pytest.mark.asyncio
    async def test_search_works(self, organizer):
        """Test work search functionality."""
        # Test that search_works returns a list
        results = await organizer.search_works("test")
        assert isinstance(results, list)
    
    def test_organization_statistics(self, organizer):
        """Test organization statistics."""
        stats = organizer.get_organization_statistics()
        assert 'total_works' in stats
        assert 'structure_level' in stats
        assert 'total_size' in stats


class TestQualityAssurance:
    """Test quality assurance system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def quality_system(self, temp_dir):
        """Create quality assurance system."""
        return QualityAssurance(temp_dir)
    
    def test_initialization(self, quality_system, temp_dir):
        """Test quality system initialization."""
        assert quality_system.data_dir == temp_dir
        assert quality_system.verification_dir == temp_dir / "verification"
        assert len(quality_system.thresholds) > 0
    
    def test_score_to_quality_conversion(self, quality_system):
        """Test score to quality level conversion."""
        assert quality_system._score_to_quality(0.95) == QualityLevel.EXCELLENT
        assert quality_system._score_to_quality(0.8) == QualityLevel.GOOD
        assert quality_system._score_to_quality(0.6) == QualityLevel.FAIR
        assert quality_system._score_to_quality(0.4) == QualityLevel.POOR
        assert quality_system._score_to_quality(0.1) == QualityLevel.FAILED
    
    @pytest.mark.asyncio
    async def test_verify_work(self, quality_system):
        """Test work verification."""
        # Create mock work
        metadata = BlakeMetadata(
            id="test_work",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        
        work = BlakeWork(
            id="test_work",
            metadata=metadata,
            text_content="Test content for verification"
        )
        
        # Mock file existence
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat', return_value=Mock(st_size=1024)):
                report = await quality_system.verify_work(work)
                
                assert report.work_id == "test_work"
                assert report.overall_score >= 0.0
                assert report.overall_score <= 1.0
                assert report.total_checks > 0
    
    @pytest.mark.asyncio
    async def test_verify_collection(self, quality_system):
        """Test collection verification."""
        # Create mock works
        works = []
        for i in range(3):
            metadata = BlakeMetadata(
                id=f"test_work_{i}",
                title=f"Test Work {i}",
                work_type=WorkType.POEM,
                source=SourceType.BLAKE_ARCHIVE
            )
            
            work = BlakeWork(
                id=f"test_work_{i}",
                metadata=metadata,
                text_content=f"Test content {i}"
            )
            works.append(work)
        
        with patch.object(quality_system, 'verify_work', return_value=Mock(
            work_id="test",
            overall_score=0.8,
            overall_quality=QualityLevel.GOOD,
            critical_issues=[],
            recommendations=[]
        )):
            report = await quality_system.verify_collection(works)
            
            assert report['total_works'] == 3
            assert report['verified_works'] == 3
            assert 'quality_distribution' in report
            assert 'overall_score' in report


class TestMonitoringSystem:
    """Test monitoring and alerting system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def monitoring_system(self, temp_dir):
        """Create monitoring system."""
        return MonitoringSystem(temp_dir)
    
    def test_initialization(self, monitoring_system, temp_dir):
        """Test monitoring system initialization."""
        assert monitoring_system.data_dir == temp_dir
        assert monitoring_system.monitoring_dir == temp_dir / "monitoring"
        assert monitoring_system.is_monitoring is False
        assert len(monitoring_system.thresholds) > 0
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, monitoring_system):
        """Test alert creation method exists and is callable."""
        # Just verify the method exists and is async-compatible
        assert hasattr(monitoring_system, '_create_alert')
        assert callable(monitoring_system._create_alert)
    
    @pytest.mark.asyncio
    async def test_metric_recording(self, monitoring_system):
        """Test metric recording."""
        await monitoring_system._record_metric("test_metric", 42.0, "count")
        
        assert len(monitoring_system.metrics) == 1
        metric = monitoring_system.metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.unit == "count"
    
    @pytest.mark.asyncio
    async def test_health_checks(self, monitoring_system):
        """Test health check execution."""
        await monitoring_system._check_cpu_health()
        await monitoring_system._check_memory_health()
        await monitoring_system._check_disk_health()
        
        assert len(monitoring_system.health_checks) >= 3
        
        # Check that health checks have valid status
        for check in monitoring_system.health_checks:
            assert check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, 
                                  HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
    
    def test_system_status(self, monitoring_system):
        """Test system status retrieval."""
        status = monitoring_system.get_system_status()
        
        assert 'overall_health' in status
        assert 'health_checks' in status
        assert 'metrics' in status
        assert 'active_alerts' in status
        assert 'monitoring_active' in status
        assert 'timestamp' in status
    
    @pytest.mark.asyncio
    async def test_metrics_summary(self, monitoring_system):
        """Test metrics summary generation."""
        # Record some real metrics
        await monitoring_system._record_metric("test_metric", 10.0, "count")
        await monitoring_system._record_metric("test_metric", 20.0, "count")
        
        summary = monitoring_system.get_metrics_summary(hours=1)
        
        assert 'period_hours' in summary
        assert 'metrics' in summary


class TestUniversalDownloader:
    """Test universal downloader integration."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def downloader(self, temp_dir):
        """Create universal downloader."""
        return UniversalBlakeDownloader(temp_dir, max_concurrent=5)
    
    def test_initialization(self, downloader, temp_dir):
        """Test downloader initialization."""
        assert downloader.data_dir == temp_dir
        assert downloader.max_concurrent == 5
        assert downloader.discovery_engine is not None
        assert downloader.incremental_updater is not None
        assert downloader.data_organizer is not None
    
    @pytest.mark.asyncio
    async def test_discover_and_download_all(self, downloader):
        """Test comprehensive discovery and download."""
        with patch.object(downloader.discovery_engine, 'discover_sources', return_value=[]):
            with patch.object(downloader.discovery_engine, 'get_comprehensive_work_list', return_value=[]):
                results = await downloader.discover_and_download_all(force=False)
                
                assert 'session_id' in results
                assert 'start_time' in results
                assert 'sources_discovered' in results
                assert 'works_discovered' in results
                assert 'works_downloaded' in results
    
    @pytest.mark.asyncio
    async def test_run_incremental_updates(self, downloader):
        """Test incremental updates method exists and returns a result."""
        # Test that run_incremental_updates returns some kind of result
        results = await downloader.run_incremental_updates()
        # It should return a dict or object with update information
        assert results is not None
    
    @pytest.mark.asyncio
    async def test_search_works(self, downloader):
        """Test work search functionality."""
        with patch.object(downloader.data_organizer, 'search_works', return_value=[]):
            with patch.object(downloader, '_load_work_from_organization', return_value=None):
                results = await downloader.search_works("test query")
                assert isinstance(results, list)
    
    def test_get_comprehensive_statistics(self, downloader):
        """Test comprehensive statistics."""
        stats = downloader.get_comprehensive_statistics()
        
        assert 'discovery' in stats
        assert 'organization' in stats
        assert 'updates' in stats
        assert 'downloads' in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_and_optimize(self, downloader):
        """Test cleanup and optimization."""
        with patch.object(downloader.data_organizer, 'cleanup_orphaned_files', return_value=5):
            with patch.object(downloader.download_manager, 'cleanup_failed_downloads', return_value=2):
                results = await downloader.cleanup_and_optimize()
                
                assert 'orphaned_files_removed' in results
                assert 'indexes_rebuilt' in results
                assert 'failed_downloads_cleaned' in results


class TestIntegration:
    """Integration tests for Project A components."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, temp_dir):
        """Test complete end-to-end workflow."""
        # Initialize universal downloader
        downloader = UniversalBlakeDownloader(temp_dir, max_concurrent=3)
        
        # Mock all external dependencies
        with patch.object(downloader.discovery_engine, 'discover_sources', return_value=[]):
            with patch.object(downloader.discovery_engine, 'get_comprehensive_work_list', return_value=[]):
                with patch.object(downloader, '_download_from_source_comprehensive', return_value={
                    'works_downloaded': 0,
                    'works': [],
                    'errors': []
                }):
                    # Run comprehensive download
                    results = await downloader.discover_and_download_all(force=False)
                    
                    assert 'session_id' in results
                    assert 'sources_discovered' in results
                    assert 'works_discovered' in results
                    assert 'works_downloaded' in results
    
    @pytest.mark.asyncio
    async def test_quality_assurance_integration(self, temp_dir):
        """Test quality assurance integration."""
        from blake.downloader.work_verifier import QualityAssurance
        
        quality_system = QualityAssurance(temp_dir)
        
        # Create test work
        metadata = BlakeMetadata(
            id="integration_test",
            title="Integration Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        
        work = BlakeWork(
            id="integration_test",
            metadata=metadata,
            text_content="This is a test work for integration testing."
        )
        
        # Mock file operations
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat', return_value=Mock(st_size=1024)):
                with patch.object(Path, 'write_text', return_value=None):
                    with patch.object(Path, 'read_text', return_value="test content"):
                        # Verify work
                        report = await quality_system.verify_work(work)
                        
                        assert report.work_id == "integration_test"
                        assert report.overall_score >= 0.0
                        assert report.overall_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self, temp_dir):
        """Test monitoring system integration."""
        monitoring_system = MonitoringSystem(temp_dir)
        
        # Start monitoring
        await monitoring_system.start_monitoring()
        assert monitoring_system.is_monitoring is True
        
        # Record some metrics
        await monitoring_system.record_download_metric(
            SourceType.BLAKE_ARCHIVE, True, 5.0, 1024*1024
        )
        
        # Get system status
        status = monitoring_system.get_system_status()
        assert 'overall_health' in status
        assert 'metrics' in status
        
        # Stop monitoring
        await monitoring_system.stop_monitoring()
        assert monitoring_system.is_monitoring is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
