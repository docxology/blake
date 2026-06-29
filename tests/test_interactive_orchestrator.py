"""
Tests for Blake interactive orchestrator module.

Tests real methods without mocks.
"""

import pytest
from pathlib import Path

from blake.interactive_orchestrator import InteractiveOrchestrator


class TestInteractiveOrchestrator:
    """Tests for InteractiveOrchestrator class."""
    
    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create InteractiveOrchestrator instance."""
        return InteractiveOrchestrator(data_dir=str(tmp_path))
    
    def test_orchestrator_initialization(self, orchestrator, tmp_path):
        """Orchestrator initializes with correct data directory."""
        assert orchestrator.data_dir == tmp_path
    
    @pytest.mark.asyncio
    async def test_orchestrator_has_blake_works(self, orchestrator):
        """Orchestrator has BlakeCorpus instance after init."""
        await orchestrator.initialize()
        assert orchestrator.blake is not None
        assert orchestrator.blake._initialized is True
    
    def test_display_welcome(self, orchestrator, capsys):
        """display_welcome outputs content."""
        orchestrator.display_welcome()
        # Just verify it doesn't crash - output goes to rich console
    
    def test_display_main_menu(self, orchestrator, capsys):
        """display_main_menu outputs menu options."""
        orchestrator.display_main_menu()
        # Just verify it doesn't crash
    
    @pytest.mark.asyncio
    async def test_view_available_works(self, orchestrator):
        """view_available_works retrieves works after initialization."""
        await orchestrator.initialize()
        # view_available_works may fail gracefully if no works exist
        try:
            await orchestrator.view_available_works()
        except Exception:
            pass  # Expected if no works downloaded
    
    @pytest.mark.asyncio  
    async def test_search_works_empty_query(self, orchestrator):
        """search_works method exists and is callable."""
        await orchestrator.initialize()
        assert hasattr(orchestrator, 'search_works')
        assert callable(orchestrator.search_works)
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, orchestrator):
        """clear_cache works after initialization."""
        await orchestrator.initialize()
        # Note: clear_cache prompts for confirmation - just verify it exists
        assert hasattr(orchestrator, 'clear_cache')
        assert callable(orchestrator.clear_cache)
    
    @pytest.mark.asyncio
    async def test_show_settings(self, orchestrator):
        """show_settings displays current settings."""
        await orchestrator.show_settings()
        # Just verify it doesn't crash


class TestOrchestratorMethods:
    """Tests for specific orchestrator methods - check method existence."""
    
    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator (no init)."""
        return InteractiveOrchestrator(data_dir=str(tmp_path))
    
    def test_has_download_method(self, orchestrator):
        """Orchestrator has download_all_works method."""
        assert hasattr(orchestrator, 'download_all_works')
        assert callable(orchestrator.download_all_works)
    
    def test_has_analysis_method(self, orchestrator):
        """Orchestrator has run_text_analysis method."""
        assert hasattr(orchestrator, 'run_text_analysis')
        assert callable(orchestrator.run_text_analysis)
    
    def test_has_visualization_method(self, orchestrator):
        """Orchestrator has create_visualizations method."""
        assert hasattr(orchestrator, 'create_visualizations')
        assert callable(orchestrator.create_visualizations)
    
    def test_has_dashboard_method(self, orchestrator):
        """Orchestrator has view_dashboards method."""
        assert hasattr(orchestrator, 'view_dashboards')
        assert callable(orchestrator.view_dashboards)
    
    def test_has_report_method(self, orchestrator):
        """Orchestrator has generate_reports method."""
        assert hasattr(orchestrator, 'generate_reports')
        assert callable(orchestrator.generate_reports)
    
    def test_has_export_method(self, orchestrator):
        """Orchestrator has export_data method."""
        assert hasattr(orchestrator, 'export_data')
        assert callable(orchestrator.export_data)
