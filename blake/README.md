# Blake Package

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-green.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Core Python package for the Blake corpus workflow.

## Features

- **Corpus pipeline**: discovery, acquisition, metadata, analysis, visualization, export, and reporting
- **Target coverage**: canonical ledger with present, partial, missing, duplicate, and unverified status
- **Multi-source acquisition**: Blake Archive, Project Gutenberg, Internet Archive
- **Text analysis**: NLTK, spaCy, sentiment analysis, entity extraction
- **Visualizations**: Word clouds, timelines, network graphs (PNG + JSON)
- **Multi-format export**: JSON, CSV, PDF, HTML, Markdown, Parquet

## Installation

```bash
# Using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Quick Start

### Run Corpus Workflow

```bash
# Quick mode (use local data, or fixture data when the cache is empty)
uv run blake corpus run --quick --output-dir analysis_output

# Local docs/manuscript/regression rerun: reuse local corpus, regenerate analysis
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus status --coverage
uv run blake corpus visualize --profile core
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

### Python API

```python
from blake import BlakeCorpus, CorpusConfig

# Initialize
corpus = BlakeCorpus(data_dir="./blake_data", output_dir="./analysis_output")

# Run reproducible workflow
summary = await corpus.run(CorpusConfig(quick=True))

# Search
matches = await corpus.search_works("innocence")

# Export to multiple formats
from pathlib import Path

from blake.export import get_exporter
from blake.models import ExportConfig

works = await corpus.get_all_works()
config = ExportConfig(format="html", output_dir=Path("analysis_output/exports"))
await get_exporter("html").export_works(works, config.output_dir, config)
```

### CLI

```bash
blake corpus run --quick --output-dir analysis_output
blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
blake corpus audit-sources --output-dir analysis_output --archive-scope archive-inventory
blake corpus acquire-evidence --from-audit analysis_output/data/source_audit.json --dry-run
blake corpus private-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
blake corpus status --coverage
blake info --work-id 21160
blake search --query "innocence"
blake explore
```

## Module Reference

| Module | Description |
|--------|-------------|
| `corpus/` | Canonical workflow, manifests, source registry |
| `analysis/` | NLP and visual analysis with NLTK, spaCy |
| `downloader/` | Multi-source acquisition with verification |
| `export/` | JSON, CSV, PDF, HTML, Markdown, Parquet export + FastAPI |
| `gui/` | Streamlit-based exploration interface |
| `metadata/` | SQLite database and search functionality |
| `utils/` | Logging, error handling, performance tracking |
| `viz/` | Visualization system with PNG + JSON output |

## Output Structure

All outputs saved to `analysis_output/`:

```
analysis_output/
├── corpus_manifest.json
├── pipeline_summary.json
├── data/              # Source discovery, provider health, audit, evidence review
├── analysis/          # Analysis summary, diagnostics, and per-work results
├── visualizations/    # Coverage, chronology, network, image/text datasets, PNG + HTML
│   ├── target_coverage_matrix.json
│   ├── target_coverage_matrix.png
│   └── corpus_workbench.html
├── exports/           # JSON, CSV, HTML, Markdown, Parquet
├── reports/           # Reports, private preflight, rights gate
└── releases/          # Public release metadata, bundle archive, citation files
```

Quick fixture records are labeled in `corpus_manifest.json`; they verify the workflow surface and do not imply a complete Blake corpus. Completeness is reported only through target ledger coverage.

## Configuration

Default data directory: `./blake_data`

Override via:
- Constructor: `BlakeCorpus(data_dir=Path("..."), output_dir=Path("..."))`
- CLI: `blake --data-dir /path --output-dir /path corpus run --quick`
- Pipeline: `CorpusConfig(data_dir=Path("..."))`

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Type checking
uv run mypy blake/

# Formatting and import checks
uv run --extra dev black --check blake/
uv run --extra dev isort --check blake/
```
