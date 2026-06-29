
import pytest
from blake.viz.dashboards.comparative_dashboard import ComparativeDashboard

class TestComparativeDashboard:
    """Tests for ComparativeDashboard."""
    
    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance."""
        return ComparativeDashboard()
        
    def test_initialization(self, dashboard):
        """Dashboard initializes correctly."""
        assert len(dashboard.components) == 4
        assert "readability_comparison" in dashboard.get_available_components()
        
    @pytest.mark.asyncio
    async def test_create_dashboard(self, dashboard):
        """Create dashboard returns InteractiveDashboard."""
        result = await dashboard.create_dashboard()
        assert result.id == "comparative_dashboard"
        assert len(result.components) == 4
        
    @pytest.mark.asyncio
    async def test_get_component(self, dashboard):
        """Get component returns component."""
        component = await dashboard.get_component("readability_comparison")
        assert component is not None
        assert component.title == "Readability Comparison"
