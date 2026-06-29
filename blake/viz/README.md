# Blake Visualization Module

Visualization and reporting system for William Blake's works.

## Features

- **Renderers**: Text, image, temporal, network, comparative
- **Dashboards**: Research, educational, public interfaces
- **Reports**: Automated report generation

## Usage

```python
from blake.viz import VisualizationEngine, ResearchDashboard

# Create visualization
engine = VisualizationEngine()
viz = engine.create_visualization(
    viz_type="timeline",
    data=works
)

# Launch dashboard
dashboard = ResearchDashboard(works)
dashboard.launch()
```

## Renderers

| Renderer | Purpose |
|----------|---------|
| `TextRenderer` | Text analysis visualizations |
| `ImageRenderer` | Image analysis displays |
| `TemporalRenderer` | Timeline charts |
| `NetworkRenderer` | Relationship graphs |
| `ComparativeRenderer` | Cross-work comparisons |

## Dashboards

| Dashboard | Audience |
|-----------|----------|
| Research | Academic researchers |
| Educational | Students/educators |
| Public | General audience |
