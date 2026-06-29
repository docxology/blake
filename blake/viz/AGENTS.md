# viz Module

Visualization and reporting system for Blake's works.

## Structure

```
viz/
├── engines/           # Core processing
│   ├── visualization_engine.py
│   └── data_processor.py
├── renderers/         # Output renderers
│   ├── text_renderer.py
│   ├── image_renderer.py
│   ├── temporal_renderer.py
│   ├── network_renderer.py
│   └── comparative_renderer.py
├── dashboards/        # Interactive dashboards
│   ├── research_dashboard.py
│   ├── educational_dashboard.py
│   └── public_dashboard.py
├── reports/           # Report generation
│   ├── report_generator.py
│   └── custom_report_builder.py
├── integrations/      # External integrations
└── models.py          # Visualization data models
```

## Key Classes

- `VisualizationEngine` - Main rendering orchestrator
- `DataProcessor` - Data preparation
- `*Renderer` - Format-specific renderers
- `*Dashboard` - Interactive dashboards
- `ReportGenerator` - Automated reports
