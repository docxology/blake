# Blake Package Documentation

## Overview

The Blake package is a reproducible corpus workflow for William Blake's works. It provides tools for discovering, acquiring, verifying, analyzing, visualizing, exporting, and reporting on Blake's poetry, paintings, and other creative works from multiple digital archives and sources. Completeness is measured against a versioned target ledger rather than assumed from local files.

The current reproducibility contract is artifact-first: `corpus_manifest.json` records target coverage; `source_audit.json` and `source_discovery_health.json` record provider/source health; `evidence_acquisition_review.json` records unresolved evidence review; `analysis_summary.json` and `analysis_diagnostics.json` record the current analysis run; and private preflight/rights-gate reports record local-only release constraints.

See the [publication consistency review](publication-consistency-review.md) for
the saved-run membership boundary of text coverage and NLP diagnostics.

## Core Functionality

### Data Acquisition

- **Corpus Workflow**: `BlakeCorpus` coordinates discovery, acquisition, metadata, analysis, export, and reports
- **Target Coverage**: `corpus_manifest.json` reports present, partial, missing, duplicate, and unverified target entries
- **Multi-Source Downloads**: Blake Archive, Project Gutenberg, Internet Archive
- **Asynchronous Processing**: High-performance async downloads with retry logic
- **Incremental Updates**: Skip existing files and resume interrupted downloads
- **Format Support**: Text, images, metadata, and structured data

### Analysis Pipeline

- **Text Analysis**: NLP processing with NLTK, spaCy, and transformers
- **Visual Analysis**: Image processing with PIL and OpenCV
- **Cross-Analysis**: Intertextual and intermedial relationships
- **Batch Processing**: Efficient analysis of large collections

### Data Management

- **SQLite Database**: Persistent metadata storage
- **File Organization**: Structured directory tree for all data types
- **Search & Filtering**: Advanced query capabilities
- **Export Options**: Multiple formats (JSON, CSV, PDF, Parquet)

### User Interface

- **Streamlit GUI**: Interactive exploration interface
- **REST API**: Programmatic access endpoints
- **CLI Tools**: Command-line interface for automation
- **Jupyter Integration**: Notebook-friendly analysis tools

## Technical Architecture

### Core Components

```
blake/
├── corpus/              # BlakeCorpus workflow, manifests, source registry
├── models.py            # Data models and schemas
├── exceptions.py        # Custom exception handling
├── downloader/          # Download management
├── metadata/            # Metadata processing
├── analysis/            # Analysis pipeline
├── gui/                 # User interface
└── export/              # Export and API
```

### Dependencies

- **Core**: Python 3.9+, asyncio, aiohttp, aiofiles
- **Analysis**: NLTK, spaCy, scikit-learn, transformers
- **Visualization**: matplotlib, seaborn, plotly, streamlit
- **Data**: pandas, numpy, pyarrow, sqlalchemy
- **Web**: requests, beautifulsoup4, scrapy, selenium

## Quick Start

```python
import asyncio
from blake import BlakeCorpus, CorpusConfig

async def main():
    # Initialize workspace
    corpus = BlakeCorpus("./blake_data", output_dir="./analysis_output")

    # Run deterministic quick workflow
    summary = await corpus.run(CorpusConfig(quick=True))
    print(summary.status)

    # Search for specific content
    results = await corpus.search_works("innocence")
    for work in results:
        print(f"- {work.metadata.title}")

# Run the example
asyncio.run(main())
```

## Installation

### Using UV (Recommended)

```bash
# Install with all dependencies
uv add blake

# Install with specific extras
uv add "blake[gui,api,dev]"
```

### Using Pip

```bash
# Basic installation
pip install blake

# With all extras
pip install "blake[gui,api,dev]"
```

### Development Installation

```bash
git clone https://github.com/docxology/blake.git
cd blake
uv sync --all-extras
uv run python -m pytest
```

## Performance Characteristics

### Run Modes

- **Quick mode**: Offline, deterministic, and fixture-backed when `blake_data/` is empty
- **Live mode**: Uses registered source providers and records source-backed coverage in the manifest
- **Coverage reports**: Explain why a run is complete, partial, empty, or unscoped
- **Local regeneration**: `blake corpus run --skip-download ...` reuses `blake_data/` while regenerating analysis, visualizations, exports, and reports

### Analysis Performance

- **Text Analysis**: ~1 second per work
- **Visual Analysis**: ~2-3 seconds per image
- **Batch Processing**: Parallel analysis with concurrency limits
- **Memory Usage**: Efficient streaming for large files

### Storage Requirements

- **Text Files**: ~25KB per work average
- **Images**: Variable, typically 100KB-2MB per image
- **Database**: ~1KB metadata per work
- **Total**: ~1-5MB per work depending on content

## Security & Privacy

### Data Handling

- **Local Storage**: All data stored locally, no cloud dependencies
- **Source Attribution**: Proper attribution and licensing tracking
- **Privacy**: No personal data collection or transmission
- **Integrity**: Checksum verification for downloaded files

### Network Security

- **HTTPS Only**: All downloads use secure connections
- **User Agent**: Proper identification for web requests
- **Rate Limiting**: Respectful request patterns
- **Error Handling**: Graceful failure without data loss

## Documentation Structure

- [Quick Start Guide](quickstart.md) - Get up and running quickly
- [API Reference](api-reference.md) - Complete API documentation
- [User Guide](user-guide.md) - Comprehensive user documentation
- [Developer Guide](developer-guide.md) - Development and contribution guidelines
- [Configuration Guide](configuration.md) - Advanced configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Contributing

We welcome contributions! See [Developer Guide](developer-guide.md) for:

- Code style guidelines
- Testing requirements
- Pull request process
- Issue reporting

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community
- **Documentation**: Comprehensive guides and examples
- **Examples**: Working code examples in `/examples` directory
