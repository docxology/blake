# Blake Documentation Hub

Central navigation for all Blake project documentation.

## Quick Links

| Document | Description |
|----------|-------------|
| [Quick Start](quickstart.md) | Get up and running in minutes |
| [User Guide](user-guide.md) | Detailed usage documentation |
| [API Reference](api-reference.md) | Python API and corpus CLI documentation |
| [Developer Guide](developer-guide.md) | Contributing and development |
| [Architecture](ARCHITECTURE.md) | System design and structure |

## Getting Started

```bash
# Install with uv
uv sync

# Run the offline smoke workflow
uv run blake corpus run --quick --output-dir analysis_output

# Regenerate the saved local corpus analysis without reacquiring remote assets
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none

# Prepare the public GitHub + Zenodo release bundle and metadata
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

All outputs are saved to `analysis_output/`:
- `data/` - Source discovery, provider health, source audit, and evidence review ledgers
- `analysis/` - Analysis results, summary, diagnostics, and error ledgers
- `visualizations/` - Generated figures, datasets, and corpus workbench
- `exports/` - JSON, CSV exports
- `reports/` - Generated reports, private preflight, and rights-gate outputs
- `releases/` - Public release metadata, bundle archives, checksums, and Zenodo-ready citation files

## Documentation Index

### User Documentation
- [Quick Start Guide](quickstart.md) - Installation and first steps
- [User Guide](user-guide.md) - Detailed usage instructions
- [Configuration](configuration.md) - Configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### Technical Documentation
- [API Reference](api-reference.md) - Complete Python API
- [Architecture](ARCHITECTURE.md) - System design
- [Specification](spec.md) - Technical specification

### Guides
- [Interactive Orchestrator](guides/interactive-orchestrator.md) - Terminal UI guide
- [Download Workflow](guides/download-workflow.md) - Source-governed acquisition workflow

### Developer Documentation
- [Developer Guide](developer-guide.md) - Development setup
- [System Summary](COMPREHENSIVE_SYSTEM_SUMMARY.md) - Target-aware system overview
- [Test Results](COMPREHENSIVE_TEST_RESULTS.md) - Test coverage

## Module Reference

| Module | Purpose | Documentation |
|--------|---------|---------------|
| `blake.analysis` | NLP and visual analysis | [README](../blake/analysis/README.md) |
| `blake.downloader` | Multi-source downloads | [README](../blake/downloader/README.md) |
| `blake.export` | Export and API | [README](../blake/export/README.md) |
| `blake.gui` | Streamlit interface | [README](../blake/gui/README.md) |
| `blake.metadata` | Database and search | [README](../blake/metadata/README.md) |
| `blake.viz` | Visualization system | [README](../blake/viz/README.md) |
| `blake.utils` | Utilities | [README](../blake/utils/README.md) |

## See Also

- [Project README](../README.md) - Main project documentation
- [Examples](../examples/) - Usage examples
- [Tests](../tests/) - Test suite
