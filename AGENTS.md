# Blake Project Agent Guidelines

## Repository Overview

Blake is a platform for downloading, analyzing, and exploring William Blake's works. Built with Python 3.9+, it integrates NLP analysis, visualization, and data export.

## Entry Points

- **`run_all.py`** - Complete analysis pipeline (recommended)
- **`blake` CLI** - Command-line interface
- **`blake.BlakeCorpus`** - Python API

## Architecture

```
blake/                  # Main package
├── analysis/           # NLP and visual analysis
├── downloader/         # Multi-source data acquisition
├── export/             # Export formats and API
├── gui/                # Streamlit interface
├── metadata/           # SQLite metadata management
├── utils/              # Logging and error handling
└── viz/                # Visualization system
```

## Key Patterns

- **Orchestrator**: `BlakeCorpus` in `core.py` coordinates all modules
- **Async-first**: Download and analysis operations are async
- **Pydantic models**: All data structures in `models.py`
- **Click CLI**: Commands defined in `cli.py`

## Development

```bash
# Environment setup
uv sync

# Run complete pipeline
uv run python run_all.py

# Run tests
uv run pytest tests/ -v

# Quick mode (use existing data)
uv run python run_all.py --quick
```

## Output Directory

All outputs go to `analysis_output/`:
- `data/` - Downloaded works
- `analysis/` - Analysis results  
- `visualizations/` - Generated images
- `exports/` - JSON, CSV exports
- `reports/` - Generated reports

## Testing Standards

- Unit tests: Fast, isolated, mock external services
- Integration tests: End-to-end flows with real data
- Performance tests: Benchmark download and analysis speeds

## Data Directories

- `blake_data/`: Local storage for downloaded works
- `docs/`: Project documentation
- `examples/`: Usage demonstrations
